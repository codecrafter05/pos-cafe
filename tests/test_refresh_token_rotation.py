"""Refresh-token rotation: lost-response recovery vs. genuine reuse.

Runs against in-memory SQLite so it never touches the live database:

    .venv/bin/python -m unittest discover -s tests -v
"""

import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  — registers every mapper before create_all
from app.core.config import settings
from app.core.database import Base
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.services import refresh_token_service as svc


class RotationTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine("sqlite://")
        Base.metadata.create_all(self.engine)
        self.db = sessionmaker(bind=self.engine)()
        self.user = User(
            name="Device Cashier",
            username="device1",
            password_hash="x",
            role="cashier",
            is_active=True,
        )
        self.db.add(self.user)
        self.db.flush()

    def tearDown(self):
        self.db.close()
        self.engine.dispose()

    def _family(self, family_id):
        return (
            self.db.query(RefreshToken)
            .filter(RefreshToken.family_id == family_id)
            .order_by(RefreshToken.id)
            .all()
        )

    def _live_tokens(self, family_id):
        return [r for r in self._family(family_id) if r.revoked_at is None]

    # ---- baseline ------------------------------------------------------

    def test_normal_rotation_chains_and_revokes_the_old_token(self):
        first_plain, first_row = svc.issue(self.db, self.user)
        family = first_row.family_id

        second_plain, second_row, user = svc.rotate(self.db, first_plain)

        self.assertEqual(user.id, self.user.id)
        self.assertNotEqual(second_plain, first_plain)
        self.assertIsNotNone(first_row.revoked_at)
        self.assertEqual(first_row.replaced_by_id, second_row.id)
        self.assertIsNone(second_row.revoked_at)
        self.assertEqual([r.id for r in self._live_tokens(family)], [second_row.id])

    # ---- branch (a): lost rotation response, device recovers -----------

    def test_replay_inside_grace_with_unused_replacement_recovers_silently(self):
        """The 499-in-nginx case: server rotated, response never arrived, device
        retries with the old token. It must get a working token back, and the
        family must survive."""
        first_plain, first_row = svc.issue(self.db, self.user)
        family = first_row.family_id
        _undelivered_plain, undelivered_row, _ = svc.rotate(self.db, first_plain)
        self.assertIsNone(undelivered_row.last_used_at)

        recovered_plain, recovered_row, user = svc.rotate(self.db, first_plain)

        self.assertEqual(user.id, self.user.id)
        self.assertEqual(recovered_row.family_id, family)
        self.assertIsNone(recovered_row.revoked_at, "re-issued token must be usable")
        self.assertNotEqual(recovered_row.id, undelivered_row.id)

        # Family intact: nothing was mass-revoked.
        self.assertIsNone(undelivered_row.revoked_at)
        self.assertCountEqual(
            [r.id for r in self._live_tokens(family)],
            [undelivered_row.id, recovered_row.id],
        )
        # The replay itself is recorded on the old row.
        self.assertIsNotNone(first_row.last_used_at)

        # And the recovered token really works for the next rotation.
        _next_plain, next_row, _ = svc.rotate(self.db, recovered_plain)
        self.assertEqual(next_row.family_id, family)
        self.assertIsNotNone(recovered_row.revoked_at)

    def test_recovery_refuses_when_user_deactivated(self):
        first_plain, first_row = svc.issue(self.db, self.user)
        svc.rotate(self.db, first_plain)
        self.user.is_active = False
        self.db.flush()

        with self.assertRaises(svc.RefreshError) as ctx:
            svc.rotate(self.db, first_plain)
        self.assertEqual(ctx.exception.status_code, 401)

    # ---- branch (b): genuine reuse, family still revoked ---------------

    def test_replay_outside_grace_revokes_the_whole_family(self):
        first_plain, first_row = svc.issue(self.db, self.user)
        family = first_row.family_id
        _plain, undelivered_row, _ = svc.rotate(self.db, first_plain)

        # Push the rotation well outside the grace window.
        first_row.revoked_at = first_row.revoked_at - timedelta(
            seconds=settings.REFRESH_REUSE_GRACE_SECONDS + 30
        )
        self.db.flush()

        with self.assertRaises(svc.RefreshError) as ctx:
            svc.rotate(self.db, first_plain)

        self.assertEqual(ctx.exception.status_code, 401)
        self.assertEqual(ctx.exception.detail, svc.REUSE_DETECTED_DETAIL)
        self.assertIsNotNone(undelivered_row.revoked_at)
        self.assertEqual(self._live_tokens(family), [])

    def test_replay_inside_grace_still_revokes_when_replacement_was_used(self):
        """Inside the window, but somebody already moved forward with the
        replacement — that makes this presentation real reuse, not a lost
        response, so theft detection must fire."""
        first_plain, first_row = svc.issue(self.db, self.user)
        family = first_row.family_id
        _plain, replacement_row, _ = svc.rotate(self.db, first_plain)

        replacement_row.last_used_at = svc._utcnow()
        self.db.flush()

        with self.assertRaises(svc.RefreshError) as ctx:
            svc.rotate(self.db, first_plain)

        self.assertEqual(ctx.exception.detail, svc.REUSE_DETECTED_DETAIL)
        self.assertEqual(self._live_tokens(family), [])

    def test_replay_after_family_already_revoked_stays_rejected(self):
        first_plain, first_row = svc.issue(self.db, self.user)
        family = first_row.family_id
        _plain, replacement_row, _ = svc.rotate(self.db, first_plain)
        svc.revoke_family(self.db, family)
        self.db.flush()

        with self.assertRaises(svc.RefreshError):
            svc.rotate(self.db, first_plain)
        self.assertEqual(self._live_tokens(family), [])

    # ---- unrelated rejection paths still behave ------------------------

    def test_unknown_token_is_rejected_without_touching_the_family(self):
        _plain, row = svc.issue(self.db, self.user)
        with self.assertRaises(svc.RefreshError):
            svc.rotate(self.db, "not-a-real-token")
        self.assertIsNone(row.revoked_at)

    def test_expired_token_is_rejected_and_revoked(self):
        plain, row = svc.issue(self.db, self.user)
        row.expires_at = svc._utcnow() - timedelta(seconds=1)
        self.db.flush()

        with self.assertRaises(svc.RefreshError) as ctx:
            svc.rotate(self.db, plain)
        self.assertEqual(ctx.exception.detail, "Refresh token expired")
        self.assertIsNotNone(row.revoked_at)


if __name__ == "__main__":
    unittest.main()

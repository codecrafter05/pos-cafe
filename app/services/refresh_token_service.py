"""Issue, rotate, and revoke opaque refresh tokens for handheld devices."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_refresh_token, new_refresh_token_plain
from app.models.refresh_token import RefreshToken
from app.models.user import User

logger = logging.getLogger(__name__)

# Distinct from a plain "Invalid refresh token" so the cause is visible to the
# client (and in support conversations) instead of looking like a network fault.
REUSE_DETECTED_DETAIL = (
    "Refresh token reuse detected — this device was signed out for security. "
    "Sign in again to resume syncing."
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _as_naive(dt: datetime) -> datetime:
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def issue(
    db: Session,
    user: User,
    *,
    family_id: str | None = None,
) -> tuple[str, RefreshToken]:
    plain = new_refresh_token_plain()
    row = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(plain),
        family_id=family_id or str(uuid.uuid4()),
        expires_at=_utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
        created_at=_utcnow(),
    )
    db.add(row)
    db.flush()
    return plain, row


def revoke_row(row: RefreshToken, *, now: datetime | None = None) -> None:
    if row.revoked_at is None:
        row.revoked_at = now or _utcnow()


def revoke_family(db: Session, family_id: str) -> int:
    now = _utcnow()
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        revoke_row(row, now=now)
    return len(rows)


def revoke_all_for_user(db: Session, user_id: int) -> int:
    now = _utcnow()
    rows = (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
        .all()
    )
    for row in rows:
        revoke_row(row, now=now)
    return len(rows)


class RefreshError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _is_lost_response_replay(
    row: RefreshToken, replacement: RefreshToken | None, now: datetime
) -> bool:
    """True when an already-rotated token is presented again so soon, and its
    replacement is so untouched, that the only sensible reading is "the device
    never received the rotation response".

    Every condition must hold:

    * the replay lands inside the grace window that follows the rotation, and
    * the replacement token still exists and is itself un-revoked, and
    * nobody has ever used the replacement.

    That last one is what keeps theft detection intact: once *any* client has
    moved forward with the replacement, a presentation of the old token is
    genuine reuse and must revoke the family.
    """
    if row.revoked_at is None or replacement is None:
        return False
    if replacement.revoked_at is not None or replacement.last_used_at is not None:
        return False
    grace = timedelta(seconds=settings.REFRESH_REUSE_GRACE_SECONDS)
    return _as_naive(row.revoked_at) >= now - grace


def rotate(db: Session, plain_token: str) -> tuple[str, RefreshToken, User]:
    """Validate a refresh token, revoke it, and issue a replacement in the same family.

    Reuse of an already-rotated token revokes the whole family (theft detection),
    except for the narrow lost-response replay handled by
    :func:`_is_lost_response_replay`, which hands the device a usable token
    instead of locking it out of a café shift.
    """
    token_hash = hash_refresh_token(plain_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        raise RefreshError(401, "Invalid refresh token")

    now = _utcnow()
    if row.revoked_at is not None:
        replacement = (
            db.get(RefreshToken, row.replaced_by_id)
            if row.replaced_by_id is not None
            else None
        )

        if _is_lost_response_replay(row, replacement, now):
            user = db.get(User, row.user_id)
            if user is None or not user.is_active:
                raise RefreshError(401, "User not found or inactive")
            # The replacement was minted but never delivered, so its plaintext is
            # unrecoverable (only the hash is stored). Mint another one in the
            # same family and leave the undelivered row valid — nobody holds it,
            # and revoking it here is what would strand a device that did in fact
            # receive the earlier response.
            new_plain, new_row = issue(db, user, family_id=row.family_id)
            row.last_used_at = now
            db.flush()
            logger.warning(
                "refresh_grace_reissue user_id=%s username=%s family_id=%s "
                "replayed_token_id=%s undelivered_token_id=%s new_token_id=%s "
                "replay_age_seconds=%.1f — rotation response was lost in transit, "
                "device recovered without re-login",
                user.id,
                user.username,
                row.family_id,
                row.id,
                replacement.id,
                new_row.id,
                (now - _as_naive(row.revoked_at)).total_seconds(),
            )
            return new_plain, new_row, user

        if row.replaced_by_id is not None:
            revoked_count = revoke_family(db, row.family_id)
            db.flush()
            user = db.get(User, row.user_id)
            logger.warning(
                "refresh_family_revoked user_id=%s username=%s role=%s family_id=%s "
                "replayed_token_id=%s rotated_at=%s replacement_token_id=%s "
                "replacement_last_used_at=%s replay_age_seconds=%.1f "
                "tokens_revoked=%s — reuse of an already-rotated token; this device "
                "is now signed out and must log in again",
                row.user_id,
                user.username if user is not None else "?",
                user.role if user is not None else "?",
                row.family_id,
                row.id,
                row.revoked_at,
                row.replaced_by_id,
                replacement.last_used_at if replacement is not None else None,
                (now - _as_naive(row.revoked_at)).total_seconds(),
                revoked_count,
            )
            raise RefreshError(401, REUSE_DETECTED_DETAIL)
        raise RefreshError(401, "Invalid refresh token")

    if _as_naive(row.expires_at) <= now:
        revoke_row(row, now=now)
        logger.warning(
            "refresh_token_expired user_id=%s family_id=%s token_id=%s expired_at=%s "
            "— device must log in again",
            row.user_id,
            row.family_id,
            row.id,
            row.expires_at,
        )
        raise RefreshError(401, "Refresh token expired")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        revoke_row(row, now=now)
        logger.warning(
            "refresh_user_unavailable user_id=%s family_id=%s token_id=%s "
            "user_missing=%s — device must log in again",
            row.user_id,
            row.family_id,
            row.id,
            user is None,
        )
        raise RefreshError(401, "User not found or inactive")

    new_plain, new_row = issue(db, user, family_id=row.family_id)
    row.last_used_at = now
    revoke_row(row, now=now)
    row.replaced_by_id = new_row.id
    db.flush()
    return new_plain, new_row, user


def revoke_plain(db: Session, plain_token: str) -> None:
    token_hash = hash_refresh_token(plain_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        return
    revoke_row(row)


def list_for_user(db: Session, user_id: int) -> list[RefreshToken]:
    return (
        db.query(RefreshToken)
        .filter(RefreshToken.user_id == user_id)
        .order_by(RefreshToken.created_at.desc())
        .limit(50)
        .all()
    )

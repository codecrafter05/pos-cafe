"""Issue, rotate, and revoke opaque refresh tokens for handheld devices."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_refresh_token, new_refresh_token_plain
from app.models.refresh_token import RefreshToken
from app.models.user import User


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


def rotate(db: Session, plain_token: str) -> tuple[str, RefreshToken, User]:
    """Validate a refresh token, revoke it, and issue a replacement in the same family.

    Reuse of an already-rotated token revokes the whole family (theft detection).
    """
    token_hash = hash_refresh_token(plain_token)
    row = db.query(RefreshToken).filter(RefreshToken.token_hash == token_hash).first()
    if row is None:
        raise RefreshError(401, "Invalid refresh token")

    now = _utcnow()
    if row.revoked_at is not None:
        if row.replaced_by_id is not None:
            revoke_family(db, row.family_id)
            db.flush()
        raise RefreshError(401, "Invalid refresh token")

    if _as_naive(row.expires_at) <= now:
        revoke_row(row, now=now)
        raise RefreshError(401, "Refresh token expired")

    user = db.get(User, row.user_id)
    if user is None or not user.is_active:
        revoke_row(row, now=now)
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

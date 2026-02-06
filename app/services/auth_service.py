from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, hash_refresh_token, new_refresh_token_plain
from app.models.refresh_token import RefreshToken
from app.models.user import User


def issue_token_pair(db: Session, user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.id))
    refresh_plain = new_refresh_token_plain()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_plain),
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    db.commit()
    return access_token, refresh_plain


def get_refresh_token(db: Session, refresh_plain: str) -> RefreshToken | None:
    refresh_hash = hash_refresh_token(refresh_plain)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == refresh_hash)
    return db.scalar(stmt)


def rotate_refresh_token(db: Session, refresh_plain: str) -> tuple[str, str] | None:
    refresh = get_refresh_token(db, refresh_plain)
    if not refresh:
        return None
    if refresh.revoked_at or refresh.expires_at < datetime.utcnow():
        return None

    refresh.revoked_at = datetime.utcnow()
    db.add(refresh)
    db.commit()

    user = refresh.user
    return issue_token_pair(db, user)


def revoke_refresh_token(db: Session, refresh_plain: str) -> bool:
    refresh = get_refresh_token(db, refresh_plain)
    if not refresh:
        return False
    refresh.revoked_at = datetime.utcnow()
    db.add(refresh)
    db.commit()
    return True

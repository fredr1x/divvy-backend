from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token_plain,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User


async def issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(str(user.id), user.first_name, user.last_name, user.email)
    refresh_plain = new_refresh_token_plain()
    refresh = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(refresh_plain),
        expires_at=datetime.utcnow()
        + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    return access_token, refresh_plain


async def get_refresh_token(
    db: AsyncSession, refresh_plain: str
) -> RefreshToken | None:
    refresh_hash = hash_refresh_token(refresh_plain)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == refresh_hash)
    return await db.scalar(stmt)


async def rotate_refresh_token(
    db: AsyncSession, refresh_plain: str
) -> tuple[str, str] | None:
    refresh = await get_refresh_token(db, refresh_plain)
    if not refresh:
        return None
    if refresh.revoked_at or refresh.expires_at < datetime.utcnow():
        return None

    refresh.revoked_at = datetime.utcnow()
    db.add(refresh)

    user = refresh.user
    return await issue_token_pair(db, user)


async def revoke_refresh_token(db: AsyncSession, refresh_plain: str) -> bool:
    refresh = await get_refresh_token(db, refresh_plain)
    if not refresh:
        return False
    refresh.revoked_at = datetime.utcnow()
    db.add(refresh)
    return True

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password
from app.models.user import User


async def get_user_by_id(db: AsyncSession, user_id: int) -> User | None:
    return await db.scalar(select(User).where(User.id == user_id))


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    return await db.scalar(select(User).where(User.email == email))


async def get_user_by_google_sub(db: AsyncSession, google_sub: str) -> User | None:
    return await db.scalar(select(User).where(User.google_sub == google_sub))


async def create_user_local(
    db: AsyncSession,
    email: str,
    password: str,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = User(
        email=email,
        first_name=first_name or "",
        last_name=last_name or "",
        password=hash_password(password),
        auth_provider="local",
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def create_google_user(
    db: AsyncSession,
    email: str,
    google_sub: str,
    first_name: str | None,
    last_name: str | None,
) -> User:
    user = User(
        email=email,
        first_name=first_name or "",
        last_name=last_name or "",
        password=None,
        auth_provider="google",
        google_sub=google_sub,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user

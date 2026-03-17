from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.user import User


def get_user_by_id(db: Session, user_id: int) -> User:
    user = db.scalar(select(User).where(User.id == user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    user = db.scalar(select(User).where(User.email == email))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_user_by_google_sub(db: Session, google_sub: str) -> User | None:
    user = db.scalar(select(User).where(User.google_sub == google_sub))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def create_user_local(
    db: Session,
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
    db.commit()
    db.refresh(user)
    return user


def create_google_user(
    db: Session,
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
    db.commit()
    db.refresh(user)
    return user

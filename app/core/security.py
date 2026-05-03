from datetime import datetime, timedelta
import hashlib
import secrets
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt_sha256"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)

def verify_password(password: str, hashed_password: str) -> bool:
    return pwd_context.verify(password, hashed_password)
# 
def create_access_token(
    subject: str,
    first_name: str,
    last_name: str,
    email: str,
    is_verified: bool,
    is_active: bool,
    auth_provider: str,
) -> str:
    expire = datetime.now() + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": subject,
        "exp": expire,
        "type": "access",
        "email": email,
        "first_name": first_name,
        "last_name": last_name,
        "is_verified": is_verified,
        "is_active": is_active,
        "auth_provider": auth_provider,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def create_refresh_token(subject: str) -> str:
    expire = datetime.now() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {"sub": subject, "exp": expire, "type": "refresh"}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(
            token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
        )
    except JWTError as exc:
        raise ValueError("Invalid token") from exc

def new_refresh_token_plain() -> str:
    return secrets.token_urlsafe(48)

def hash_refresh_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()

from app.core.config import settings
from fastapi import HTTPException
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

salt = "email-verification"
serializer = URLSafeTimedSerializer(secret_key=settings.SECRET_KEY, salt=salt)

def create_url_safe_token(data: dict, expiration=3600) -> str:
    _ = expiration
    return serializer.dumps(data, salt=salt)

def decode_url_safe_token(token: str, max_age=3600) -> dict:
    try:
        data = serializer.loads(token, salt=salt, max_age=max_age)
        return data
    except SignatureExpired:
        raise HTTPException(status_code=400, detail="Token has expired")
    except BadSignature:
        raise HTTPException(status_code=400, detail="Invalid token")

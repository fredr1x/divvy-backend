import asyncio
from datetime import datetime, timedelta
from urllib.parse import urlencode

import httpx
from fastapi import BackgroundTasks, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import HTMLResponse

from app.core.config import settings
from app.core.security import (
    create_access_token,
    hash_refresh_token,
    new_refresh_token_plain,
    verify_password,
)
from app.dependencies import get_ip_address
from app.models.audit_logs import AuditLog
from app.models.enums import ActionStatus, ActionType
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead,
)
from app.services.email.email_service import send_verification_email
from app.services.email.utils import create_url_safe_token, decode_url_safe_token
from app.services.user.user_service import (
    create_google_user,
    create_user_local,
    get_user_by_email,
    get_user_by_google_sub,
    set_verified_to_user,
)
from app.services.audit.audit_logs_service import (
    create_failed_audit_log,
)


GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"
GOOGLE_CODE_CACHE_TTL_SECONDS = 120

_google_code_lock = asyncio.Lock()
_google_code_futures: dict[str, asyncio.Future[TokenPair]] = {}
_google_code_results: dict[str, tuple[TokenPair, datetime]] = {}


def _cleanup_google_code_cache(now: datetime) -> None:
    expired_codes = [
        code
        for code, (_, created_at) in _google_code_results.items()
        if (now - created_at).total_seconds() > GOOGLE_CODE_CACHE_TTL_SECONDS
    ]
    for code in expired_codes:
        _google_code_results.pop(code, None)


async def issue_token_pair(db: AsyncSession, user: User) -> tuple[str, str]:
    access_token = create_access_token(
        str(user.id),
        user.first_name,
        user.last_name,
        user.email,
        user.is_verified,
        user.is_active,
    )

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
    if not user.is_active:
        return None
    return await issue_token_pair(db, user)


async def revoke_refresh_token(db: AsyncSession, refresh_plain: str) -> bool:
    refresh = await get_refresh_token(db, refresh_plain)
    if not refresh:
        return False
    refresh.revoked_at = datetime.utcnow()
    db.add(refresh)
    return True


async def register_user(
    request: Request,
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession,
) -> TokenPair:
    audit_log = AuditLog(
        action_type=ActionType.CREATE,
        ip_address=get_ip_address(request),
        entity_name="USER",
    )

    existing = await get_user_by_email(db, payload.email.__str__())
    if existing:
        if not existing.is_active:
            message = "Account is deactivated"
            await create_failed_audit_log(db, audit_log, message)
            raise HTTPException(status_code=400, detail=message)
        message = "Email already registered"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    user: User = await create_user_local(
        db,
        payload.email.__str__(),
        payload.password,
        payload.first_name,
        payload.last_name,
    )
    user_read = UserRead.model_validate(user)

    audit_log.user_id = user.id
    audit_log.entity_id = user.id
    audit_log.new_values = user_read.model_dump(mode="json")
    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = (
        f"User created successfully, user_id: {user.id}, email: {user.email}"
    )
    db.add(audit_log)
    await db.commit()

    token = create_url_safe_token({"email": user.email})
    background_tasks.add_task(
        send_verification_email,
        user.email,
        f"{settings.BACKEND_DOMAIN}/auth/verify/{token}",
    )

    access_token, refresh_token = await issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def verify_user_email_token(
    token: str, db: AsyncSession
) -> RedirectResponse | HTMLResponse:
    token_data = decode_url_safe_token(token)
    email = token_data.get("email")

    if email:
        user = await get_user_by_email(db, email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await set_verified_to_user(db, user)

        return RedirectResponse(url=f"{settings.FRONTEND_DOMAIN}/dashboard")

    return HTMLResponse(
        content="""
        <html><body><h2>Verification failed</h2></body></html>
        """,
        status_code=400,
    )


async def resend_verification_email(
    db: AsyncSession,
    email: str,
    background_tasks: BackgroundTasks,
) -> dict[str, str]:
    normalized_email = email.strip().lower()
    user = await get_user_by_email(db, normalized_email)

    if not user or user.is_verified or not user.is_active:
        return {
            "message": "If an account exists and needs verification, we sent an email."
        }

    token = create_url_safe_token({"email": normalized_email})
    link = f"{settings.BACKEND_DOMAIN}/auth/verify/{token}"
    background_tasks.add_task(send_verification_email, normalized_email, link)

    return {
        "message": "If an account exists and needs verification, we sent an email."
    }


async def login_user(request: Request, payload: LoginRequest, db: AsyncSession) -> TokenPair:
    user = await get_user_by_email(db, payload.email.__str__())
    audit_log = AuditLog(
        action_type=ActionType.LOGIN,
        ip_address=get_ip_address(request),
        entity_name="USER",
    )

    if (
        not user
        or not user.password
        or not verify_password(payload.password, user.password)
    ):
        message = "Invalid credentials"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)
    if not user.is_active:
        message = "Account is not active"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=403, detail=message)

    audit_log.user_id = user.id
    audit_log.entity_id = user.id
    audit_log.message = "User login successful"
    audit_log.action_status = ActionStatus.SUCCESS
    db.add(audit_log)
    await db.commit()

    access_token, refresh_token = await issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


async def refresh_user_token(
    request: Request, payload: RefreshRequest, db: AsyncSession
) -> TokenPair:
    result = await rotate_refresh_token(db, payload.refresh_token)
    audit_log = AuditLog(
        action_type=ActionType.REFRESH_TOKEN,
        ip_address=get_ip_address(request),
        entity_name="REFRESH_TOKEN, USER",
    )

    if not result:
        message = "Invalid refresh token"
        audit_log.message = message
        audit_log.action_status = ActionStatus.FAILED
        db.add(audit_log)
        await db.commit()
        raise HTTPException(status_code=401, detail=message)

    access_token, refresh_token_value = result
    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = "Token refreshed successfully"
    db.add(audit_log)
    await db.commit()
    return TokenPair(access_token=access_token, refresh_token=refresh_token_value)


async def logout_user(
    request: Request, payload: LogoutRequest, db: AsyncSession
) -> dict[str, bool]:
    revoked = await revoke_refresh_token(db, payload.refresh_token)
    audit_log = AuditLog(
        action_type=ActionType.LOGOUT,
        ip_address=get_ip_address(request),
        entity_name="REFRESH_TOKEN, USER",
    )

    if not revoked:
        message = "Failed to revoke refresh token"
        audit_log.action_status = ActionStatus.FAILED
        audit_log.message = message
        db.add(audit_log)
        await db.commit()
        return {"revoked": revoked}

    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = "User logged out successfully"
    db.add(audit_log)
    await db.commit()
    return {"revoked": revoked}


def get_google_login_redirect() -> RedirectResponse:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    url = f"{GOOGLE_AUTH_URL}?{urlencode(params)}"
    return RedirectResponse(url)


async def handle_google_callback(code: str, db: AsyncSession) -> TokenPair:
    now = datetime.utcnow()
    async with _google_code_lock:
        _cleanup_google_code_cache(now)

        cached = _google_code_results.get(code)
        if cached:
            return cached[0]

        existing_future = _google_code_futures.get(code)
        if existing_future:
            wait_future = existing_future
            is_owner = False
        else:
            wait_future = asyncio.get_running_loop().create_future()
            _google_code_futures[code] = wait_future
            is_owner = True

    if not is_owner:
        return await wait_future

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            token_response = await client.post(
                GOOGLE_TOKEN_URL,
                data={
                    "code": code,
                    "client_id": settings.GOOGLE_CLIENT_ID,
                    "client_secret": settings.GOOGLE_CLIENT_SECRET,
                    "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                    "grant_type": "authorization_code",
                },
            )

            if token_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Google token exchange failed")

            token_data = token_response.json()
            id_token = token_data.get("id_token")
            if not id_token:
                raise HTTPException(status_code=400, detail="Google ID token missing")

            info_response = await client.get(
                GOOGLE_TOKENINFO_URL, params={"id_token": id_token}
            )

            if info_response.status_code != 200:
                raise HTTPException(status_code=400, detail="Google token verification failed")

            info = info_response.json()
            if info.get("aud") != settings.GOOGLE_CLIENT_ID:
                raise HTTPException(status_code=400, detail="Invalid Google audience")

            email = info.get("email")
            google_sub = info.get("sub")
            full_name = info.get("name")
            first_name = info.get("given_name")
            last_name = info.get("family_name")

            if not email or not google_sub:
                raise HTTPException(status_code=400, detail="Invalid Google profile")

            if not first_name and not last_name and full_name:
                name_parts = full_name.split(maxsplit=1)
                first_name = name_parts[0]
                last_name = name_parts[1] if len(name_parts) > 1 else ""

            user = await get_user_by_google_sub(db, google_sub)
            if user and not user.is_active:
                raise HTTPException(status_code=403, detail="Account is not active")
            if not user:
                existing = await get_user_by_email(db, email)
                if existing:
                    if not existing.is_active:
                        raise HTTPException(status_code=403, detail="Account is not active")
                    existing.google_sub = google_sub
                    existing.auth_provider = "google"
                    db.add(existing)
                    await db.flush()
                    await db.refresh(existing)
                    user = existing
                else:
                    user = await create_google_user(
                        db,
                        email,
                        google_sub,
                        first_name,
                        last_name,
                    )

            access_token, refresh_token = await issue_token_pair(db, user)
            token_pair = TokenPair(access_token=access_token, refresh_token=refresh_token)

            async with _google_code_lock:
                _google_code_results[code] = (token_pair, datetime.utcnow())
                future = _google_code_futures.pop(code, None)
                if future and not future.done():
                    future.set_result(token_pair)

            return token_pair
        except Exception as exc:
            async with _google_code_lock:
                future = _google_code_futures.pop(code, None)
                if future and not future.done():
                    future.set_exception(exc)
            raise


def get_google_frontend_callback_redirect(code: str) -> RedirectResponse:
    frontend_callback_url = (
        f"{settings.FRONTEND_DOMAIN}/auth/google/callback?{urlencode({'code': code})}"
    )
    return RedirectResponse(url=frontend_callback_url)

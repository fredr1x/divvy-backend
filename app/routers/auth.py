from urllib.parse import urlencode

import httpx
from app.core.config import settings
from app.core.security import verify_password
from app.db.session import get_db
from app.dependencies import get_ip_address
from app.models.audit_logs import AuditLog
from app.models.enums import ActionStatus, ActionType
from app.models.user import User
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
    UserRead, AccountVerified, AccountVerificationFailed,
)
from app.services.auth.auth_service import (
    issue_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.email.email_service import (send_verification_email)
from app.services.email.utils import (create_url_safe_token, decode_url_safe_token)
from app.services.user.user_service import (
    create_google_user,
    create_user_local,
    get_user_by_email,
    get_user_by_google_sub,
    set_verified_to_user
)
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


@router.post("/register", response_model=TokenPair)
async def register(
    request: Request,
    payload: UserCreate,
    db: AsyncSession = Depends(get_db)
) -> TokenPair:
    audit_log = AuditLog(
        action_type=ActionType.CREATE,
        ip_address=get_ip_address(request),
        entity_name="USER",
    )

    existing = await get_user_by_email(db, payload.email.__str__())
    if existing:
        message = "Email already registered"
        audit_log.action_status = ActionStatus.FAILED
        audit_log.message = message
        db.add(audit_log)
        await db.commit()
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
    audit_log.new_values = user_read.model_dump(mode="json")
    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = f"User created successfully, user_id: {user.id}, email: {user.email}"
    db.add(audit_log)
    await db.commit()

    token = create_url_safe_token({"email": user.email})
    await send_verification_email(user.email, f"http://{settings.DOMAIN}/auth/verify/{token}")

    access_token, refresh_token = await issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.get("/verify/{token}")
async def verify_user_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    token_data = decode_url_safe_token(token)
    email = token_data.get("email")

    if email:
        user = await get_user_by_email(db, email)

        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        await set_verified_to_user(db, user)

        return AccountVerified(message="Account verified successfully")

    return AccountVerificationFailed(message="Error occurred during verification")

@router.post("/login", response_model=TokenPair)
async def login(
    request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    user = await get_user_by_email(db, payload.email.__str__())
    audit_log = AuditLog(
        action_type=ActionType.LOGIN,
        ip_address=get_ip_address(request),
        entity_name="USER",
    )

    if not user or not user.password or not verify_password(payload.password, user.password):
        message = "Invalid credentials"
        audit_log.action_status = ActionStatus.FAILED
        audit_log.message = message
        db.add(audit_log)
        await db.commit()
        raise HTTPException(status_code=400, detail=message)

    audit_log.user_id = user.id
    audit_log.entity_id = user.id
    audit_log.message = "User login successful"
    audit_log.action_status = ActionStatus.SUCCESS
    db.add(audit_log)
    await db.commit()

    access_token, refresh_token = await issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)
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


@router.post("/logout")
async def logout(
    request: Request, payload: LogoutRequest, db: AsyncSession = Depends(get_db)
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


@router.get("/google/login")
async def google_login() -> RedirectResponse:
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


@router.get("/google/callback", response_model=TokenPair)
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    async with httpx.AsyncClient(timeout=10.0) as client:
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
    if not user:
        existing = await get_user_by_email(db, email)
        if existing:
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
    return TokenPair(access_token=access_token, refresh_token=refresh_token)

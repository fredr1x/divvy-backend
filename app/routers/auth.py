from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import verify_password
from app.db.session import get_db
from app.schemas.auth import LoginRequest, LogoutRequest, RefreshRequest, TokenPair
from app.schemas.user import UserCreate
from app.services.auth_service import (
    issue_token_pair,
    revoke_refresh_token,
    rotate_refresh_token,
)
from app.services.user_service import (
    create_google_user,
    create_user_local,
    get_user_by_email,
    get_user_by_google_sub,
)

router = APIRouter(prefix="/auth", tags=["auth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


@router.post("/register", response_model=TokenPair)
def register(payload: UserCreate, db: Session = Depends(get_db)) -> TokenPair:
    """
    Register a new user with email and password.

    Creates a new local user account with the provided email and password.
    Returns a token pair (access and refresh tokens) for immediate authentication.

    Args:
        payload: User creation data containing email, password, first_name, last_name
        db: Database session

    Returns:
        TokenPair: Access token and refresh token for the newly registered user

    Raises:
        HTTPException 400: If email is already registered
    """

    if get_user_by_email(db, payload.email.__str__()):
        raise HTTPException(status_code=400, detail="Email already registered")

    user = create_user_local(
        db,
        payload.email.__str__(),
        payload.password,
        payload.first_name,
        payload.last_name,
    )

    access_token, refresh_token = issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/login", response_model=TokenPair)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenPair:
    """
    Register a new user with email and password.

    Creates a new local user account with the provided email and password.
    Returns a token pair (access and refresh tokens) for immediate authentication.

    Args:
        payload: User creation data containing email, password, first_name, last_name
        db: Database session

    Returns:
        TokenPair: Access token and refresh token for the newly registered user

    Raises:
        HTTPException 400: If email is already registered
    """
    user = get_user_by_email(db, payload.email.__str__())

    if not user or not user.password:
        raise HTTPException(status_code=400, detail="Invalid credentials")

    if not verify_password(payload.password, user.password):
        raise HTTPException(status_code=400, detail="Invalid credentials")

    access_token, refresh_token = issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=TokenPair)
def refresh_token(payload: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    """
    Refresh an expired access token using a valid refresh token.

    Rotates the refresh token and issues a new access token pair.
    Maintains session continuity without re-entering credentials.

    Args:
        payload: Contains the refresh token
        db: Database session

    Returns:
        TokenPair: New access token and rotated refresh token

    Raises:
        HTTPException 401: If refresh token is invalid or expired
    """
    result = rotate_refresh_token(db, payload.refresh_token)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    access_token, refresh_token = result
    return TokenPair(access_token=access_token, refresh_token=refresh_token)


@router.post("/logout")
def logout(payload: LogoutRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    """
    Revoke the user's refresh token and logout.

    Invalidates the provided refresh token, preventing further token rotations.

    Args:
        payload: Contains the refresh token to revoke
        db: Database session

    Returns:
        dict: Contains 'revoked' boolean indicating successful revocation
    """
    revoked = revoke_refresh_token(db, payload.refresh_token)
    return {"revoked": revoked}


@router.get("/google/login")
def google_login() -> RedirectResponse:
    """
    Initiate Google OAuth2 login flow.

    Redirects user to Google's authentication server.
    Part of OAuth2 authorization code flow.

    Returns:
        RedirectResponse: Redirect to Google OAuth2 login page
    """
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
def google_callback(
    code: str = Query(...),
    db: Session = Depends(get_db),
) -> TokenPair:
    """
    Handle OAuth2 callback from Google after user authentication.

    Exchanges authorization code for ID token, verifies with Google,
    and creates or links Google account with existing user.

    Args:
        code: Authorization code from Google OAuth2
        db: Database session

    Returns:
        TokenPair: Access token and refresh token for authenticated user

    Raises:
        HTTPException 400: If Google token exchange, verification, or profile is invalid
    """
    token_response = httpx.post(
        GOOGLE_TOKEN_URL,
        data={
            "code": code,
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        },
        timeout=10.0,
    )
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google token exchange failed")

    token_data = token_response.json()
    id_token = token_data.get("id_token")
    if not id_token:
        raise HTTPException(status_code=400, detail="Google ID token missing")

    info_response = httpx.get(
        GOOGLE_TOKENINFO_URL, params={"id_token": id_token}, timeout=10.0
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

    user = get_user_by_google_sub(db, google_sub)

    if not user:
        existing = get_user_by_email(db, email)
        if existing:
            existing.google_sub = google_sub
            existing.auth_provider = "google"
            db.add(existing)
            db.refresh(existing)
            user = existing
        else:
            user = create_google_user(
                db,
                email,
                google_sub,
                first_name,
                last_name,
            )

    access_token, refresh_token = issue_token_pair(db, user)
    return TokenPair(access_token=access_token, refresh_token=refresh_token)

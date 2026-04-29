from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas import (
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    TokenPair,
    UserCreate,
)
from app.services.auth.auth_service import (
    get_google_login_redirect,
    handle_google_callback,
    login_user,
    logout_user,
    refresh_user_token,
    register_user,
    verify_user_email_token,
    resend_verification_email,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenPair)
async def register(
    request: Request,
    payload: UserCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """
    Register a new user with email and password.

    Creates a local user account, sends a verification email in the background,
    and issues a token pair upon successful registration.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        payload: Registration data including email, password, first and last name
        background_tasks: FastAPI background task runner for sending verification email
        db: Database session

    Returns:
        TokenPair: Access and refresh tokens for the newly created user

    Raises:
        HTTPException 400: If the email is already registered
    """
    return await register_user(request, payload, background_tasks, db)


@router.get("/verify/{token}")
async def verify_user_email(token: str, db: AsyncSession = Depends(get_db)):
    """
    Verify a user's email address via a URL-safe token.

    Decodes the token from the verification link sent to the user's email,
    finds the corresponding user, and marks their account as verified.

    Args:
        token: URL-safe encoded token containing the user's email
        db: Database session

    Returns:
        HTMLResponse 200: Confirmation page with a link to the app if verification succeeds
        HTMLResponse 400: Failure page if the token does not contain a valid email

    Raises:
        HTTPException 404: If no user is found for the email in the token
    """
    return await verify_user_email_token(token, db)


@router.post("/resend-verification/{email}")
async def resend_verification(
    email: str,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    return await resend_verification_email(db, email, background_tasks)


@router.post("/login", response_model=TokenPair)
async def login(
    request: Request, payload: LoginRequest, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """
    Authenticate a user with email and password.

    Validates the provided credentials against the stored password hash
    and issues a new token pair on success. All attempts are audit-logged.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        payload: Login data containing email and password
        db: Database session

    Returns:
        TokenPair: Access and refresh tokens for the authenticated user

    Raises:
        HTTPException 400: If credentials are invalid or the user does not exist
    """
    return await login_user(request, payload, db)


@router.post("/refresh", response_model=TokenPair)
async def refresh_token(
    request: Request, payload: RefreshRequest, db: AsyncSession = Depends(get_db)
) -> TokenPair:
    """
    Rotate a refresh token and issue a new token pair.

    Validates the provided refresh token, invalidates it, and returns a
    freshly issued access and refresh token pair (token rotation).

    Args:
        request: The incoming HTTP request (used for IP address logging)
        payload: Request body containing the current refresh token
        db: Database session

    Returns:
        TokenPair: New access and refresh tokens

    Raises:
        HTTPException 401: If the refresh token is invalid or already revoked
    """
    return await refresh_user_token(request, payload, db)


@router.post("/logout")
async def logout(
    request: Request, payload: LogoutRequest, db: AsyncSession = Depends(get_db)
) -> dict[str, bool]:
    """
    Log out a user by revoking their refresh token.

    Marks the provided refresh token as revoked in the database so it
    can no longer be used to obtain new access tokens.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        payload: Request body containing the refresh token to revoke
        db: Database session

    Returns:
        dict[str, bool]: {"revoked": True} on success, {"revoked": False} on failure
    """
    return await logout_user(request, payload, db)


@router.get("/google/login")
async def google_login() -> RedirectResponse:
    """
    Initiate the Google OAuth2 authorization flow.

    Builds the Google authorization URL with the required scopes and
    parameters, then redirects the user to Google's consent screen.

    Returns:
        RedirectResponse: Redirect to Google's OAuth2 authorization endpoint
    """
    return get_google_login_redirect()


@router.get("/google/callback", response_model=TokenPair)
async def google_callback(
    code: str = Query(...),
    db: AsyncSession = Depends(get_db),
) -> TokenPair:
    """
    Handle the Google OAuth2 callback and authenticate the user.

    Exchanges the authorization code for tokens, verifies the ID token
    with Google, and either retrieves an existing user, links the Google
    account to an existing email, or creates a new user. Issues a token pair
    upon completion.

    Args:
        code: Authorization code returned by Google after user consent
        db: Database session

    Returns:
        TokenPair: Access and refresh tokens for the authenticated user

    Raises:
        HTTPException 400: If the token exchange fails, the ID token is missing or invalid,
                           the Google audience does not match, or the profile is incomplete
    """
    return await handle_google_callback(code, db)

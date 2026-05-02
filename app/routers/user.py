from app.models import User
from app.schemas import UserUpdate, ChangePasswordRequest, UserRead
from fastapi import APIRouter, Depends, status, Request
from app.dependencies import get_current_verified_user, get_ip_address, get_db
from app.services.user.user_service import (
    update_user as update_user_service,
    delete_user_account as delete_user_account_service,
    change_password as change_password_service,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

router = APIRouter(prefix="/users", tags=["users"])

@router.patch("")
async def update_user(
    request: Request,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await update_user_service(get_ip_address(request), payload, current_user, db)


@router.post("/change-password")
async def change_password(
    request: Request,
    payload: ChangePasswordRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> UserRead:
    """
    Change the password for the current user.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        payload: Request body containing current_password and new_password
        db: Database session
        current_user: The authenticated and verified user

    Returns:
        UserRead: Updated user details after password change

    Raises:
        HTTPException 400: If user is OAuth-only or password is incorrect
    """
    return await change_password_service(
        get_ip_address(request),
        current_user,
        payload.current_password,
        payload.new_password,
        db,
    )


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    await delete_user_account_service(get_ip_address(request), db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

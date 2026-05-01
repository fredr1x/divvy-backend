from app.models import User
from app.schemas import UserUpdate
from fastapi import APIRouter, Depends, status, Request
from app.dependencies import get_current_verified_user, get_ip_address, get_db
from app.services.user.user_service import (
    update_user as update_user_service,
    delete_user_account as delete_user_account_service,
)
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import Response

router = APIRouter(prefix="/users", tags=["users"])

@router.patch("/")
async def update_user(
    request: Request,
    payload: UserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await update_user_service(get_ip_address(request), payload, current_user, db)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user)
):
    await delete_user_account_service(get_ip_address(request), db, current_user)
    return Response(status_code=status.HTTP_204_NO_CONTENT)

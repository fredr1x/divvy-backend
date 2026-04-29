from app.db.session import get_db
from app.dependencies import get_current_verified_user, get_ip_address
from app.models import User
from app.schemas import GroupMediaRead
from app.services.group.group_media_service import (
    get_all_group_media,
    get_group_media,
    upload_receipt as upload_receipt_service,
    upload_photo as upload_photo_service,
)
from fastapi import APIRouter, Depends, File, UploadFile, Request
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/group-media", tags=["group media"])


@router.get("/{id}")
async def get_group_media_by_id(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> GroupMediaRead:
    return await get_group_media(id, db, current_user.id)


@router.get("/group/{group_id}")
async def get_all_by_group_id(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> list[GroupMediaRead]:
    return await get_all_group_media(group_id, db, current_user.id)


@router.post("/receipt")
async def upload_receipt(
    request: Request,
    group_id: int,
    expense_id: int | None = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    files: list[UploadFile] = File(...),
):
    return await upload_receipt_service(
        ip_address=get_ip_address(request),
        group_id=group_id,
        expense_id=expense_id,
        db=db,
        current_user=current_user,
        files=files,
    )


@router.post("/photo")
async def upload_photo(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
    files: list[UploadFile] = File(...),
):
    return await upload_photo_service(
        ip_address=get_ip_address(request),
        group_id=group_id,
        db=db,
        current_user=current_user,
        files=files,
    )

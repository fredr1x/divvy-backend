from fastapi import APIRouter, Depends, File, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user, get_ip_address
from app.models import User
from app.schemas import GroupMediaRead
from app.services.group.group_media_service import (
    get_all_group_media,
    get_group_media,
)
from app.services.group.group_media_service import (
    upload_photo as upload_photo_service,
)
from app.services.group.group_media_service import (
    upload_receipt as upload_receipt_service,
)

router = APIRouter(prefix="/group-media", tags=["group media"])


@router.get("/{id}")
async def get_group_media_by_id(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> GroupMediaRead:
    """
    Retrieve a single group media item by its ID.

    Fetches a specific media record and verifies that the current user
    is a member of the group it belongs to.

    Args:
        id: The ID of the group media record
        db: Database session
        current_user: The authenticated and verified user

    Returns:
        GroupMediaRead: The requested group media item

    Raises:
        HTTPException 403: If the current user is not a member of the associated group
        HTTPException 404: If the media record is not found
    """
    return await get_group_media(id, db, current_user.id)


@router.get("/group/{group_id}")
async def get_all_by_group_id(
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> list[GroupMediaRead]:
    """
    Retrieve all media items belonging to a group.

    Returns every media record associated with the specified group,
    provided the current user is a member of that group.

    Args:
        group_id: The ID of the group whose media to retrieve
        db: Database session
        current_user: The authenticated and verified user

    Returns:
        list[GroupMediaRead]: All media items associated with the group

    Raises:
        HTTPException 403: If the current user is not a member of the group
        HTTPException 404: If the group is not found
    """
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
    """
    Upload one or more receipt images for a group, optionally linked to an expense.

    Stores the uploaded files as receipt media records associated with the
    given group. If an expense ID is provided, the receipts are also linked
    to that specific expense.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        group_id: The ID of the group to associate the receipts with
        expense_id: Optional ID of the expense to link the receipts to
        db: Database session
        current_user: The authenticated and verified user
        files: One or more uploaded receipt image files

    Returns:
        list[GroupMediaRead]: The created media records for all uploaded receipts

    Raises:
        HTTPException 403: If the current user is not a member of the group
        HTTPException 404: If the group or expense is not found
    """
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
    """
    Upload one or more photos for a group.

    Stores the uploaded files as photo media records associated with
    the given group.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        group_id: The ID of the group to associate the photos with
        db: Database session
        current_user: The authenticated and verified user
        files: One or more uploaded image files

    Returns:
        list[GroupMediaRead]: The created media records for all uploaded photos

    Raises:
        HTTPException 403: If the current user is not a member of the group
        HTTPException 404: If the group is not found
    """
    return await upload_photo_service(
        ip_address=get_ip_address(request),
        group_id=group_id,
        db=db,
        current_user=current_user,
        files=files,
    )

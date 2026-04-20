from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.schemas import GroupMediaRead
from app.services.group.group_media_service import (
    get_all_group_media,
    get_group_media,
    upload_expense_receipt,
)

router = APIRouter(prefix="/group-media", tags=["group media"])


@router.get("/{id}")
def get_group_media_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupMediaRead:
    return get_group_media(id, db, current_user.id)


@router.get("/group/{group_id}")
def get_all_by_group_id(
    group_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[GroupMediaRead]:
    return get_all_group_media(group_id, db, current_user.id)


@router.post("/receipt")
def upload_receipt(
    group_id: int,
    expense_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    files: list[UploadFile] = File(...),
):
    return upload_expense_receipt(
        group_id=group_id,
        expense_id=expense_id,
        db=db,
        current_user=current_user,
        files=files,
    )

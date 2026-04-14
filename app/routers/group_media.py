from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.enums.media_category import MediaCategory
from app.schemas import GroupMediaCreate, GroupMediaRead
from app.services.group.group_media_service import (
    create_group_media,
    get_all_group_media,
    get_group_media,
)
from app.services.minio.minio_service import minio_service

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
    created_media = []

    for f in files:
        key: str = minio_service.generate_object_key(
            group_id, MediaCategory.RECEIPT.name, f.filename
        )

        payload = GroupMediaCreate(
            group_id=group_id,
            uploaded_by=current_user.id,
            expense_id=expense_id,
            file_url=key,
            category=MediaCategory.RECEIPT,
        )

        minio_service.upload(f.file.read(), key, f.content_type)

        created = create_group_media(
            db,
            payload,
        )
        created_media.append(created)

    return {"items": created_media}

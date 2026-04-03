from fastapi import APIRouter
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.dependencies import get_current_user
from app.services.minio_service import minio_service
from app.services.group_media_service import validate_user_access

router = APIRouter(prefix="/minio", tags=["minio"])


@router.get("/media")
def get_media(
    key: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    validate_user_access(key, current_user.id, db)

    return minio_service.get_file_stream(key)

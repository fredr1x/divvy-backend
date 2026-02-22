from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.group import GroupCreate, GroupRead, GroupUpdate
from app.services.group_service import (
    get_group_by_id as get_group_by_id_service,
    create_group as create_group_service,
    update_group as update_group_service, get_invitation_link_by_group_id
)

router = APIRouter(prefix="/groups", tags=["groups"])

@router.get("/{id}", response_model=GroupRead)
def get_group_by_id(
        id: int,
        db: Session = Depends(get_db)
) -> GroupRead:
    return get_group_by_id_service(db, id=id)

@router.post("/create-group", response_model=GroupRead)
def create_group(
        payload: GroupCreate,
        db: Session = Depends(get_db)
) -> GroupRead:
    return create_group_service(db, payload.name, payload.creator_id, payload.currency)

@router.put("/{id}", response_model=GroupRead)
def update_group(
        payload: GroupUpdate,
        db: Session = Depends(get_db)
) -> GroupRead:
    return update_group_service(db, payload)

@router.get("/invitation-link-by-group-id/{id}")
def invitation_link_by_group_id(
        id: int,
        db: Session = Depends(get_db)
) -> str:
    return get_invitation_link_by_group_id(db, id)

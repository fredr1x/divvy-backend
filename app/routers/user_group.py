from fastapi import APIRouter, Depends

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user

from app.models.user import User

from app.schemas.user_group import UserGroupRead, UserGroupAddMemberByEmail
from app.schemas.user import UserRead

from app.services.user_group_service import (get_group_members,
                                             invite_to_group_by_email as add_to_group_by_email_service,
                                             join_by_invitation_link as join_by_invitation_link_service)

router = APIRouter(prefix="/user-groups", tags=["user group"])

@router.get("/by-group-id/{id}")
def get_group_members_by_group_id(
        id: int,
        db: Session = Depends(get_db)
)-> list[UserRead]:
    return get_group_members(db, id)

@router.post("/invite-by-email", response_model=UserGroupRead)
def invite_to_group_by_email(
        payload: UserGroupAddMemberByEmail,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
) -> UserGroupRead:
    return add_to_group_by_email_service(db, payload, current_user)

@router.post("/invite/{link}")
def join_by_invitation_link(
        link: str,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    return join_by_invitation_link_service(db, link, current_user)

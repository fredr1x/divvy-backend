from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.user import UserRead
from app.schemas.user_group import UserGroupAddMemberByEmail, UserGroupRead
from app.services.user.user_group_service import (
    get_group_members,
)
from app.services.user.user_group_service import (
    invite_to_group_by_email as add_to_group_by_email_service,
)
from app.services.user.user_group_service import (
    join_by_invitation_link as join_by_invitation_link_service,
)

router = APIRouter(prefix="/user-groups", tags=["user group"])


@router.get("/by-group-id/{id}")
async def get_group_members_by_group_id(
    id: int, db: AsyncSession = Depends(get_db)
) -> list[UserRead]:
    """
    Retrieve all members of a group.

    Lists all users that are part of the specified group.

    Args:
        id: The group ID
        db: Database session

    Returns:
        list[UserRead]: List of users in the group
    """
    return await get_group_members(db, id)


@router.post("/invite-by-email", response_model=UserGroupRead)
async def invite_to_group_by_email(
    payload: UserGroupAddMemberByEmail,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> UserGroupRead:
    """
    Invite a user to group by email address.

    Sends an invitation to join a group to the specified email.
    Can create user if they don't exist or add to group if they do.
    Current user must have permission to invite.

    Args:
        payload: Contains email and group information
        db: Database session
        current_user: The user making the invitation

    Returns:
        UserGroupRead: The created user-group relationship
    """
    return await add_to_group_by_email_service(db, payload, current_user)


@router.post("/invite/{link}")
async def join_by_invitation_link(
    link: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Join a group using an invitation link.

    Allows a user to join a group by providing a valid invitation link.
    User must be authenticated.

    Args:
        link: The invitation link string
        db: Database session
        current_user: The authenticated user joining the group

    Returns:
        Confirmation of group membership

    Raises:
        HTTPException 400: If invitation link is invalid or expired
    """
    return await join_by_invitation_link_service(db, link, current_user)

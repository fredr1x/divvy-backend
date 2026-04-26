from app.dependencies import get_current_user, get_ip_address
from app.models import User
from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.group import GroupCreate, GroupRead, GroupUpdate
from app.services.group.group_service import (
    create_group as create_group_service,
)
from app.services.group.group_service import (
    get_group_by_id as get_group_by_id_service,
)
from app.services.group.group_service import (
    get_invitation_link_by_group_id,
)
from app.services.group.group_service import (
    update_group as update_group_service,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.get("/{id}", response_model=GroupRead)
async def get_group_by_id(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    """
    Retrieve group details by ID.

    Fetches all information about a specific group including name and settings.

    Args:
        request
        id: The group ID
        db: Database session
        current_user

    Returns:
        GroupRead: Group information

    Raises:
        HTTPException 404: If group not found
    """
    return await get_group_by_id_service(get_ip_address(request), db, id, current_user)


@router.post("/create-group", response_model=GroupRead)
async def create_group(
    request: Request,
    payload: GroupCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    """
    Create a new expense group.

    Creates a group for tracking shared expenses and managing splits
    with the specified creator and currency.

    Args:
        request
        payload: Group creation data with name, creator_id, and currency
        db: Database session
        current_user

    Returns:
        GroupRead: The newly created group
    """
    return await create_group_service(get_ip_address(request),
                                      db,
                                      payload.name,
                                      payload.creator_id,
                                      payload.currency,
                                      current_user
                                      )


@router.put("/{id}", response_model=GroupRead)
async def update_group(
    request: Request,
    id: int,
    payload: GroupUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupRead:
    """
    Update group information.

    Modifies group settings such as name, description, or other properties.

    Args:
        payload: Updated group data
        db: Database session

    Returns:
        GroupRead: The updated group

    Raises:
        HTTPException 404: If group not found
    """
    return await update_group_service(get_ip_address(request),
                                      db,
                                      id,
                                      payload,
                                      current_user,
                                      )


@router.get("/invitation-link-by-group-id/{id}")
async def invitation_link_by_group_id(
    request: Request,
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> str:
    """
    Generate or retrieve invitation link for a group.

    Creates a shareable link that allows other users to join the group
    without needing explicit user invitation.

    Args:
        request
        id: The group ID
        db: Database session
        current_user

    Returns:
        str: The invitation/join link

    Raises:
        HTTPException 404: If group not found
    """
    return await get_invitation_link_by_group_id(get_ip_address(request), db, id, current_user)

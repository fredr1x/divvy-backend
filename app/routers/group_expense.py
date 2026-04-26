from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_user, get_ip_address
from app.models import User
from app.schemas import (
    GroupExpenseCreate,
    GroupExpenseRead,
    GroupExpenseUpdate,
)
from app.services.expense.group_expense_service import (
    create_group_expense as create_group_expense_service,
)
from app.services.expense.group_expense_service import (
    get_group_expense_by_group_id as get_group_expense_service,
)
from app.services.expense.group_expense_service import (
    update_group_expense as update_group_expense_service,
)


router = APIRouter(prefix="/group-expenses", tags=["group expenses"])


@router.get("/{group_id}", status_code=200)
async def get_group_expenses(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> list[GroupExpenseRead]:
    """
    Retrieve all expenses for a specific group.

    Lists all expenses that have been added to the group for tracking
    and split calculations.

    Args:
        group_id: The group ID
        db: Database session

    Returns:
        list[GroupExpenseRead]: List of expenses in the group

    Raises:
        HTTPException 404: If group not found
    """
    return await get_group_expense_service(get_ip_address(request), db, group_id, current_user)


@router.post("", status_code=201)
async def create_group_expense(
    request: Request,
    payload: GroupExpenseCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> GroupExpenseRead:
    """
    Create a new expense in a group.

    Records a new expense that needs to be split among group members.

    Args:
        payload: Expense details including amount, description, and payer
        db: Database session

    Returns:
        GroupExpenseRead: The newly created expense
    """
    return await create_group_expense_service(get_ip_address(request), db, current_user, payload)


@router.put("", status_code=200)
async def update_group_expense(
    request: Request,
    payload: GroupExpenseUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
) -> GroupExpenseRead:
    """
    Update an existing expense.

    Modifies expense details. Only the user who created the expense
    or group admins can update it.

    Args:
        payload: Updated expense data
        db: Database session
        user: The authenticated user making the update

    Returns:
        GroupExpenseRead: The updated expense

    Raises:
        HTTPException 403: If user lacks permission to update
        HTTPException 404: If expense not found
    """
    return await update_group_expense_service(get_ip_address(request),
                                              db,
                                              payload,
                                              user.id
                                              )

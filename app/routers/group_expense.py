from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
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
def get_group_expenses(
    group_id: int, db: Session = Depends(get_db)
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
    return get_group_expense_service(group_id, db)


@router.post("", status_code=201)
def create_group_expense(
    payload: GroupExpenseCreate,
    db: Session = Depends(get_db),
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
    return create_group_expense_service(db, payload)


@router.put("", status_code=200)
def update_group_expense(
    payload: GroupExpenseUpdate,
    db: Session = Depends(get_db),
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
    return update_group_expense_service(db, payload, user.id)

from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user
from app.models.user import User
from app.schemas import AllExpensesByGroupAndUser, ExpenseSplitBalances
from app.services.expense.expense_split_service import (
    get_all_expenses_by_group_id_and_user_id,
    get_balances as get_balances_service
)
from app.dependencies import get_ip_address


router = APIRouter(prefix="/expense-split", tags=["expense split"])


@router.get("/get-all/{group_id}")
async def get_all_by_group_id(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> AllExpensesByGroupAndUser:
    """
    Retrieve all expenses and splits for a group from current user's perspective.

    Gets detailed information about expenses in the group and how much
    the current user owes or is owed.

    Args:
        group_id: The group ID
        db: Database session
        current_user: The authenticated user

    Returns:
        AllExpensesByGroupAndUser: Expenses and settlement amounts

    Raises:
        HTTPException 404: If group not found
    """
    return await get_all_expenses_by_group_id_and_user_id(get_ip_address(request), db, group_id, current_user.id)


@router.get("/{group_id}/balances")
async def get_balances(
    request: Request,
    group_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
)-> ExpenseSplitBalances:
    """
    Retrieve settlement balances for all members in a group.

    Computes who owes whom in the specified group and returns
    aggregated balances from the perspective of the current user.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        group_id: The ID of the group to calculate balances for
        db: Database session
        current_user: The authenticated and verified user

    Returns:
        ExpenseSplitBalances: Calculated debtor/creditor balances for the group

    Raises:
        HTTPException 403: If the current user has no access to the group
        HTTPException 404: If the group is not found
    """
    return await get_balances_service(get_ip_address(request), group_id, current_user, db)

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import GroupExpense
from app.schemas.group_expense import (
    GroupExpenseCreate,
    GroupExpenseRead,
    GroupExpenseUpdate,
)
from app.services.expense.expense_split_service import (
    create_expense_split,
    update_expense_split,
)
from app.services.item.item_service import create_items_from_list, update_items_from_list
from app.services.user.user_group_service import get_group_by_id, is_member_of_group
from app.services.user.user_service import get_user_by_id


async def get_group_expense_by_id(
    db: AsyncSession, group_expense_id: int
) -> GroupExpense:
    group_expense: GroupExpense = await db.scalar(
        select(GroupExpense).where(GroupExpense.id == group_expense_id)
    )

    if not group_expense:
        raise HTTPException(status_code=404, detail="Group expense not found")
    return group_expense


async def get_group_expense_by_group_id(
    db: AsyncSession, group_id: int
) -> list[GroupExpenseRead]:
    stmt = (
        select(GroupExpense)
        .where(GroupExpense.group_id == group_id)
        .options(selectinload(GroupExpense.splits))
        .order_by(GroupExpense.created_at.desc())
    )
    group_expenses = (await db.scalars(stmt)).all()
    return [GroupExpenseRead.model_validate(exp) for exp in group_expenses]


async def create_group_expense(
    db: AsyncSession, payload: GroupExpenseCreate
) -> GroupExpenseRead:
    group = await get_group_by_id(db, payload.group_id)
    payer = await get_user_by_id(db, payload.payer_id)
    creator = await get_user_by_id(db, payload.created_by)

    if not payer or not creator:
        raise HTTPException(status_code=404, detail="User not found")

    if not await is_member_of_group(db, group.id, payer.id):
        raise HTTPException(
            status_code=400, detail="Payer is not a member of this group"
        )

    if not await is_member_of_group(db, group.id, creator.id):
        raise HTTPException(
            status_code=403, detail="Creator is not a member of this group"
        )

    group_expense = GroupExpense(
        payer_id=payer.id,
        group_id=group.id,
        created_by=payload.created_by,
        name=payload.name,
        currency=payload.currency or group.currency,
        total_amount=payload.total_amount,
        share_type=payload.share_type,
    )

    db.add(group_expense)
    await db.flush()

    await create_expense_split(db, payload, group_expense)
    await create_items_from_list(db, group_expense.id, payload.expense_items)

    await db.commit()

    group_expense = await db.scalar(select(GroupExpense)
        .options(
            selectinload(GroupExpense.splits),
            selectinload(GroupExpense.items),
        )
        .where(GroupExpense.id == group_expense.id))

    return GroupExpenseRead.model_validate(group_expense)


async def update_group_expense(
    db: AsyncSession, payload: GroupExpenseUpdate, current_user_id: int
) -> GroupExpenseRead:
    group_expense: GroupExpense = await db.scalar(
        select(GroupExpense).where(GroupExpense.id == payload.id)
    )

    if not group_expense:
        raise HTTPException(status_code=404, detail="Group expense not found")

    if not await is_member_of_group(db, group_expense.group_id, current_user_id):
        raise HTTPException(status_code=403, detail="You are not a member of the group")

    exclude_fields = {
        "expense_members",
        "expense_items",
        "exact_share_amount",
        "percentage_share_amount",
    }

    updates = payload.model_dump(exclude_unset=True, exclude=exclude_fields)
    for key, value in updates.items():
        setattr(group_expense, key, value)

    db.add(group_expense)
    await db.flush()

    await update_expense_split(db, group_expense, payload)
    await update_items_from_list(db, group_expense.id, payload.expense_items)

    await db.refresh(group_expense)

    return GroupExpenseRead.model_validate(group_expense)

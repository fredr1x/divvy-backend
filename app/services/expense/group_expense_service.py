from app.models import GroupExpense, User, AuditLog
from app.models.item import Item
from app.models.enums import ActionType, ActionStatus
from app.schemas.group_expense import (
    GroupExpenseCreate,
    GroupExpenseRead,
    GroupExpenseUpdate,
)
from app.services.audit.audit_logs_service import create_failed_audit_log
from app.services.expense.expense_split_service import (
    create_expense_split,
    update_expense_split,
)
from app.services.item.item_service import create_items_from_list, update_items_from_list
from app.services.user.user_group_service import get_group_by_id, is_member_of_group
from app.services.user.user_service import get_user_by_id
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def get_group_expense_by_id(
    ip_address: str,
    db: AsyncSession,
    current_user_id: int,
    group_expense_id: int
) -> GroupExpense:

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="GROUP_EXPENSE",
    )

    group_expense: GroupExpense = await db.scalar(
        select(GroupExpense).where(GroupExpense.id == group_expense_id)
    )

    if not group_expense:
        message="Group expense not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id=group_expense.id
    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Successfully retrieved group expense"

    db.add(audit_log)
    await db.commit()

    return group_expense


async def get_group_expense_by_group_id(
    ip_address: str,
    db: AsyncSession,
    group_id: int,
    current_user: User
) -> list[GroupExpenseRead]:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="GROUP_EXPENSE",
    )

    stmt = (
        select(GroupExpense)
        .where(GroupExpense.group_id == group_id)
        .options(
            selectinload(GroupExpense.splits),
            selectinload(GroupExpense.items).selectinload(Item.item_splits),
        )
        .order_by(GroupExpense.created_at.desc())
    )
    group_expenses = (await db.scalars(stmt)).all()

    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Successfully retrieved group expenses"

    db.add(audit_log)
    await db.commit()

    return [_to_group_expense_read(exp) for exp in group_expenses]


async def create_group_expense(
    ip_address: str,
    db: AsyncSession,
    current_user: User,
    payload: GroupExpenseCreate
) -> GroupExpenseRead:
    group = await get_group_by_id(db, payload.group_id)
    payer = await get_user_by_id(db, payload.payer_id)
    creator = await get_user_by_id(db, current_user.id)

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.CREATE,
        ip_address=ip_address,
        entity_name="GROUP_EXPENSE, EXPENSE_SPLIT, SPLIT_ITEM",
    )

    if not payer or not creator:
        message="User not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    if not await is_member_of_group(db, group.id, payer.id):
        message="Payer is not a member of this group"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    if not await is_member_of_group(db, group.id, creator.id):
        message="Creator is not a member of this group"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=403, detail=message)

    group_expense = GroupExpense(
        payer_id=payer.id,
        group_id=group.id,
        created_by=current_user.id,
        name=payload.name,
        currency=payload.currency or group.currency,
        total_amount=payload.total_amount,
        share_type=payload.share_type,
    )

    db.add(group_expense)
    await db.flush()
    await db.refresh(group_expense)
    await db.flush()

    await create_expense_split(ip_address, db, payload, group_expense, current_user)
    await create_items_from_list(ip_address, db, group_expense.id, payload.expense_items, current_user)

    audit_log.entity_id=group_expense.id
    audit_log.message="Successfully created group expense"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    group_expense = await db.scalar(select(GroupExpense)
        .options(
            selectinload(GroupExpense.splits),
            selectinload(GroupExpense.items).selectinload(Item.item_splits),
        )
        .where(GroupExpense.id == group_expense.id))

    return _to_group_expense_read(group_expense)


async def update_group_expense(
    ip_address: str,
    db: AsyncSession,
    payload: GroupExpenseUpdate,
    current_user_id: int
) -> GroupExpenseRead:
    group_expense: GroupExpense = await db.scalar(
        select(GroupExpense).where(GroupExpense.id == payload.id)
    )

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="GROUP_EXPENSE, EXPENSE_SPLIT, SPLIT_ITEM",
    )

    if not group_expense:
        message="Group expense not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    if not await is_member_of_group(db, group_expense.group_id, current_user_id):
        message="You are not a member of the group"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=403, detail=message)

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

    await update_expense_split(ip_address, db, group_expense, payload, current_user_id)
    await update_items_from_list(ip_address, db, group_expense.id, current_user_id, payload.expense_items)

    audit_log.entity_id=group_expense.id
    audit_log.message="Successfully updated group expense"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    group_expense = await db.scalar(
        select(GroupExpense)
        .options(
            selectinload(GroupExpense.splits),
            selectinload(GroupExpense.items).selectinload(Item.item_splits),
        )
        .where(GroupExpense.id == group_expense.id)
    )

    return _to_group_expense_read(group_expense)


def _to_group_expense_read(group_expense: GroupExpense) -> GroupExpenseRead:
    return GroupExpenseRead(
        id=group_expense.id,
        payer_id=group_expense.payer_id,
        group_id=group_expense.group_id,
        name=group_expense.name,
        total_amount=group_expense.total_amount,
        created_by=group_expense.created_by,
        created_at=group_expense.created_at,
        splits=group_expense.splits,
        items=group_expense.items,
        item_splits={
            item.id: [item_split.user_id for item_split in item.item_splits]
            for item in group_expense.items
        },
    )

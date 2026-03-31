from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import GroupExpense
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseRead, GroupExpenseUpdate
from app.services.expense_split_service import create_expense_split, update_expense_split
from app.services.user_group_service import is_member_of_group, get_group_by_id
from app.services.user_service import get_user_by_id
from app.services.item_service import create_items_from_list, update_items_from_list


def get_group_expense_by_id(
        db: Session,
        group_expense_id: int
)-> GroupExpense:
    group_expense: GroupExpense = db.scalar(select(GroupExpense).where(GroupExpense.id == group_expense_id))

    if not group_expense:
        raise HTTPException(status_code=404, detail="Group expense not found")
    return group_expense


def get_group_expense_by_group_id(
        db: Session,
        group_id: int
) -> list[GroupExpenseRead]:
    stmt = (
        select(GroupExpense)
        .where(GroupExpense.group_id == group_id)
        .options(selectinload(GroupExpense.splits))
        .order_by(GroupExpense.created_at.desc())
    )

    group_expenses = db.scalars(stmt).all()
    return [GroupExpenseRead.model_validate(exp) for exp in group_expenses]

def create_group_expense(
        db: Session,
        payload: GroupExpenseCreate
) -> GroupExpenseRead:

    group = get_group_by_id(db, payload.group_id)
    payer = get_user_by_id(db, payload.payer_id)
    creator = get_user_by_id(db, payload.created_by)

    if not is_member_of_group(db, group.id, payer.id):
        raise HTTPException(status_code=400, detail="Payer is not a member of this group")

    if not is_member_of_group(db, group.id, creator.id):
        raise HTTPException(status_code=403, detail="Creator is not a member of this group")

    group_expense = GroupExpense(
        payer_id=payer.id,
        group_id=group.id,
        created_by=payload.created_by,
        name=payload.name,
        currency=payload.currency or group.currency,
        total_amount=payload.total_amount,
        share_type=payload.share_type
    )

    db.add(group_expense)
    db.flush()
    create_expense_split(db, payload, group_expense)
    create_items_from_list(db, group_expense.id, payload.expense_items)
    db.refresh(group_expense)
    return GroupExpenseRead.model_validate(group_expense)


def update_group_expense(
        db: Session,
        payload: GroupExpenseUpdate,
        current_user_id: int
) -> GroupExpenseRead:

    group_expense: GroupExpense = db.scalar(select(GroupExpense).where(GroupExpense.id == payload.id))

    if not group_expense:
        raise HTTPException(status_code=404, detail="Group expense not found")

    if not is_member_of_group(db, group_expense.group_id, current_user_id):
        raise HTTPException(status_code=403, detail="You are not a member of the group")

    exclude_fields = {"expense_members", "expense_items", "exact_share_amount", "percentage_share_amount"}
    updates = payload.model_dump(exclude_unset=True, exclude=exclude_fields)
    for key, value in updates.items():
        setattr(group_expense, key, value)

    db.add(group_expense)
    db.flush()

    update_expense_split(db, group_expense, payload)
    update_items_from_list(db, group_expense.id, payload.expense_items)
    db.refresh(group_expense)
    return GroupExpenseRead.model_validate(group_expense)

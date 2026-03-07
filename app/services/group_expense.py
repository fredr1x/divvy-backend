from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload


from app.models import GroupExpense
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseRead, GroupExpenseUpdate
from app.services.expense_split_service import create_expense_split, update_expense_split
from app.services.user_group_service import is_member_of_group

def get_group_expense(
        group_id: int,
        db: Session
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
    group_expense = GroupExpense(
        payer_id=payload.payer_id,
        group_id=payload.group_id,
        created_by=payload.created_by,
        name=payload.name,
        total_amount=payload.total_amount
    )

    db.add(group_expense)
    db.flush()
    create_expense_split(db, payload, group_expense.id)
    db.commit()
    db.refresh(group_expense)
    return GroupExpenseRead.model_validate(group_expense)


def update_group_expense(
        db: Session,
        payload: GroupExpenseUpdate,
        current_user_id: int
) -> GroupExpenseRead:
    find_group_expense_by_id = select(GroupExpense).where(GroupExpense.id == payload.id)

    group_expense = db.scalar(find_group_expense_by_id)

    if not group_expense:
        raise HTTPException(status_code=404, detail="Group expense not found")

    if not is_member_of_group(db, group_expense.group_id, current_user_id):
        raise HTTPException(status_code=403, detail="You are not a member of the group")

    updates = payload.model_dump(exclude_unset=True)
    for key, value in updates.items():
        setattr(group_expense, key, value)

    db.add(group_expense)
    db.commit()
    db.refresh(group_expense)
    update_expense_split(db, group_expense, payload)
    return group_expense

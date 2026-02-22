from sqlalchemy.orm import Session

from app.models import GroupExpense
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseRead
from app.services.expense_split_service import create_expense_split


def create_expense(
        db: Session,
        payload: GroupExpenseCreate
) -> GroupExpenseRead:
    group_expense = GroupExpense(
        payer_id=payload.payer_id,
        group_id=payload.group_id,
        created_by=payload.created_by,
        name=payload.name
    )

    db.add(group_expense)
    db.flush()
    create_expense_split(db, payload, group_expense.id)
    db.commit()
    db.refresh(group_expense)
    return group_expense

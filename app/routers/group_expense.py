from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.dependencies import get_current_user

from app.db.session import get_db
from app.models import User
from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseRead, GroupExpenseUpdate
from app.services.group_expense import (create_group_expense as create_group_expense_service,
                                        get_group_expense as get_group_expense_service,
                                        update_group_expense as update_group_expense_service)

router = APIRouter(prefix="/group-expenses", tags=["group expenses"])


@router.get("/{group_id}", status_code=200)
def get_group_expenses(
    group_id: int,
    db: Session = Depends(get_db)
) -> list[GroupExpenseRead]:
    return get_group_expense_service(db, group_id)


@router.post("", status_code=201)
def create_group_expense(
        payload: GroupExpenseCreate,
        db: Session = Depends(get_db),
) -> GroupExpenseRead:
    return create_group_expense_service(db, payload)


@router.put("", status_code=200)
def update_group_expense(payload: GroupExpenseUpdate,
                         db: Session = Depends(get_db),
                         user: User = Depends(get_current_user)
) -> GroupExpenseRead:
    return update_group_expense_service(db, payload, user.id)



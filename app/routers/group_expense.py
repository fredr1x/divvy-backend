from fastapi import APIRouter, Depends
from rich import status

from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user

from app.schemas.group_expense import GroupExpenseCreate, GroupExpenseRead

from app.services.group_expense import (create_expense)

router = APIRouter(prefix="/group-expenses", tags=["group expenses"])

@router.post("", status_code=201, tags=["group expenses"])
def create_group_expense(
        payload: GroupExpenseCreate,
        db: Session = Depends(get_db),
) -> GroupExpenseRead:
    return create_expense(db, payload)

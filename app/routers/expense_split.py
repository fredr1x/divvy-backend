from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas import AllExpensesByGroupAndUser
from app.services.expense_split_service import get_all_expenses_by_group_id_and_user_id

router = APIRouter(prefix="/expense-split", tags=["expense split"])


@router.get("/get-all/{group_id}")
def get_all_by_group_id(
        group_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
) -> AllExpensesByGroupAndUser:
    return get_all_expenses_by_group_id_and_user_id(db, group_id, current_user.id)

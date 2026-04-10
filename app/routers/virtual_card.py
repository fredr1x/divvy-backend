from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies import get_current_user
from app.models.user import User
from app.schemas.virtual_card import VirtualCardRead, VirtualCardDeposit, PayDebtRequest, PayDebtResponse
from app.services.virtual_card_service import (
    create_virtual_card as create_virtual_card_service,
    deposit_virtual_card as deposit_virtual_card_service,
    pay_debt as pay_debt_service,
    get_virtual_card_by_user as get_virtual_card_by_user_service,
)

router = APIRouter(prefix="/virtual-card", tags=["virtual-card"])


@router.get("/")
def get_virtual_card_by_user(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
) -> VirtualCardRead:
    return get_virtual_card_by_user_service(db, current_user)


@router.post("/")
def create_virtual_card(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
)-> VirtualCardRead:
    return create_virtual_card_service(db, current_user)

@router.post("/{card_id}/deposit")
def deposit_virtual_card(
    card_id: int,
    payload: VirtualCardDeposit,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
)-> VirtualCardRead:
    return deposit_virtual_card_service(db, current_user, card_id, payload.amount, payload.currency)


@router.post("/{card_id}/pay-debt")
def pay_debt(
    payload: PayDebtRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
)-> PayDebtResponse:
    return pay_debt_service(payload.expense_split_id, current_user, db)

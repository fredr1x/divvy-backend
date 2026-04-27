from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user, get_ip_address
from app.models.user import User
from app.schemas import (
    PayDebtRequest,
    PayDebtResponse,
    VirtualCardDeposit,
    VirtualCardRead,
    CardBalanceConvert,
    CardBalanceConverted,
)
from app.services.card.virtual_card_service import (
    create_virtual_card as create_virtual_card_service,
)
from app.services.card.virtual_card_service import (
    deposit_virtual_card as deposit_virtual_card_service,
)
from app.services.card.virtual_card_service import (
    get_virtual_card_by_user as get_virtual_card_by_user_service,
)
from app.services.card.virtual_card_service import (
    pay_debt as pay_debt_service,
)
from app.services.card.card_balance_service import (
    convert_card_balance as convert_card_balance_service
)

router = APIRouter(prefix="/virtual-card", tags=["virtual-card"])


@router.get("/")
async def get_virtual_card_by_user(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db)
) -> VirtualCardRead:
    return await get_virtual_card_by_user_service(get_ip_address(request), db, current_user)


@router.post("/")
async def create_virtual_card(
    request: Request,
    current_user: User = Depends(get_current_verified_user), db: AsyncSession = Depends(get_db)
) -> VirtualCardRead:
    return await create_virtual_card_service(get_ip_address(request), db, current_user)


@router.post("/{card_id}/deposit")
async def deposit_virtual_card(
    request: Request,
    card_id: int,
    payload: VirtualCardDeposit,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> VirtualCardRead:
    return await deposit_virtual_card_service(
        get_ip_address(request), db, current_user, card_id, payload.amount, payload.currency
    )


@router.post("/{card_id}/pay-debt")
async def pay_debt(
    request: Request,
    payload: PayDebtRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PayDebtResponse:
    return await pay_debt_service(get_ip_address(request), payload.expense_split_id, current_user, db)


@router.post("/{card_id}/convert")
async def convert(
    request: Request,
    card_id: int,
    payload: CardBalanceConvert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
)-> CardBalanceConverted:
    return await convert_card_balance_service(
        get_ip_address(request),
        db,
        current_user,
        card_id,
        payload.amount,
        payload.currency_from,
        payload.currency_to,
    )

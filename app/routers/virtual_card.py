from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user, get_ip_address
from app.models.user import User
from app.schemas import (
    CardBalanceConvert,
    CardBalanceConverted,
    PayDebtRequest,
    PayDebtResponse,
    VirtualCardDeposit,
    VirtualCardRead,
)
from app.services.card.card_balance_service import (
    convert_card_balance as convert_card_balance_service,
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

router = APIRouter(prefix="/virtual-card", tags=["virtual-card"])


@router.get("/")
async def get_virtual_card_by_user(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> VirtualCardRead:
    """
    Retrieve the virtual card belonging to the current user.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        current_user: The authenticated and verified user
        db: Database session

    Returns:
        VirtualCardRead: The user's virtual card details

    Raises:
        HTTPException 404: If no virtual card exists for the current user
    """
    return await get_virtual_card_by_user_service(
        get_ip_address(request), db, current_user
    )


@router.post("/")
async def create_virtual_card(
    request: Request,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> VirtualCardRead:
    """
    Create a new virtual card for the current user.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        current_user: The authenticated and verified user
        db: Database session

    Returns:
        VirtualCardRead: The newly created virtual card details

    Raises:
        HTTPException 400: If the user already has a virtual card
    """
    return await create_virtual_card_service(get_ip_address(request), db, current_user)


@router.post("/{card_id}/deposit")
async def deposit_virtual_card(
    request: Request,
    card_id: int,
    payload: VirtualCardDeposit,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> VirtualCardRead:
    """
    Deposit funds into a virtual card.

    Adds the specified amount in the given currency to the balance
    of the identified virtual card, which must belong to the current user.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        card_id: The ID of the virtual card to deposit into
        payload: Deposit details including amount and currency
        current_user: The authenticated and verified user
        db: Database session

    Returns:
        VirtualCardRead: Updated virtual card details after the deposit

    Raises:
        HTTPException 403: If the card does not belong to the current user
        HTTPException 404: If the virtual card is not found
    """
    return await deposit_virtual_card_service(
        get_ip_address(request),
        db,
        current_user,
        card_id,
        payload.amount,
        payload.currency,
    )


@router.post("/{card_id}/pay-debt")
async def pay_debt(
    request: Request,
    payload: PayDebtRequest,
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
) -> PayDebtResponse:
    """
    Pay a debt associated with an expense split using the virtual card.

    Settles an outstanding expense split for the current user by
    charging the balance of the specified virtual card.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        card_id: The ID of the virtual card to charge
        payload: Request body containing the expense_split_id to settle
        current_user: The authenticated and verified user
        db: Database session

    Returns:
        PayDebtResponse: Result details of the debt payment

    Raises:
        HTTPException 403: If the card does not belong to the current user
        HTTPException 404: If the virtual card or expense split is not found
        HTTPException 400: If the card has insufficient balance
    """
    return await pay_debt_service(
        get_ip_address(request), payload.expense_split_id, current_user, db
    )


@router.post("/{card_id}/convert")
async def convert(
    request: Request,
    card_id: int,
    payload: CardBalanceConvert,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> CardBalanceConverted:
    """
    Convert an amount between two currencies on a virtual card.

    Performs a currency conversion on the specified virtual card,
    deducting the source currency amount and crediting the target currency.

    Args:
        request: The incoming HTTP request (used for IP address logging)
        card_id: The ID of the virtual card to perform the conversion on
        payload: Conversion details including amount, source and target currencies
        db: Database session
        current_user: The authenticated and verified user

    Returns:
        CardBalanceConverted: Conversion result including exchanged amounts and updated balances

    Raises:
        HTTPException 403: If the card does not belong to the current user
        HTTPException 404: If the virtual card is not found
        HTTPException 400: If the card has insufficient balance in the source currency
    """
    return await convert_card_balance_service(
        get_ip_address(request),
        db,
        current_user,
        card_id,
        payload.amount,
        payload.currency_from,
        payload.currency_to,
    )

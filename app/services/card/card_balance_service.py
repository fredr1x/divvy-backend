from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, VirtualCard
from app.models.card_balance import CardBalance
from app.models.enums import Currency
from app.schemas import CardBalanceConverted

from app.services.currency.currency_service import CurrencyService

def get_card_balance_by_card_id_and_currency(
    db: Session,
    card_id: int,
    currency: Currency
):
    card_balance: CardBalance = db.scalar(select(CardBalance)
                                          .where(CardBalance.card_id == card_id,
                                                 CardBalance.currency == currency
                                                 )
                                          )

    return card_balance


def deposit_balance(
    db: Session,
    card_id: int,
    amount: Decimal,
    currency: Currency
):
    card_balance: CardBalance = get_card_balance_by_card_id_and_currency(db, card_id, currency)

    if not card_balance:
        card_balance = CardBalance(
            card_id=card_id,
            currency=currency,
            balance=Decimal("0.0")
        )

        db.add(card_balance)
        db.flush()
        db.refresh(card_balance)

    card_balance.balance += amount

    db.flush()
    db.refresh(card_balance)

    return card_balance


def convert_card_balance(
    db: Session,
    current_user: User,
    card_id: int,
    amount: Decimal,
    from_currency: Currency,
    to_currency: Currency
):

    if from_currency == to_currency:
        raise HTTPException(status_code=400, detail="Currency cannot be the same")

    virtual_card: VirtualCard = db.scalar(
        select(VirtualCard).where(VirtualCard.user_id == current_user.id)
    )

    if not virtual_card:
        raise HTTPException(status_code=404, detail="Virtual card not found")

    if virtual_card.id != card_id:
        raise HTTPException(status_code=400, detail="Virtual card id mismatch")

    card_balance_from = get_card_balance_by_card_id_and_currency(db, virtual_card.id, from_currency)

    if not card_balance_from:
        raise HTTPException(status_code=400, detail=f"Card balance with currency {from_currency.name} not found")

    if card_balance_from.balance < amount:
        raise HTTPException(status_code=400, detail="Not enough balance to convert")

    converted_amount: Decimal = CurrencyService.convert_amount(db, amount, from_currency, to_currency)

    card_balance_from.balance -= amount

    card_balance_to = get_card_balance_by_card_id_and_currency(db, virtual_card.id, to_currency)

    if card_balance_to:
        card_balance_to.balance += converted_amount

    else:
        card_balance_to = CardBalance(
            card_id=virtual_card.id,
            currency=to_currency,
            balance=converted_amount
        )

        db.add(card_balance_to)

    db.flush()
    db.refresh(card_balance_to)
    db.refresh(card_balance_from)

    return CardBalanceConverted(
        card_id=virtual_card.id,
        card_balance_to=card_balance_to.balance,
        card_balance_from=card_balance_from.balance,
    )

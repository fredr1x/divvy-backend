from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import User, VirtualCard
from app.models.card_balance import CardBalance
from app.models.enums import Currency

from app.services.virtual_card_service import get_virtual_card_by_user_id
from app.services.currency_service import CurrencyService

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
            balance=amount
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

    virtual_card: VirtualCard = get_virtual_card_by_user_id(db, current_user.id)

    if virtual_card.id != card_id:
        raise HTTPException(status_code=400, detail="Virtual card id mismatch")

    card_balance_from = get_card_balance_by_card_id_and_currency(db, virtual_card.id, from_currency)

    if not card_balance_from:
        raise HTTPException(status_code=400, detail=f"Card balance with currency {from_currency.name} not found")

    if card_balance_from.balance < amount:
        raise HTTPException(status_code=400, detail="Not enough balance to convert")

    card_balance_to = get_card_balance_by_card_id_and_currency(db, virtual_card.id, to_currency)

    currency_rate = CurrencyService.get_currency_rate(db, card_balance_from.currency).rate
    converted_balance: Decimal = Decimal(amount * currency_rate)
    card_balance_from.balance -= amount

    if not card_balance_to:
        CardBalance(
            card_id=virtual_card.id,
            currency=to_currency,
            balance=converted_balance
        )

        db.add(card_balance_to)

    card_balance_to.balance += converted_balance
    db.flush()
    db.refresh(card_balance_from)
    db.refresh(card_balance_to)

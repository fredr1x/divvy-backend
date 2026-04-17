from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session
from stripe.error import StripeError

from app.models import ExpenseSplit, GroupExpense
from app.models.card_balance import CardBalance
from app.models.enums import Currency, SplitStatus, Type
from app.models.user import User
from app.models.virtual_card import VirtualCard
from app.schemas import PayDebtResponse
from app.schemas.stripe import StripeCreateCardResponse
from app.schemas.virtual_card import VirtualCardRead
from app.services.card.card_balance_service import (
    deposit_balance,
    get_card_balance_by_card_id_and_currency,
)
from app.services.currency.currency_service import CurrencyService
from app.services.expense.expense_split_service import get_expense_split_by_id
from app.services.expense.group_expense_service import get_group_expense_by_id
from app.services.stripe.stripe_service import StripeService
from app.services.stripe.stripe_transaction_service import create_transaction


def get_virtual_card_by_user_id(db: Session, user_id: int) -> VirtualCard:
    virtual_card: VirtualCard = db.scalar(
        select(VirtualCard).where(VirtualCard.user_id == user_id)
    )

    if not virtual_card:
        raise HTTPException(status_code=404, detail="Virtual card not found")

    return virtual_card


def get_virtual_card_by_user(db: Session, current_user: User) -> VirtualCardRead:
    virtual_card = get_virtual_card_by_user_id(db, current_user.id)
    card_balance: CardBalance | None = get_card_balance_by_card_id_and_currency(
        db, virtual_card.id, Currency.USD
    )

    return VirtualCardRead(
        id=virtual_card.id,
        stripe_customer_id=virtual_card.stripe_customer_id,
        card_number=virtual_card.card_number,
        card_last4=virtual_card.card_last4,
        balance=card_balance.balance if card_balance else Decimal("0.0"),
    )


def create_virtual_card(db: Session, current_user: User) -> VirtualCardRead:

    card_exists = db.scalar(
        select(VirtualCard).where(VirtualCard.user_id == current_user.id)
    )

    if card_exists:
        raise HTTPException(status_code=400, detail="User already have virtual card")

    try:
        stripe_data: StripeCreateCardResponse = StripeService.create_customer_card(
            db=db,
            email=current_user.email,
            name=f"{current_user.first_name} {current_user.last_name}",
        )

        new_card: VirtualCard = VirtualCard(
            user_id=current_user.id,
            stripe_customer_id=stripe_data.customer_id,
            stripe_payment_method_id=stripe_data.payment_method_id,
            card_number=stripe_data.card_number,
            card_last4=stripe_data.card_last4,
            card_exp_month=stripe_data.card_exp_month,
            card_exp_year=stripe_data.card_exp_year,
            card_brand=stripe_data.card_brand,
            is_active=True,
        )

        db.add(new_card)
        db.flush()
        db.refresh(new_card)

        deposit_balance(
            db=db,
            card_id=new_card.id,
            amount=Decimal("0.0"),
            currency=Currency.USD,
        )

        return VirtualCardRead(
            id=new_card.id,
            stripe_customer_id=new_card.stripe_customer_id,
            card_number=new_card.card_number,
            card_last4=new_card.card_last4,
            balance=Decimal("0.0"),
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def deposit_virtual_card(
    db: Session, current_user: User, card_id: int, amount: Decimal, currency: Currency
) -> VirtualCardRead:

    virtual_card: VirtualCard = db.scalar(
        select(VirtualCard).where(
            VirtualCard.user_id == current_user.id, VirtualCard.id == card_id
        )
    )

    if not virtual_card:
        raise HTTPException(status_code=404, detail="Virtual card not found")

    amount_usd = amount if currency == Currency.USD \
                    else CurrencyService.convert_amount(db,
                                                        amount,
                                                        currency,
                                                        Currency.USD
                                                        )



    if amount_usd < 0.50:
        raise HTTPException(status_code=400, detail="Amount must be greater than 0.50$")

    try:
        payment_intent = StripeService.deposit_funds(
            customer_id=virtual_card.stripe_customer_id,
            payment_method_id=virtual_card.stripe_payment_method_id,
            amount=amount_usd,
            currency=Currency.USD,
        )

        card_balance = deposit_balance(
            db=db,
            card_id=virtual_card.id,
            amount=amount,
            currency=currency,
        )

        create_transaction(
            db=db,
            card_id=virtual_card.id,
            stripe_payment_intent_id=payment_intent.id,
            stripe_charge_id=payment_intent.latest_charge,
            transaction_type=Type.DEPOSIT,
            amount=amount,
            currency=currency,
            status=payment_intent.status,
            description="Deposit to virtual card",
            split_id=None,
            metadata=payment_intent.metadata,
        )

        return VirtualCardRead(
            id=virtual_card.id,
            stripe_customer_id=virtual_card.stripe_customer_id,
            card_number=virtual_card.card_number,
            card_last4=virtual_card.card_last4,
            balance=card_balance.balance,
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))


def pay_debt(expense_split_id: int, current_user: User, db: Session) -> PayDebtResponse:
    expense_split: ExpenseSplit = get_expense_split_by_id(db, expense_split_id)

    if expense_split.status == SplitStatus.PAID:
        raise HTTPException(status_code=400, detail="Expense split already paid")

    group_expense: GroupExpense = get_group_expense_by_id(
        db, expense_split.group_expense_id
    )

    if expense_split.user_id != current_user.id:
        raise HTTPException(status_code=400, detail="You do not manage this expense")

    virtual_card: VirtualCard = get_virtual_card_by_user_id(db, current_user.id)

    card_balance = get_card_balance_by_card_id_and_currency(
        db, virtual_card.id, group_expense.currency
    )

    if not card_balance or card_balance.balance < abs(expense_split.owed_amount):
        raise HTTPException(
            status_code=400,
            detail=f"Not enough balance in {group_expense.currency.value}",
        )

    try:
        payment_intent = StripeService.pay_debt(
            customer_id=virtual_card.stripe_customer_id,
            payment_method_id=virtual_card.stripe_payment_method_id,
            amount=abs(expense_split.owed_amount),
            currency=group_expense.currency,
            debt_id=expense_split.id,
            description=f"Paying debt {expense_split.id}",
        )

        card_balance.balance -= abs(expense_split.owed_amount)

        expense_split.status = SplitStatus.PAID
        expense_split.paid_at = datetime.now()
        expense_split.last_modified_at = datetime.now()

        create_transaction(
            db=db,
            card_id=virtual_card.id,
            stripe_payment_intent_id=payment_intent.id,
            stripe_charge_id=payment_intent.latest_charge,
            transaction_type=Type.PAYMENT,
            amount=abs(expense_split.owed_amount),
            currency=group_expense.currency,
            status=payment_intent.status,
            split_id=expense_split.id,
            description="Paying debt {expense_split.id}",
            metadata=payment_intent.metadata,
        )

        db.flush()
        db.refresh(expense_split)
        db.refresh(card_balance)

        return PayDebtResponse(
            expense_split_id=expense_split.id,
            expense_split_status=expense_split.status,
            card_balance=card_balance.balance,
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

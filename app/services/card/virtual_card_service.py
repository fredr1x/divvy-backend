from datetime import datetime
from decimal import Decimal

from app.models import AuditLog, ExpenseSplit, GroupExpense
from app.models.enums import ActionStatus, ActionType, Currency, SplitStatus, Type
from app.models.user import User
from app.models.virtual_card import VirtualCard
from app.schemas import PayDebtResponse, CardBalanceRead
from app.schemas.stripe import StripeCreateCardResponse
from app.schemas.virtual_card import VirtualCardRead
from app.services.audit.audit_logs_service import create_failed_audit_log
from app.services.card.card_balance_service import (
    deposit_balance,
    get_card_balance_by_card_id_and_currency,
    get_all_balances_by_card_id
)
from app.services.currency.currency_service import CurrencyService
from app.services.expense.expense_split_service import get_expense_split_by_id
from app.services.expense.group_expense_service import get_group_expense_by_id
from app.services.stripe.stripe_service import StripeService
from app.services.stripe.stripe_transaction_service import create_transaction
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe.error import StripeError


async def get_virtual_card_by_user_id(
    ip_address: str, db: AsyncSession, user_id: int
) -> VirtualCard:
    audit_log = AuditLog(
        user_id=user_id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="VIRTUAL_CARD",
    )

    virtual_card: VirtualCard = await db.scalar(
        select(VirtualCard).where(VirtualCard.user_id == user_id)
    )

    if not virtual_card:
        message = "Virtual card not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id = virtual_card.id
    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = "Virtual card retrieved successfully"

    db.add(audit_log)
    await db.commit()

    return virtual_card


async def get_virtual_card_by_user(
    ip_address: str, db: AsyncSession, current_user: User
) -> VirtualCardRead:
    virtual_card = await get_virtual_card_by_user_id(ip_address, db, current_user.id)

    balances: list[CardBalanceRead] = await get_all_balances_by_card_id(db, virtual_card.id)

    return VirtualCardRead(
        id=virtual_card.id,
        stripe_customer_id=virtual_card.stripe_customer_id,
        card_number=virtual_card.card_number,
        card_last4=virtual_card.card_last4,
        balances=balances
    )


async def create_virtual_card(
    ip_address: str, db: AsyncSession, current_user: User
) -> VirtualCardRead:
    audit_log = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.CREATE,
        ip_address=ip_address,
        entity_name="VIRTUAL_CARD",
    )

    card_exists = await db.scalar(
        select(VirtualCard).where(VirtualCard.user_id == current_user.id)
    )
    if card_exists:
        message = "User already have virtual card"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    try:
        stripe_data: StripeCreateCardResponse = await StripeService.create_customer_card(
            db=db,
            email=current_user.email,
            name=f"{current_user.first_name} {current_user.last_name}",
        )

        new_card = VirtualCard(
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
        await db.flush()
        await db.refresh(new_card)

        audit_log.entity_id = new_card.id
        audit_log.action_status = ActionStatus.SUCCESS
        audit_log.message = f"Virtual card created successfully for user {current_user.id}"
        db.add(audit_log)
        await db.commit()

        await deposit_balance(
            ip_address=ip_address,
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
        await create_failed_audit_log(db, audit_log, e.error.message)
        raise HTTPException(status_code=400, detail=str(e))


async def deposit_virtual_card(
    ip_address: str,
    db: AsyncSession,
    current_user: User,
    card_id: int,
    amount: Decimal,
    currency: Currency,
) -> VirtualCardRead:
    audit_log = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="VIRTUAL_CARD",
    )

    virtual_card: VirtualCard = await db.scalar(
        select(VirtualCard).where(
            VirtualCard.user_id == current_user.id, VirtualCard.id == card_id
        )
    )

    if not virtual_card:
        message = "Virtual card not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    amount_usd = (
        amount
        if currency == Currency.USD
        else await CurrencyService.convert_amount(db, amount, currency, Currency.USD)
    )

    if amount_usd < 0.50:
        message = "Amount must be greater than 0.50$"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    try:
        payment_intent = StripeService.deposit_funds(
            customer_id=virtual_card.stripe_customer_id,
            payment_method_id=virtual_card.stripe_payment_method_id,
            amount=amount_usd,
            currency=Currency.USD,
        )

        card_balance = await deposit_balance(
            ip_address=ip_address,
            db=db,
            card_id=virtual_card.id,
            amount=amount,
            currency=currency,
        )

        await create_transaction(
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
        await create_failed_audit_log(db, audit_log, e.error.message)
        raise HTTPException(status_code=400, detail=str(e))


async def pay_debt(
    ip_address: str, expense_split_id: int, current_user: User, db: AsyncSession
) -> PayDebtResponse:
    audit_log = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="EXPENSE_SPLIT",
    )

    expense_split: ExpenseSplit = await get_expense_split_by_id(db, expense_split_id)
    if expense_split.status == SplitStatus.PAID:
        message = "Expense split already paid"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    group_expense: GroupExpense = await get_group_expense_by_id(
        db, expense_split.group_expense_id
    )

    if expense_split.user_id != current_user.id:
        message = "You do not manage this expense"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    virtual_card: VirtualCard = await get_virtual_card_by_user_id(ip_address, db, current_user.id)
    card_balance = await get_card_balance_by_card_id_and_currency(
        ip_address, db, virtual_card.id, group_expense.currency
    )

    if not card_balance or card_balance.balance < abs(expense_split.owed_amount):
        message = f"Not enough balance in {group_expense.currency.value} currency"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

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

        await create_transaction(
            db=db,
            card_id=virtual_card.id,
            stripe_payment_intent_id=payment_intent.id,
            stripe_charge_id=payment_intent.latest_charge,
            transaction_type=Type.PAYMENT,
            amount=abs(expense_split.owed_amount),
            currency=group_expense.currency,
            status=payment_intent.status,
            split_id=expense_split.id,
            description=f"Paying debt {expense_split.id}",
            metadata=payment_intent.metadata,
        )

        await db.flush()
        await db.refresh(expense_split)
        await db.refresh(card_balance)

        audit_log.entity_id = expense_split.id
        audit_log.action_status = ActionStatus.SUCCESS
        audit_log.message = "Debt paid successfully"
        db.add(audit_log)
        await db.commit()

        return PayDebtResponse(
            expense_split_id=expense_split.id,
            expense_split_status=expense_split.status,
            card_balance=card_balance.balance,
        )

    except StripeError as e:
        raise HTTPException(status_code=400, detail=str(e))

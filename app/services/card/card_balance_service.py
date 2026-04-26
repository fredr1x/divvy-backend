from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User, VirtualCard
from app.models.card_balance import CardBalance
from app.models.enums import ActionStatus, ActionType, Currency
from app.schemas import CardBalanceConverted, CardBalanceOut, CardBalanceRead
from app.services.audit.audit_logs_service import create_failed_audit_log
from app.services.currency.currency_service import CurrencyService


async def get_all_balances_by_card_id(
    db: AsyncSession,
    card_id: int
)-> list[CardBalanceRead]:
    return list(await db.scalars(select(CardBalance).where(CardBalance.card_id == card_id)))


async def get_card_balance_by_card_id_and_currency(
    ip_address: str,
    db: AsyncSession,
    card_id: int,
    currency: Currency,
) -> CardBalance:
    card_balance: CardBalance = await db.scalar(
        select(CardBalance).where(
            CardBalance.card_id == card_id,
            CardBalance.currency == currency,
        )
    )

    audit_log = AuditLog(
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="CARD_BALANCE",
    )

    if not card_balance:
        card_balance = CardBalance(
            card_id=card_id,
            currency=currency,
            balance=Decimal("0.0"),
        )
        db.add(card_balance)
        await db.flush()
        await db.refresh(card_balance)

    audit_log.entity_id = card_balance.id
    audit_log.action_status = ActionStatus.SUCCESS
    audit_log.message = "Card balance retrieved successfully"
    db.add(audit_log)
    await db.commit()
    return card_balance


async def deposit_balance(
    ip_address: str,
    db: AsyncSession,
    card_id: int,
    amount: Decimal,
    currency: Currency,
) -> CardBalance:
    card_balance = await get_card_balance_by_card_id_and_currency(
        ip_address, db, card_id, currency
    )

    audit_log = AuditLog(
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="CARD_BALANCE",
    )
    old_values = CardBalanceOut.model_validate(card_balance)

    card_balance.balance += amount
    new_values = CardBalanceOut.model_validate(card_balance)

    await db.flush()
    await db.refresh(card_balance)

    audit_log.entity_id=card_balance.id
    audit_log.old_values=[old_values.model_dump(mode="json")]
    audit_log.new_values=[new_values.model_dump(mode="json")]
    audit_log.message=f"Card balance updated successfully, balance: {card_balance.id}"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()
    return card_balance


async def convert_card_balance(
    ip_address: str,
    db: AsyncSession,
    current_user: User,
    card_id: int,
    amount: Decimal,
    from_currency: Currency,
    to_currency: Currency,
) -> CardBalanceConverted:
    from app.services.card.virtual_card_service import get_virtual_card_by_user_id

    audit_log_for_from_card = AuditLog(
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="CARD_BALANCE",
    )

    if from_currency == to_currency:
        message = "Currencies can not be the same"
        await create_failed_audit_log(db, audit_log_for_from_card, message)
        raise HTTPException(status_code=400, detail=message)

    virtual_card: VirtualCard = await get_virtual_card_by_user_id(
        ip_address, db, current_user.id
    )
    if virtual_card.id != card_id:
        message = "Virtual card id mismatch"
        await create_failed_audit_log(db, audit_log_for_from_card, message)
        raise HTTPException(status_code=400, detail=message)

    card_balance_from = await get_card_balance_by_card_id_and_currency(
        ip_address, db, virtual_card.id, from_currency
    )
    if card_balance_from.balance < amount:
        message = "Not enough balance to convert"
        await create_failed_audit_log(db, audit_log_for_from_card, message)
        raise HTTPException(status_code=400, detail=message)

    audit_log_for_from_card.old_values = CardBalanceOut.model_validate(
        card_balance_from
    ).model_dump(mode="json")

    converted_amount: Decimal = await CurrencyService.convert_amount(
        current_user.id,
        ip_address,
        db,
        amount,
        from_currency,
        to_currency
    )
    card_balance_from.balance -= amount
    audit_log_for_from_card.new_values = CardBalanceOut.model_validate(
        card_balance_from
    ).model_dump(mode="json")

    card_balance_to = await get_card_balance_by_card_id_and_currency(
        ip_address, db, virtual_card.id, to_currency
    )

    audit_log_for_to_card = AuditLog(
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="CARD_BALANCE",
    )
    audit_log_for_to_card.old_values = CardBalanceOut.model_validate(
        card_balance_to
    ).model_dump(mode="json")

    card_balance_to.balance += converted_amount
    audit_log_for_to_card.new_values = CardBalanceOut.model_validate(
        card_balance_to
    ).model_dump(mode="json")
    audit_log_for_to_card.entity_id = card_balance_to.id
    audit_log_for_to_card.action_status = ActionStatus.SUCCESS
    audit_log_for_to_card.message = (
        f"Card balance converted successfully from card {card_balance_from.id}"
    )

    audit_log_for_from_card.entity_id = card_balance_from.id
    audit_log_for_from_card.action_status = ActionStatus.SUCCESS
    audit_log_for_from_card.message = (
        f"Card balance converted successfully to card {card_balance_to.id}"
    )

    db.add(audit_log_for_from_card)
    db.add(audit_log_for_to_card)
    await db.commit()

    await db.flush()
    await db.refresh(card_balance_to)
    await db.refresh(card_balance_from)

    return CardBalanceConverted(
        card_id=virtual_card.id,
        card_balance_to=card_balance_to.balance,
        card_balance_from=card_balance_from.balance,
    )

from app.models import User, AuditLog, Item
from app.models.enums import ActionType, ActionStatus
from app.schemas import ItemCreate, ItemUpdate, ItemRead
from app.services.audit.audit_logs_service import create_failed_audit_log
from app.services.item.item_split_service import create_item_splits, update_item_splits

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


async def get_item_by_id(
    ip_address: str,
    db: AsyncSession,
    id: int,
    current_user_id: int,
) -> Item:

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="ITEMS",
    )

    item = await db.scalar(select(Item).where(Item.id == id).options(selectinload(Item.item_splits)))

    if not item:
        message="Item not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id=item.id
    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Successfully retrieved item"

    db.add(audit_log)
    await db.commit()

    return item


async def create_items_from_list(
    ip_address: str,
    db: AsyncSession,
    group_expense_id: int,
    items: list[ItemCreate],
    current_user: User,
) -> None:
    if not items:
        return

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.CREATE,
        ip_address=ip_address,
        entity_name="ITEMS"
    )

    for item in items:
        item_to_save = Item(
            group_expense_id=group_expense_id,
            name=item.name,
            price=item.price,
            quantity=item.quantity,
            total_price=item.total_price,
        )


        db.add(item_to_save)
        await db.flush()

        audit_log.entity_id=item_to_save.id
        audit_log.message="Item created successfully"
        audit_log.action_status=ActionStatus.SUCCESS
        db.add(audit_log)
        await db.commit()

        await create_item_splits(
            ip_address,
            db,
            item_to_save.id,
            item.assigned_user_ids,
            item.total_price,
            current_user.id,
        )


async def update_items_from_list(
    ip_address: str,
    db: AsyncSession,
    group_expense_id: int,
    current_user_id: int,
    items: list[ItemUpdate] | None
) -> None:
    if not items:
        return

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="ITEMS"
    )

    old_values = []
    new_values = []

    for item_update in items:
        item: Item = await get_item_by_id(
            ip_address,
            db,
            item_update.id,
            current_user_id,
        )

        if item.group_expense_id != group_expense_id:
            message="Item does not belong to this group expense"
            await create_failed_audit_log(db, audit_log, message)
            raise HTTPException(status_code=400, detail=message)

        old_values.append(ItemRead.model_validate(item).model_dump(mode="json"))

        item.name = item_update.name
        item.price = item_update.price
        item.quantity = item_update.quantity
        item.total_price = item_update.total_price
        await db.flush()

        new_values.append(ItemRead.model_validate(item).model_dump(mode="json"))

        await update_item_splits(
            ip_address,
            db,
            item,
            item_update.assigned_user_ids,
            current_user_id,
        )

    audit_log.old_values=old_values
    audit_log.new_values=new_values
    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Successfully updated items"

    db.add(audit_log)
    await db.commit()

from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog
from app.models.item import Item
from app.models.item_split import ItemSplit
from app.models.enums import ActionType, ActionStatus


async def create_item_splits(
    ip_address: str,
    db: AsyncSession,
    item_id: int,
    assigned_user_ids: list[int],
    item_total_price: Decimal,
    current_user_id: int,
) -> None:
    count = len(assigned_user_ids)
    share = normalize_amount(item_total_price / count)
    remainder = item_total_price - (share * count)

    for i, user_id in enumerate(assigned_user_ids):
        share_amount = share + remainder if i == 0 else share
        item_split = ItemSplit(item_id=item_id, user_id=user_id, share_amount=share_amount)
        db.add(item_split)
        await db.flush()

        audit_log = AuditLog(
            user_id=current_user_id,
            action_type=ActionType.CREATE,
            ip_address=ip_address,
            entity_id=item_split.id,
            entity_name="ITEM_SPLIT",
            new_values=[serialize_item_split(item_split)],
            action_status=ActionStatus.SUCCESS,
            message="Item split created successfully",
        )
        db.add(audit_log)


async def update_item_splits(
    ip_address: str,
    db: AsyncSession,
    item: Item,
    assigned_user_ids: list[int],
    current_user_id: int,
) -> None:
    splits = list(item.item_splits)
    old_assigned_user_ids = [split.user_id for split in splits]
    old_assigned_user_ids_set = set(old_assigned_user_ids)
    assigned_user_ids_set = set(assigned_user_ids)
    common_user_ids = old_assigned_user_ids_set & assigned_user_ids_set
    old_common_values = [
        serialize_item_split(split)
        for split in splits
        if split.user_id in common_user_ids
    ]

    removed_user_ids = old_assigned_user_ids_set - assigned_user_ids_set
    for user_id in sorted(removed_user_ids):
        removed_split = next(
            (split for split in splits if split.user_id == user_id),
            None,
        )
        await db.execute(
            delete(ItemSplit).where(
                ItemSplit.item_id == item.id,
                ItemSplit.user_id == user_id,
            )
        )
        if removed_split:
            delete_audit_log = AuditLog(
                user_id=current_user_id,
                action_type=ActionType.DELETE,
                ip_address=ip_address,
                entity_id=removed_split.id,
                entity_name="ITEM_SPLIT",
                old_values=[serialize_item_split(removed_split)],
                action_status=ActionStatus.SUCCESS,
                message="Item split deleted successfully",
            )
            db.add(delete_audit_log)

    new_assigned_user_ids = assigned_user_ids_set - old_assigned_user_ids_set
    for new_id in sorted(new_assigned_user_ids):
        new_item_split = ItemSplit(item_id=item.id, user_id=new_id, share_amount=Decimal("0"))
        db.add(new_item_split)
        await db.flush()

        create_audit_log = AuditLog(
            user_id=current_user_id,
            action_type=ActionType.CREATE,
            ip_address=ip_address,
            entity_id=new_item_split.id,
            entity_name="ITEM_SPLIT",
            new_values=[serialize_item_split(new_item_split)],
            action_status=ActionStatus.SUCCESS,
            message="Item split created successfully",
        )
        db.add(create_audit_log)

    await db.flush()
    await db.refresh(item)
    splits = list(item.item_splits)
    splits.sort(key=lambda x: x.user_id)

    count = len(assigned_user_ids)
    share = normalize_amount(item.total_price / count)
    remainder = item.total_price - (share * count)

    for i, split in enumerate(splits):
        split.share_amount = share + remainder if i == 0 else share

    await db.flush()

    new_common_values = [
        serialize_item_split(split)
        for split in splits
        if split.user_id in common_user_ids
    ]

    if old_common_values and new_common_values:
        update_audit_log = AuditLog(
            user_id=current_user_id,
            action_type=ActionType.UPDATE,
            ip_address=ip_address,
            entity_name="ITEM_SPLIT",
            old_values=old_common_values,
            new_values=new_common_values,
            action_status=ActionStatus.SUCCESS,
            message="Successfully updated item splits",
        )
        db.add(update_audit_log)


def normalize_amount(value: Decimal | int | float) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def serialize_item_split(item_split: ItemSplit) -> dict:
    return {
        "id": item_split.id,
        "item_id": item_split.item_id,
        "user_id": item_split.user_id,
        "share_amount": str(item_split.share_amount),
    }

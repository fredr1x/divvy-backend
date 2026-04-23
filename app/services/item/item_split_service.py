from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.item import Item
from app.models.item_split import ItemSplit


async def create_item_splits(
    db: AsyncSession, item_id: int, assigned_user_ids: list[int], item_total_price: Decimal
) -> None:
    count = len(assigned_user_ids)
    share = normalize_amount(item_total_price / count)
    remainder = item_total_price - (share * count)

    for i, user_id in enumerate(assigned_user_ids):
        share_amount = share + remainder if i == 0 else share
        db.add(ItemSplit(item_id=item_id, user_id=user_id, share_amount=share_amount))


async def update_item_splits(db: AsyncSession, item: Item, assigned_user_ids: list[int]) -> None:
    splits = item.item_splits
    old_assigned_user_ids = [split.user_id for split in splits]

    removed_user_ids = set(old_assigned_user_ids) - set(assigned_user_ids)
    for id in removed_user_ids:
        await db.execute(
            delete(ItemSplit).where(
                ItemSplit.item_id == item.id, ItemSplit.user_id == id
            )
        )

    new_assigned_user_ids = set(assigned_user_ids) - set(old_assigned_user_ids)
    for new_id in new_assigned_user_ids:
        db.add(ItemSplit(item_id=item.id, user_id=new_id, share_amount=Decimal("0")))

    await db.flush()
    await db.refresh(item)
    splits = item.item_splits
    splits.sort(key=lambda x: x.user_id)

    count = len(assigned_user_ids)
    share = normalize_amount(item.total_price / count)
    remainder = item.total_price - (share * count)

    for i, split in enumerate(splits):
        split.share_amount = share + remainder if i == 0 else share

    await db.flush()


def normalize_amount(value: Decimal | int | float) -> Decimal:
    if not isinstance(value, Decimal):
        value = Decimal(str(value))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

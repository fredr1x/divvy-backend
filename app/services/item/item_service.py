from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.item import Item
from app.schemas.item import ItemCreate, ItemUpdate
from app.services.item.item_split_service import create_item_splits, update_item_splits


async def get_item_by_id(db: AsyncSession, id: int) -> Item:
    item = await db.scalar(
        select(Item).where(Item.id == id).options(selectinload(Item.item_splits))
    )
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


async def create_items_from_list(
    db: AsyncSession, group_expense_id: int, items: list[ItemCreate]
) -> None:
    if not items:
        return

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
        await create_item_splits(db, item_to_save.id, item.assigned_user_ids, item.total_price)


async def update_items_from_list(
    db: AsyncSession, group_expense_id: int, items: list[ItemUpdate] | None
) -> None:
    if not items:
        return

    for item_update in items:
        item: Item = await get_item_by_id(db, item_update.id)

        if item.group_expense_id != group_expense_id:
            raise HTTPException(
                status_code=400, detail="Item does not belong to this group expense"
            )

        item.name = item_update.name
        item.price = item_update.price
        item.quantity = item_update.quantity
        item.total_price = item_update.total_price
        await db.flush()
        await update_item_splits(db, item, item_update.assigned_user_ids)

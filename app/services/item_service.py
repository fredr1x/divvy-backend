from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.schemas.item import ItemCreate, ItemUpdate

from app.services.item_split_service import create_item_splits, update_item_splits

from app.models.item import Item

def get_item_by_id(
    db: Session,
    id: int
)-> Item:
    item = db.scalar(select(Item).where(Item.id == id).options(selectinload(Item.item_splits)))
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
    return item


def create_items_from_list(
    db: Session,
    group_expense_id: int,
    items: list[ItemCreate]
) -> None:
    for item in items:
        item_to_save = Item(
            group_expense_id=group_expense_id,
            name=item.name,
            price=item.price,
            quantity=item.quantity,
            total_price=item.total_price
        )

        db.add(item_to_save)
        db.flush()

        create_item_splits(db, item_to_save.id, item.assigned_user_ids, item.total_price)


def update_items_from_list(
    db: Session,
    group_expense_id: int,
    items: list[ItemUpdate] | None
)-> None:

    if not items:
        return

    for item_update in items:
        item: Item = get_item_by_id(db, item_update.id)

        if item.group_expense_id != group_expense_id:
            raise HTTPException(status_code=400, detail="Item does not belong to this group expense")

        item.name = item_update.name
        item.price = item_update.price
        item.quantity = item_update.quantity
        item.total_price = item_update.total_price
        db.flush()

        update_item_splits(db, item, item_update.assigned_user_ids)

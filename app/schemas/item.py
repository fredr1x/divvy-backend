from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, ConfigDict


class ItemRead(BaseModel):
    id: int
    name: str
    group_expense_id: int
    price: Decimal
    quantity: int
    total_price: Decimal

    model_config = ConfigDict(from_attributes=True)


class ItemCreate(BaseModel):
    name: str
    price: Decimal
    quantity: int
    total_price: Decimal
    assigned_user_ids: list[int]


class ItemUpdate(BaseModel):
    id: int
    name: str
    price: Decimal
    quantity: int
    total_price: Decimal
    assigned_user_ids: list[int]


class ReceiptItem(BaseModel):
    item_name: str = Field(
        description="Full product description exactly as printed on the receipt"
    )
    quantity: int = Field(
        description="Explicitly printed quantity, or 1 if not shown. Never use weight as quantity."
    )
    price: Optional[float] = Field(
        description="Final line-item total. Null if price is not visible or legible."
    )


class ReceiptItems(BaseModel):
    items: list[ReceiptItem]


OutputSchema = {
    "format": {
        "type": "json_schema",
        "schema": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_name": {
                                "type": "string",
                                "description": "Full product description exactly as printed on the receipt",
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Explicitly printed quantity, or 1 if not shown. Never use weight as quantity.",
                            },
                            "price": {
                                "type": ["number", "null"],
                                "description": "Final line-item total. Null if price is not visible or legible.",
                            },
                        },
                        "additionalProperties": False,
                        "required": ["item_name", "quantity", "price"],
                    },
                }
            },
            "additionalProperties": False,
            "required": ["items"],
        },
    }
}

from decimal import Decimal
from pydantic import BaseModel

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

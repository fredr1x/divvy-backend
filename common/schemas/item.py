from decimal import Decimal
from pydantic import BaseModel

class ItemOCRResponse(BaseModel):
    name: str
    quantity: int
    price: Decimal
    total_price: Decimal

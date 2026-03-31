from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ShareType, Currency
from app.schemas.expense_split import ExpenseSplitDetails
from app.schemas.item import ItemCreate, ItemUpdate


class GroupExpenseCreate(BaseModel):
    payer_id: int
    group_id: int
    name: str
    currency: Currency | None = None
    created_by: int
    share_type: ShareType
    total_amount: Decimal
    expense_members: list[int]
    expense_items: Optional[list[ItemCreate]] = None
    exact_share_amount: Optional[dict[int, Decimal]] = None
    percentage_share_amount: Optional[dict[int, Decimal]] = None

class GroupExpenseRead(BaseModel):
    id: int
    payer_id: int
    group_id: int
    name: str
    total_amount: Decimal
    created_by: int
    created_at: datetime

    expenses_split: list[ExpenseSplitDetails] = Field(validation_alias="splits")

    model_config = ConfigDict(from_attributes=True)

class GroupExpenseUpdate(BaseModel):
    id: int
    payer_id: int
    name: str
    total_amount: Decimal
    share_type: ShareType
    expense_members: list[int]
    exact_share_amount: Optional[dict[int, Decimal]] = None
    percentage_share_amount: Optional[dict[int, Decimal]] = None
    expense_items: Optional[list[ItemUpdate]] = None

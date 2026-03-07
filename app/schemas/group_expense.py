from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ShareType
from app.schemas.expense_split import ExpenseSplitDetails

# TODO add list of user ids that related to expense
class GroupExpenseCreate(BaseModel):
    payer_id: int
    group_id: int
    name: str
    created_by: int
    share_type: ShareType
    total_amount: Decimal
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
    name: str
    total_amount: Decimal
    share_type: ShareType
    exact_share_amount: Optional[dict[int, Decimal]] = None
    percentage_share_amount: Optional[dict[int, Decimal]] = None

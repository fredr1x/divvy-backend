from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict

from app.models.enums import ShareType


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
    created_by: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

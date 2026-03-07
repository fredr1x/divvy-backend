from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ShareType, SplitStatus

class ExpenseSplitDetails(BaseModel):
    user_id: int
    owed_amount: Decimal
    share_type: ShareType
    status: SplitStatus = Field(validation_alias="split_status")
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwedAmountDetail(BaseModel):
    amount: Decimal
    to_user_id: int

class ReceivableAmountDetail(BaseModel):
    amount: Decimal
    from_user_id: int

class AllExpensesByGroupAndUser(BaseModel):
    group_id: int
    user_id: int
    total_owed_amount: Decimal
    total_receivable_amount: Decimal
    owed_amount_details: list[OwedAmountDetail]
    receivable_amount_details: list[ReceivableAmountDetail]

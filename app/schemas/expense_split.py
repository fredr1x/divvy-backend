from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import SplitStatus, SplitType


class ExpenseSplitDetails(BaseModel):
    id: int
    user_id: int
    owed_amount: Decimal
    split_type: SplitType
    status: SplitStatus
    refund_to_user_id: int | None = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class OwedAmountDetail(BaseModel):
    amount: Decimal
    to_user_id: int
    status: SplitStatus


class ReceivableAmountDetail(BaseModel):
    amount: Decimal
    from_user_id: int
    status: SplitStatus

class AllExpensesByGroupAndUser(BaseModel):
    group_id: int
    user_id: int
    total_owed_amount: Decimal
    total_receivable_amount: Decimal
    owed_amount_details: list[OwedAmountDetail]
    receivable_amount_details: list[ReceivableAmountDetail]


class UserSplitBalance(BaseModel):
    user_id: int
    balance: Decimal


class ExpenseSplitBalances(BaseModel):
    group_id: int
    balances: list[UserSplitBalance]

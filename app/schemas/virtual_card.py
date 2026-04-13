from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import Currency, SplitStatus


class VirtualCardRead(BaseModel):
    id: int
    stripe_customer_id: str
    card_number: str
    card_last4: str = Field(serialization_alias="card_last_4")
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class VirtualCardDeposit(BaseModel):
    amount: Decimal
    currency: Currency


class PayDebtRequest(BaseModel):
    expense_split_id: int


class PayDebtResponse(BaseModel):
    expense_split_id: int
    expense_split_status: SplitStatus
    card_balance: Decimal

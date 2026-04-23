from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from app.models.enums import Currency


class CardBalanceConvert(BaseModel):
    amount: Decimal
    currency_from: Currency
    currency_to: Currency


class CardBalanceConverted(BaseModel):
    card_id: int
    card_balance_to: Decimal
    card_balance_from: Decimal


class CardBalanceOut(BaseModel):
    id: int
    card_id: int
    currency: Currency
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)


class CardBalanceRead(BaseModel):
    currency: Currency
    balance: Decimal

    model_config = ConfigDict(from_attributes=True)

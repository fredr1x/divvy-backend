from decimal import Decimal

from pydantic import BaseModel

from app.models.enums import Currency


class CardBalanceConvert(BaseModel):
    amount: Decimal
    currency_from: Currency
    currency_to: Currency

class CardBalanceConverted(BaseModel):
    card_id: int
    card_balance_to: Decimal
    card_balance_from: Decimal

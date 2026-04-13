import os
import requests

from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.currency_rate import CurrencyRate
from app.models.enums import Currency

exchange_rate_api = os.getenv("EXCHANGE_RATE_API")

class CurrencyService:

    @staticmethod
    def fetch_rates_from_api(currency: Currency) -> dict[str, float]:
        try:
            response = requests.get(
                url=f"https://v6.exchangerate-api.com/v6/{exchange_rate_api}/latest/{currency.name}",
                timeout=10,
            )

            data = response.json()["conversion_rates"]

            return data

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


    @staticmethod
    def save_rates_to_db(db: Session, rates: dict):
        allowed_currencies = {c.value for c in Currency}

        for currency_str, rate in rates.items():
            if currency_str not in allowed_currencies:
                continue

            currency_enum = Currency(currency_str)

            existing = db.execute(
                select(CurrencyRate).where(
                    CurrencyRate.currency == currency_enum
                )
            ).scalar_one_or_none()

            if existing:
                existing.rate = Decimal(str(rate))

            else:
                db.add(
                    CurrencyRate(
                        currency=currency_enum,
                        base_currency=Currency.USD,
                        rate=Decimal(str(rate))
                    )
                )


    @staticmethod
    def get_currency_rate(db: Session, currency_from: Currency, currency_to: Currency) -> Decimal:
        currency_rate: CurrencyRate = db.scalar(select(CurrencyRate).where(CurrencyRate.currency == currency_from))

        if not currency_rate:
            data = CurrencyService.fetch_rates_from_api()

            CurrencyService.save_rates_to_db(db, data)
            db.flush()

        return currency_rate

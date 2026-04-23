import os
import requests

from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.currency_rate import CurrencyRate
from app.models.enums import Currency

exchange_rate_api = os.getenv("EXCHANGE_RATE_API")

class CurrencyService:

    @staticmethod
    def fetch_rates_from_api(base_currency: Currency = Currency.USD) -> dict[str, float]:
        try:
            response = requests.get(
                url=f"https://v6.exchangerate-api.com/v6/{exchange_rate_api}/latest/{base_currency.value}",
                timeout=10,
            )
            response.raise_for_status()

            data = response.json()

            if data.get("result") != "success":
                raise HTTPException(
                    status_code=500,
                    detail=f"API error: {data.get('error-type', 'Unknown error')}"
                )

            return data["conversion_rates"]

        except requests.RequestException as e:
            raise HTTPException(status_code=500, detail=f"API request failed: {str(e)}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @staticmethod
    async def save_rates_to_db(
        db: AsyncSession, rates: dict, base_currency: Currency = Currency.USD
    ):
        allowed_currencies = {c.value for c in Currency}

        for currency_str, rate in rates.items():
            if currency_str not in allowed_currencies:
                continue

            if currency_str == base_currency.value:
                continue

            currency_enum = Currency(currency_str)

            existing = (await db.execute(
                select(CurrencyRate).where(
                    CurrencyRate.currency == currency_enum,
                    CurrencyRate.base_currency == base_currency.value
                )
            )).scalar_one_or_none()

            if existing:
                existing.rate = Decimal(str(rate))

            else:
                db.add(
                    CurrencyRate(
                        currency=currency_enum,
                        base_currency=base_currency,
                        rate=Decimal(str(rate))
                    )
                )

        await db.commit()

    @staticmethod
    async def get_rate_from_db(
            db: AsyncSession,
            currency: Currency,
            base_currency: Currency = Currency.USD
    ) -> Decimal:

        if currency == base_currency:
            return Decimal("1.0")

        rate = await db.scalar(
            select(CurrencyRate.rate).where(
                CurrencyRate.currency == currency,
                CurrencyRate.base_currency == base_currency.value
            )
        )

        if not rate:
            rates = CurrencyService.fetch_rates_from_api(base_currency)
            await CurrencyService.save_rates_to_db(db, rates, base_currency)

            rate = await db.scalar(
                select(CurrencyRate.rate).where(
                    CurrencyRate.currency == currency,
                    CurrencyRate.base_currency == base_currency.value
                )
            )

            if not rate:
                raise HTTPException(
                    status_code=404,
                    detail=f"Rate for {currency.value} not found"
                )

        return rate

    @staticmethod
    async def convert_amount(
            db: AsyncSession,
            amount: Decimal,
            from_currency: Currency,
            to_currency: Currency
    ) -> Decimal:

        if from_currency == to_currency:
            return amount

        rate_from = await CurrencyService.get_rate_from_db(db, from_currency, Currency.USD)
        rate_to = await CurrencyService.get_rate_from_db(db, to_currency, Currency.USD)

        if from_currency == Currency.USD:
            converted = amount * rate_to

        elif to_currency == Currency.USD:
            converted = amount / rate_from

        else:
            converted = amount * (rate_to / rate_from)

        return converted.quantize(Decimal("0.01"))

    @staticmethod
    async def get_exchange_rate(
            db: AsyncSession,
            from_currency: Currency,
            to_currency: Currency
    ) -> Decimal:
        return await CurrencyService.convert_amount(
            db=db,
            amount=Decimal("1.0"),
            from_currency=from_currency,
            to_currency=to_currency
        )

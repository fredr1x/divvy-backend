import logging

from app.db.session import SessionLocal
from app.models.enums import Currency
from app.services.currency.currency_service import CurrencyService

async def update_currency_rates():
    async with SessionLocal() as db:
        logging.info("Start updating currency rates job")
        rates = CurrencyService.fetch_rates_from_api(Currency.USD)
        logging.info("Successfully fetched currency rates")

        logging.info("Saving new currency rates")
        await CurrencyService.save_rates_to_db(db, rates, Currency.USD)
        await db.commit()

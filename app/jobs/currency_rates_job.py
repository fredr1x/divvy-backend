from app.db.session import SessionLocal
from app.models.enums import Currency
from app.services.currency.currency_service import CurrencyService

def update_currency_rates():
    db = SessionLocal()

    try:
        rates = CurrencyService.fetch_rates_from_api(Currency.USD)
        CurrencyService.save_rates_to_db(db, rates, Currency.USD)

    finally:
        db.close()

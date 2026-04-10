import os
import stripe

from decimal import Decimal
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.enums import Currency
from app.schemas.stripe import StripeCreateCardResponse
from app.services.stripe_next_card_service import get_next_card_number, update_next_card_number

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


class StripeService:
    @staticmethod
    def create_customer_card(db: Session, email: str, name: str):
        customer = stripe.Customer.create(
            email=email,
            name=name,
            description=f"Mock customer {name}"
        )

        card_data = StripeTestCards.get_next_card(db)
        test_pm_id = StripeTestCards.get_test_token(card_data['brand'])

        try:
            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                payment_method_types=['card'],
            )

            setup_intent = stripe.SetupIntent.confirm(
                setup_intent.id,
                payment_method=test_pm_id,
            )

            payment_method_id = setup_intent.payment_method

        except stripe.error.StripeError as e:
            setup_intent = stripe.SetupIntent.create(
                customer=customer.id,
                payment_method_types=['card'],
            )

            setup_intent = stripe.SetupIntent.confirm(
                setup_intent.id,
                payment_method="pm_card_visa",
            )

            payment_method_id = setup_intent.payment_method

        stripe.Customer.modify(
            customer.id,
            invoice_settings={
                "default_payment_method": payment_method_id
            }
        )

        payment_method = stripe.PaymentMethod.retrieve(payment_method_id)

        return StripeCreateCardResponse(
            customer_id=customer.id,
            payment_method_id=payment_method_id,
            card_number=card_data['number'],
            card_last4=payment_method.card.last4,
            card_exp_month=payment_method.card.exp_month,
            card_exp_year=payment_method.card.exp_year,
            card_brand=card_data['brand'],
            card_description=card_data['description']
        )

    @staticmethod
    def deposit_funds(customer_id: str, payment_method_id: str, amount: Decimal, currency: Currency, description: str = "Balance deposit"):
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=str.lower(currency.name),
            customer=customer_id,
            payment_method=payment_method_id,
            off_session=True,
            confirm=True,
            description=description,
            metadata={
                "type": "deposit",
                "description": description
            }
        )
        return payment_intent

    @staticmethod
    def pay_debt(customer_id: str, payment_method_id: str, amount: Decimal, currency: Currency, debt_id: int, description: str):
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=str.lower(currency.name),
            customer=customer_id,
            payment_method=payment_method_id,
            off_session=True,
            confirm=True,
            description=description,
            metadata={
                "type": "payment",
                "debt_id": str(debt_id),
                "description": description
            }
        )
        return payment_intent

    @staticmethod
    def get_customer_balance(customer_id: str):
        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            limit=100
        )

        balance = 0.0
        for pi in payment_intents.auto_paging_iter():
            if pi.status == "succeeded":
                tx_type = pi.metadata.get("type", "payment")
                amount = pi.amount / 100

                if tx_type == "deposit":
                    balance += amount
                elif tx_type == "payment":
                    balance -= amount

        return balance

    @staticmethod
    def get_transaction_history(customer_id: str):
        payment_intents = stripe.PaymentIntent.list(
            customer=customer_id,
            limit=100
        )

        transactions = []
        for pi in payment_intents.auto_paging_iter():
            transactions.append({
                "id": pi.id,
                "type": pi.metadata.get("type", "unknown"),
                "amount": pi.amount / 100,
                "status": pi.status,
                "description": pi.description,
                "created": pi.created,
                "debt_id": pi.metadata.get("debt_id")
            })

        return transactions


class StripeTestCards:
    CARDS = [
        {"number": "4242424242424242", "brand": "Visa", "description": "Успешная Visa"},
        {"number": "4000056655665556", "brand": "Visa (debit)", "description": "Visa Debit"},
        {"number": "5555555555554444", "brand": "Mastercard", "description": "Успешная Mastercard"},
        {"number": "2223003122003222", "brand": "Mastercard (2-series)", "description": "Mastercard 2-series"},
        {"number": "5200828282828210", "brand": "Mastercard (debit)", "description": "Mastercard Debit"},
        {"number": "378282246310005", "brand": "American Express", "description": "Amex"},
        {"number": "371449635398431", "brand": "American Express", "description": "Amex (альтернативная)"},
        {"number": "6011111111111117", "brand": "Discover", "description": "Discover"},
        {"number": "6011000990139424", "brand": "Discover", "description": "Discover (альтернативная)"},
        {"number": "3056930009020004", "brand": "Diners Club", "description": "Diners Club"},
        {"number": "36227206271667", "brand": "Diners Club (14-digit)", "description": "Diners Club 14"},
        {"number": "3566002020360505", "brand": "JCB", "description": "JCB"},
    ]

    TEST_TOKENS = {
        "Visa": "pm_card_visa",
        "Visa (debit)": "pm_card_visa_debit",
        "Mastercard": "pm_card_mastercard",
        "Mastercard (2-series)": "pm_card_mastercard",
        "Mastercard (debit)": "pm_card_mastercard_debit",
        "American Express": "pm_card_amex",
        "Discover": "pm_card_discover",
        "Diners Club": "pm_card_diners",
        "Diners Club (14-digit)": "pm_card_diners",
        "JCB": "pm_card_jcb",
    }

    @staticmethod
    def get_test_token(brand: str) -> str:
        return StripeTestCards.TEST_TOKENS.get(brand, "pm_card_visa")

    @staticmethod
    def get_next_card(db: Session):
        number: int = get_next_card_number(db)

        if number > 11:
            raise HTTPException(status_code=400, detail="We are run out of test cards, sorry :)")

        card = StripeTestCards.CARDS[number]
        update_next_card_number(db, number + 1)
        return card

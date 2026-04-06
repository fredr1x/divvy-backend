import os

import stripe
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.stripe import StripeCreateCardResponse
from app.services.stripe_next_card_service import get_next_card_number, update_next_card_number

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
cvc4 = os.getenv("STRIPE_DEFAULT_CVC_4")
cvc3 = os.getenv("STRIPE_DEFAULT_CVC_3")

class StripeService:
    @staticmethod
    def create_customer_card(db: Session, email: str, name: str):
        customer = stripe.Customer.create(
            email=email,
            name=name,
            description=f"Mock customer {name}"
        )

        card_data = StripeTestCards.get_next_card(db)

        exp_month = 12
        exp_year = 2027
        if card_data['brand'] in ['American Express', 'Diners Club (14-digit)']:
            cvc = cvc4
        else:
            cvc = cvc3

        payment_method = stripe.PaymentMethod.create(
            type="card",
            card={
                "number": card_data['number'],
                "exp_month": exp_month,
                "exp_year": exp_year,
                "cvc": cvc
            }
        )

        stripe.PaymentMethod.attach(payment_method.id, customer=customer.id)
        stripe.Customer.modify(
            customer.id,
            invoice_settings={
                "default_payment_method": payment_method.id
            }
        )

        return StripeCreateCardResponse(
            customer_id=customer.id,
            payment_method_id=payment_method.id,
            card_number=card_data['number'],
            card_last4=card_data['number'][-4:],
            card_exp_month=exp_month,
            card_exp_year=exp_year,
            card_brand=card_data['brand'],
            card_description=card_data['description']
        )

    @staticmethod
    def deposit_funds(customer_id: str, amount: float, description: str = "Balance deposit"):
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            customer=customer_id,
            payment_method_types=["card"],
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
    def pay_debt(customer_id: str, amount: float, debt_id: int, description: str):
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency="usd",
            customer=customer_id,
            payment_method_types=["card"],
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
        {
            "number": "4242424242424242",
            "brand": "Visa",
            "description": "Успешная Visa"
        },
        {
            "number": "4000056655665556",
            "brand": "Visa (debit)",
            "description": "Visa Debit"
        },
        {
            "number": "5555555555554444",
            "brand": "Mastercard",
            "description": "Успешная Mastercard"
        },
        {
            "number": "2223003122003222",
            "brand": "Mastercard (2-series)",
            "description": "Mastercard 2-series"
        },
        {
            "number": "5200828282828210",
            "brand": "Mastercard (debit)",
            "description": "Mastercard Debit"
        },
        {
            "number": "378282246310005",
            "brand": "American Express",
            "description": "Amex"
        },
        {
            "number": "371449635398431",
            "brand": "American Express",
            "description": "Amex (альтернативная)"
        },
        {
            "number": "6011111111111117",
            "brand": "Discover",
            "description": "Discover"
        },
        {
            "number": "6011000990139424",
            "brand": "Discover",
            "description": "Discover (альтернативная)"
        },
        {
            "number": "3056930009020004",
            "brand": "Diners Club",
            "description": "Diners Club"
        },
        {
            "number": "36227206271667",
            "brand": "Diners Club (14-digit)",
            "description": "Diners Club 14"
        },
        {
            "number": "3566002020360505",
            "brand": "JCB",
            "description": "JCB"
        },
    ]

    @staticmethod
    def get_next_card(db: Session):
        number: int = get_next_card_number(db)

        if number > 11:
            raise HTTPException(status_code=400, detail="We are run out of test cards, sorry :)")

        card = StripeTestCards.CARDS[number]

        update_next_card_number(db, number + 1)
        return card

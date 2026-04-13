from decimal import Decimal

from sqlalchemy.orm import Session

from app.models import StripeTransaction
from app.models.enums import Currency, Status, Type


def create_transaction(
    db: Session,
    card_id: int,
    stripe_payment_intent_id: str,
    stripe_charge_id: str,
    transaction_type: Type,
    amount: Decimal,
    currency: Currency,
    status: str,
    split_id: int | None,
    description: str,
    metadata: dict,
):
    stripe_transaction = StripeTransaction(
        card_id=card_id,
        stripe_payment_intent_id=stripe_payment_intent_id,
        stripe_charge_id=stripe_charge_id,
        type=transaction_type,
        amount=amount,
        currency=currency,
        status=Status(status.upper()),
        split_id=split_id,
        description=description,
        metadata_json=metadata,
    )

    db.add(stripe_transaction)
    db.flush()
    db.refresh(stripe_transaction)

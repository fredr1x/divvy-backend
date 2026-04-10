from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import StripeNextCard


def get_next_card(db: Session):
    next_card: StripeNextCard = db.scalar(select(StripeNextCard).where(StripeNextCard.id == 1))
    if not next_card:
        raise HTTPException(status_code=400, detail="Failed to get next card number")

    return next_card


def get_next_card_number(db: Session):
    next_card: StripeNextCard = db.scalar(select(StripeNextCard).where(StripeNextCard.id == 1))
    if not next_card:
        raise HTTPException(status_code=400, detail="Failed to get next card number")

    return next_card.number


def update_next_card_number(db: Session, new_next_card_number: int):
    next_card: StripeNextCard = get_next_card(db)
    next_card.number = new_next_card_number
    db.flush()


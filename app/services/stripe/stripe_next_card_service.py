from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import StripeNextCard


async def get_next_card(db: AsyncSession):
    next_card: StripeNextCard = await db.scalar(
        select(StripeNextCard).where(StripeNextCard.id == 1)
    )
    if not next_card:
        raise HTTPException(status_code=400, detail="Failed to get next card number")

    return next_card


async def get_next_card_number(db: AsyncSession):
    next_card: StripeNextCard = await db.scalar(
        select(StripeNextCard).where(StripeNextCard.id == 1)
    )
    if not next_card:
        raise HTTPException(status_code=400, detail="Failed to get next card number")

    return next_card.number


async def update_next_card_number(db: AsyncSession, new_next_card_number: int):
    next_card: StripeNextCard = await get_next_card(db)
    next_card.number = new_next_card_number
    await db.flush()

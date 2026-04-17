from sqlalchemy import Integer, ForeignKey, Enum, Numeric, UniqueConstraint
from sqlalchemy.orm import mapped_column, Mapped

from decimal import Decimal
from app.db.base import Base
from app.models.enums import Currency


class CardBalance(Base):
    __tablename__ = 'card_balances'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    card_id: Mapped[int] = mapped_column(Integer, ForeignKey('virtual_cards.id'))

    currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        default=Currency.USD,
        nullable=False
    )

    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        default=Decimal("0.0")
    )

    __table_args__ = (
        UniqueConstraint('card_id', 'currency', name='unique_card_currency'),
    )

from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, ForeignKey, String, Numeric, Boolean, DateTime
from sqlalchemy.orm import mapped_column, Mapped

from app.db.base import Base


class VirtualCard(Base):
    __tablename__ = 'virtual_cards'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey('users.id')
    )

    stripe_customer_id: Mapped[str] = mapped_column(
        String(128), nullable=False,  unique=True
    )

    stripe_payment_method_id: Mapped[str] = mapped_column(
        String(128), nullable=False
    )

    card_number: Mapped[str] = mapped_column(
        String(14), nullable=False, unique=True
    )

    card_last4: Mapped[str] = mapped_column(
        String(4), nullable=False
    )

    card_exp_month: Mapped[int] = mapped_column(Integer)

    card_exp_year: Mapped[int] = mapped_column(Integer)

    card_brand: Mapped[str] = mapped_column(String(64))

    balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

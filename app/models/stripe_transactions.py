from sqlalchemy import Integer, ForeignKey, String, Enum, Numeric, JSON, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from decimal import Decimal
from app.db.base import Base
from app.models.enums import Type, Currency, Status
from datetime import datetime

class StripeTransaction(Base):
    __tablename__ = "stripe_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    card_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("virtual_cards.id")
    )

    stripe_payment_intent_id = mapped_column(
        String(128), unique=True
    )

    stripe_charge_id = mapped_column(
        String(128), nullable=True
    )

    type: Mapped[Type] = mapped_column(
        Enum(Type, name="transaction_type"),
        nullable=False
    )

    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency"),
        nullable=False,
        default=Currency.KZT
    )

    status: Mapped[Status] = mapped_column(
        Enum(Status, name="transaction_status"),
        nullable=False,
    )

    split_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("expense_splits.id"), nullable=True
    )

    description: Mapped[str] = mapped_column(String(255))

    metadata_json: Mapped[dict] = mapped_column("metadata", JSON)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, onupdate=datetime.now, nullable=True
    )

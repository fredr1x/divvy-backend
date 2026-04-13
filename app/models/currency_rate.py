from datetime import datetime
from decimal import Decimal

from sqlalchemy import Integer, Enum, Numeric, DateTime
from sqlalchemy.orm import mapped_column, Mapped

from app.db.base import Base
from app.models.enums import Currency


class CurrencyRate(Base):
    __tablename__ = "currency_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        nullable=False,
        unique=True
    )

    base_currency: Mapped[Currency] = mapped_column(
        Enum(Currency),
        nullable=False,
        default=Currency.USD
    )


    rate: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now(),
    )

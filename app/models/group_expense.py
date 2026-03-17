from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Numeric, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ShareType, Currency

if TYPE_CHECKING:
    from app.models.expense_split import ExpenseSplit
    from app.models.group import Group
    from app.models.user import User


class GroupExpense(Base):
    __tablename__ = "group_expenses"

    id: Mapped[int] = mapped_column(primary_key=True)

    payer_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id"), nullable=False
    )

    name: Mapped[str] = mapped_column(
        String(256), nullable=True
    )

    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_constraint=True, validate_strings=True),
        nullable=False, default=Currency.USD
    )

    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    share_type: Mapped[ShareType] = mapped_column(
        Enum(ShareType),
        nullable=False,
        default=ShareType.EQUAL
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    last_modified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    payer: Mapped["User"] = relationship(
        back_populates="expenses_paid", foreign_keys=[payer_id]
    )
    created_by_user: Mapped["User"] = relationship(
        back_populates="expenses_created", foreign_keys=[created_by]
    )

    group: Mapped["Group"] = relationship(
        back_populates="expenses"
    )

    splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan"
    )

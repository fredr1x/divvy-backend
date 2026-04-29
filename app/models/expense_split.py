from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SplitStatus, SplitType

if TYPE_CHECKING:
    from app.models.group_expense import GroupExpense
    from app.models.user import User


class ExpenseSplit(Base):
    __tablename__ = 'expense_splits'

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    group_expense_id: Mapped[int] = mapped_column(
        ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=False
    )

    owed_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2, asdecimal=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

    status: Mapped[SplitStatus] = mapped_column(
        "split_status",
        Enum(SplitStatus, name='split_status'),
        nullable=False,
        default=SplitStatus.PENDING,
    )

    split_type: Mapped[SplitType] = mapped_column(
        Enum(SplitType, name='split_type'),
        nullable=False,
        default=SplitType.ORIGINAL,
    )

    refund_to_user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id"), nullable=True
    )

    paid_at: Mapped[datetime | None] = mapped_column(
        DateTime, nullable=True
    )

    last_modified_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=True
    )

    user: Mapped["User"] = relationship(
        back_populates="expense_splits",
        foreign_keys=[user_id],
    )

    refund_to_user: Mapped["User"] = relationship(
        foreign_keys=[refund_to_user_id],
    )

    expense: Mapped["GroupExpense"] = relationship(back_populates="splits")

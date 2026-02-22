from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Enum, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ShareType

if TYPE_CHECKING:
    from app.models.group_expense import GroupExpense
    from app.models.user import User


class ExpenseSplit(Base):
    __tablename__ = 'expense_splits'

    id: Mapped[int] = mapped_column(primary_key=True)

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    share_type: Mapped[ShareType] = mapped_column(
        Enum(ShareType), nullable=False, default=ShareType.EQUAL, name="share_type"
    )

    group_expense_id: Mapped[int] = mapped_column(
        ForeignKey("group_expenses.id"), nullable=False
    )

    owed_amount: Mapped[Numeric] = mapped_column(
        Numeric(10, 2, asdecimal=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )

    user: Mapped["User"] = relationship(back_populates="expense_splits")
    expense: Mapped["GroupExpense"] = relationship(back_populates="splits")

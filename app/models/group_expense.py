from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

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

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), nullable=False
    )

    created_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    payer: Mapped["User"] = relationship(
        back_populates="expenses_paid", foreign_keys=[payer_id]
    )
    created_by_user: Mapped["User"] = relationship(
        back_populates="expenses_created", foreign_keys=[created_by]
    )
    group: Mapped["Group"] = relationship(back_populates="expenses")
    splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="expense", cascade="all, delete-orphan"
    )

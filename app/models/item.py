from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, String, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.group_expense import GroupExpense
    from app.models.item_split import ItemSplit


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)

    group_expense_id: Mapped[int] = mapped_column(
        ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=False
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)

    price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    quantity: Mapped[int] = mapped_column(default=1, nullable=False)

    total_price: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    expense: Mapped["GroupExpense"] = relationship(back_populates="items")

    item_splits: Mapped[list["ItemSplit"]] = relationship(
        back_populates="item", cascade="all, delete-orphan"
    )

from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.item import Item
    from app.models.user import User


class ItemSplit(Base):
    __tablename__ = "item_splits"

    __table_args__ = (
        UniqueConstraint("item_id", "user_id", name="uq_item_split_item_user"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    item_id: Mapped[int] = mapped_column(
        ForeignKey("items.id"), nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    share_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )

    item: Mapped["Item"] = relationship(back_populates="item_splits")

    user: Mapped["User"] = relationship(back_populates="item_splits")

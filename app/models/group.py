from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, String, ForeignKey, Enum, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums.currency import Currency

if TYPE_CHECKING:
    from app.models.group_expense import GroupExpense
    from app.models.user import User
    from app.models.user_group import UserGroup


class Group(Base):
    __tablename__ = "groups"

    id: Mapped[int] = mapped_column(primary_key=True)

    creator_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", onupdate="CASCADE")
    )

    name: Mapped[str] = mapped_column(String(255), nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now()
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(),
    )

    currency: Mapped[Currency] = mapped_column(
        Enum(Currency, name="currency", create_constraint=True, validate_strings=True),
        nullable=False, default=Currency.USD
    )

    invitation_link: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True
    )

    creator: Mapped["User"] = relationship(
        back_populates="created_groups", foreign_keys=[creator_id]
    )

    user_links: Mapped[list["UserGroup"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

    expenses: Mapped[list["GroupExpense"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )

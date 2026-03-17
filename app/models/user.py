from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.expense_split import ExpenseSplit
    from app.models.group import Group
    from app.models.group_expense import GroupExpense
    from app.models.refresh_token import RefreshToken
    from app.models.user_group import UserGroup


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(254), unique=True, index=True, nullable=False
    )

    first_name: Mapped[str] = mapped_column(String(256), nullable=False)

    last_name: Mapped[str] = mapped_column(String(256), nullable=False)

    password: Mapped[str | None] = mapped_column(String(256), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    auth_provider: Mapped[str] = mapped_column(
        String(32), default="local", nullable=False
    )

    google_sub: Mapped[str | None] = mapped_column(
        String(255), unique=True, nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.now(), nullable=False
    )

    refresh_tokens: Mapped[list["RefreshToken"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    created_groups: Mapped[list["Group"]] = relationship(
        back_populates="creator", foreign_keys="Group.creator_id"
    )

    group_links: Mapped[list["UserGroup"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    expenses_paid: Mapped[list["GroupExpense"]] = relationship(
        back_populates="payer", foreign_keys="GroupExpense.payer_id"
    )

    expenses_created: Mapped[list["GroupExpense"]] = relationship(
        back_populates="created_by_user", foreign_keys="GroupExpense.created_by"
    )

    expense_splits: Mapped[list["ExpenseSplit"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
        foreign_keys="ExpenseSplit.user_id",
    )

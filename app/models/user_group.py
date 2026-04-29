from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Enum, DateTime, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import GroupRole

if TYPE_CHECKING:
    from app.models.group import Group
    from app.models.user import User


class UserGroup(Base):
    __tablename__ = "user_groups"

    id: Mapped[int] = mapped_column(primary_key=True)

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True,
    )

    group_role: Mapped[GroupRole] = mapped_column(
        Enum(GroupRole, name="group_role", create_constraint=True, validate_strings=True)
    )

    joined_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now(),
    )

    user: Mapped["User"] = relationship(back_populates="group_links")

    group: Mapped["Group"] = relationship(back_populates="user_links")

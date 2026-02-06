from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models import RefreshToken


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)

    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(255), nullable=False)

    last_name: Mapped[str] = mapped_column(String(255), nullable=False)

    password: Mapped[str | None] = mapped_column(String(255), nullable=True)

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

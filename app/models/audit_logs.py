from datetime import datetime

from app.db.base import Base
from app.models.enums import ActionType, ActionStatus
from sqlalchemy import ForeignKey, DateTime, Enum, String, JSON, Integer
from sqlalchemy.orm import mapped_column, Mapped


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )

    ip_address: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    action_type: Mapped[ActionType] = mapped_column(
        Enum(ActionType, name="action_type"),
        nullable=False
    )

    entity_id: Mapped[int] = mapped_column(
        Integer,
        nullable=True
    )

    entity_name: Mapped[str] = mapped_column(
        String,
        nullable=False
    )

    old_values: Mapped[dict] = mapped_column(
        JSON, nullable=True
    )

    new_values: Mapped[dict] = mapped_column(
        JSON,
        nullable=True
    )

    action_status: Mapped[ActionStatus] = mapped_column(
        Enum(ActionStatus, name="action_status"),
        nullable=False
    )

    message: Mapped[str] = mapped_column(
        String,
        nullable=True
    )

    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )

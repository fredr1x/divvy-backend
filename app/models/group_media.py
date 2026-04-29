from datetime import datetime

from app.db.base import Base

from sqlalchemy import ForeignKey, Enum, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.enums.media_category import MediaCategory


class GroupMedia(Base):
    __tablename__ = "group_media"

    id: Mapped[int] = mapped_column(primary_key=True)

    group_id: Mapped[int] = mapped_column(
        ForeignKey("groups.id", ondelete="CASCADE"), nullable=False
    )

    uploaded_by: Mapped[int] = mapped_column(
        ForeignKey("users.id"), nullable=False
    )

    expense_id: Mapped[int | None] = mapped_column(
        ForeignKey("group_expenses.id", ondelete="CASCADE"), nullable=True
    )

    category: Mapped[MediaCategory] = mapped_column(
        Enum(
            MediaCategory,
            name="media_category",
        ),
        nullable=False
    )

    file_url: Mapped[str] = mapped_column(
        String, nullable=False, index=True
    )

    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.now
    )

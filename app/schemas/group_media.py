from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums.media_category import MediaCategory


class GroupMediaCreate(BaseModel):
    group_id: int
    expense_id: Optional[int] = None
    file_url: str
    category: MediaCategory
    uploaded_at: datetime = Field(default_factory=datetime.now)


class GroupMediaRead(BaseModel):
    id: int
    group_id: int
    uploaded_by: int
    expense_id: Optional[int] = None
    category: MediaCategory
    file_url: str
    uploaded_at: datetime

    model_config = ConfigDict(from_attributes=True)

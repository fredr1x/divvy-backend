from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums.currency import Currency

GroupName = Annotated[str, Field(min_length=1)]


class GroupUpdate(BaseModel):
    name: GroupName
    currency: Currency


class GroupCreate(BaseModel):
    name: GroupName
    creator_id: int
    currency: Currency


class GroupRead(BaseModel):
    id: int
    name: str
    creator_id: int
    created_at: datetime
    is_active: bool
    currency: Currency
    invitation_link: str

    model_config = ConfigDict(from_attributes=True)

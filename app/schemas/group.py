from datetime import datetime

from pydantic import BaseModel, ConfigDict
from app.models.enums.currency import Currency

class GroupUpdate(BaseModel):
    id: int
    name: str
    currency: Currency


class GroupCreate(BaseModel):
    name: str
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

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import GroupRole


class UserGroupRead(BaseModel):
    id: int
    group_id: int
    user_id: int
    group_role: GroupRole
    joined_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserGroupAddMemberByEmail(BaseModel):
    email: str
    group_id: int


class UserGroupJoinByInvitationLink:
    id: int
    user_id: int

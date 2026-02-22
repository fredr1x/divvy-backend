from datetime import datetime

from pydantic import BaseModel

from app.models.enums import GroupRole


class UserGroupRead(BaseModel):
    id: int
    group_id: int
    user_id: int
    group_role: GroupRole
    joined_at: datetime


class UserGroupAddMemberByEmail(BaseModel):
    email: str
    group_id: int


class UserGroupJoinByInvitationLink:
    id: int
    user_id: int
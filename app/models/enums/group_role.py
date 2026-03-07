import enum


class GroupRole(str, enum.Enum):
    CREATOR = "CREATOR"
    MODERATOR = "MODERATOR"
    MEMBER = "MEMBER"

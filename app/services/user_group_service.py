from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, User, UserGroup
from app.models.enums import GroupRole
from app.schemas import UserGroupAddMemberByEmail
from app.schemas.user import UserRead
from app.schemas.user_group import UserGroupRead


def get_group_members(
        id: int,
        db: Session
) -> list[UserRead]:
    statement = (select(User)
                 .join(UserGroup, UserGroup.user_id == User.id)
                 .where(UserGroup.group_id == id))

    return list(db.scalars(statement))


def add_to_group_by_email(
    payload: UserGroupAddMemberByEmail,
    db: Session,
    current_user: User
) -> UserGroupRead:

    email = payload.email
    group_id = payload.group_id

    select_user_query = select(User).where(User.email == email)
    user_to_add = db.scalar(select_user_query)

    if not user_to_add:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")

    select_for_existence = select(UserGroup).where(UserGroup.group_id == group_id).where(UserGroup.user_id == user_to_add.id)
    user_exists = db.scalar(select_for_existence)

    if user_exists:
        raise HTTPException(status_code=409, detail=f"User with email {email} already member of group {group_id}")

    select_user_group_query = (select(UserGroup)
                                .join(User, User.id == UserGroup.user_id)
                                .where(UserGroup.group_id == group_id)
                                .where(User.id == current_user.id))

    user_group = db.scalar(select_user_group_query)

    if not user_group:
        raise HTTPException(status_code=404, detail=f"User group information for user {current_user} and for group {group_id} not found")

    group_role = user_group.group_role

    if group_role != GroupRole.CREATOR and group_role != GroupRole.MODERATOR:
        raise HTTPException(status_code=403, detail="Not enough permissions to add user to group")

    user_group_to_save = UserGroup(group_id=group_id, user_id=user_to_add.id, group_role=GroupRole.MEMBER, )
    db.add(user_group_to_save)
    db.commit()
    db.refresh(user_group_to_save)
    return user_group_to_save


def join_by_invitation_link(
    link: str,
    db: Session,
    current_user: User
) -> UserGroupRead:

    link = extract_link(link)
    print(link)

    statement = select(Group).where(Group.invitation_link.endswith(f"/invite/{link}"))
    group = db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with invitation link {link} not found")

    existing_member_statement = (
        select(UserGroup)
        .where(UserGroup.group_id == group.id)
        .where(UserGroup.user_id == current_user.id)
    )
    existing_member = db.scalar(existing_member_statement)

    if existing_member:
        raise HTTPException(status_code=409, detail="User already member of this group")

    user_group_to_save = UserGroup(
        group_id=group.id,
        user_id=current_user.id,
        group_role=GroupRole.MEMBER,
    )
    db.add(user_group_to_save)
    db.commit()
    db.refresh(user_group_to_save)
    return user_group_to_save


def extract_link(link: str) -> str:
    token = link.strip()
    if "/invite/" in token:
        token = token.rsplit("/invite/", 1)[-1]
    if not token:
        raise HTTPException(status_code=400, detail="Invitation link is required")
    return token

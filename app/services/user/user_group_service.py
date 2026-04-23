from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


from app.services.email.email_service import send_invite_email
from app.models import Group, User, UserGroup
from app.models.enums import GroupRole
from app.schemas import UserGroupAddMemberByEmail
from app.schemas.user import UserRead
from app.schemas.user_group import UserGroupRead


async def get_group_by_id(
        db: AsyncSession,
        id: int
) -> Group:
    statement = select(Group).where(Group.id == id)
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {id} not found")

    return group


async def get_group_members(
        db: AsyncSession,
        id: int
) -> list[UserRead]:
    statement = (select(User)
                 .join(UserGroup, UserGroup.user_id == User.id)
                 .where(UserGroup.group_id == id, UserGroup.is_active))

    return list((await db.scalars(statement)).all())


async def invite_to_group_by_email(
    db: AsyncSession,
    payload: UserGroupAddMemberByEmail,
    current_user: User
) -> UserGroupRead:

    email = payload.email
    group_id = payload.group_id
    select_group = select(Group).where(Group.id == group_id)
    group = await db.scalar(select_group)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {group_id} not found")

    select_user_query = select(User).where(User.email == email)
    user_to_add = await db.scalar(select_user_query)

    if not user_to_add:
        raise HTTPException(status_code=404, detail=f"User with email {email} not found")

    select_for_existence = select(UserGroup).where(UserGroup.group_id == group_id).where(UserGroup.user_id == user_to_add.id)
    user_exists = await db.scalar(select_for_existence)

    if user_exists:
        raise HTTPException(status_code=409, detail=f"User with email {email} already member of group {group_id}")

    select_user_group_query = (select(UserGroup)
                                .join(User, User.id == UserGroup.user_id)
                                .where(UserGroup.group_id == group_id)
                                .where(User.id == current_user.id))

    user_group = await db.scalar(select_user_group_query)

    if not user_group:
        raise HTTPException(status_code=404, detail=f"User group information for user {current_user} and for group {group_id} not found")

    user_group_to_save = UserGroup(group_id=group_id, user_id=user_to_add.id, group_role=GroupRole.MEMBER, is_active=False)

    send_invite_email(email, group.name, group.invitation_link)

    db.add(user_group_to_save)
    await db.flush()
    await db.refresh(user_group_to_save)
    return UserGroupRead.model_validate(user_group_to_save)


async def join_by_invitation_link(
    db: AsyncSession,
    link: str,
    current_user: User
) -> UserGroupRead:

    link = extract_link(link)

    statement = select(Group).where(Group.invitation_link.endswith(f"/invite/{link}"))
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with invitation link {link} not found")

    existing_member_statement = (
        select(UserGroup)
        .where(UserGroup.group_id == group.id)
        .where(UserGroup.user_id == current_user.id)
    )
    existing_member = await db.scalar(existing_member_statement)

    if not existing_member:
        raise HTTPException(status_code=404, detail=f"User with invitation link {link} not found")

    if existing_member:
        if existing_member.is_active:
            return existing_member
        existing_member.is_active = True
        await db.flush()
        await db.refresh(existing_member)
        return existing_member

    user_group_to_save = UserGroup(
        group_id=group.id,
        user_id=current_user.id,
        group_role=GroupRole.MEMBER,
        is_active=True
    )
    db.add(user_group_to_save)
    await db.flush()
    await db.refresh(user_group_to_save)
    return UserGroupRead.model_validate(user_group_to_save)


async def is_member_of_group(
        db: AsyncSession,
        group_id: int,
        user_id: int
) -> bool:
    find_by_user_id_and_group_id = (select(UserGroup)
                                    .where(UserGroup.group_id == group_id,
                                                       UserGroup.user_id == user_id))

    user_group = await db.scalar(find_by_user_id_and_group_id)

    if not user_group:
        return False

    return True

def extract_link(link: str) -> str:
    token = link.strip()
    if "/invite/" in token:
        token = token.rsplit("/invite/", 1)[-1]
    if not token:
        raise HTTPException(status_code=400, detail="Invitation link is required")
    return token

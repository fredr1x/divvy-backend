import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, User, UserGroup
from app.models.enums.currency import Currency
from app.models.enums.group_role import GroupRole
from app.schemas.group import GroupRead, GroupUpdate


async def create_group(
    db: AsyncSession, name: str, creator_id: int, currency: Currency
) -> GroupRead:
    group = Group(
        name=name,
        creator_id=creator_id,
        currency=currency,
        invitation_link=generate_invitation_link(),
    )

    statement = (
        select(Group).where(Group.creator_id == creator_id).where(Group.name == name)
    )
    group_exists = await db.scalar(statement)

    if group_exists:
        raise HTTPException(
            status_code=400, detail=f"Group with name {name} already exists"
        )

    db.add(group)
    await db.flush()
    await add_creator_to_user_group(db, group.id, creator_id)
    await db.refresh(group)
    return GroupRead.model_validate(group)


async def get_group_by_id(db: AsyncSession, id: int) -> GroupRead:
    statement = select(Group).where(Group.id == id)
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return group


async def get_groups_by_user(db: AsyncSession, user: User) -> list[GroupRead]:
    statement = (
        select(Group)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == user.id)
    )
    return list((await db.scalars(statement)).all())


async def get_invitation_link_by_group_id(db: AsyncSession, id: int) -> str:
    statement = select(Group).where(Group.id == id)
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {id} not found")

    return group.invitation_link


async def update_group(db: AsyncSession, group_update: GroupUpdate) -> GroupRead:
    statement = select(Group).where(Group.id == group_update.id)
    group = await db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    group.name = group_update.name
    group.currency = group_update.currency
    await db.refresh(group)
    return group


def generate_invitation_link() -> str:
    return str("http://localhost:8001/invite/" + uuid.uuid4().__str__())


async def add_creator_to_user_group(
    db: AsyncSession, group_id: int, creator_id: int
) -> None:
    user_group = UserGroup(
        group_id=group_id,
        user_id=creator_id,
        group_role=GroupRole.CREATOR,
    )

    db.add(user_group)

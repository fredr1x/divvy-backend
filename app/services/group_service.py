import uuid

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Group, UserGroup, User

from app.models.enums.currency import Currency
from app.models.enums.group_role import GroupRole

from app.schemas.group import GroupUpdate, GroupRead


def create_group(
        db: Session,
        name: str,
        creator_id: int,
        currency: Currency
) -> GroupRead:
    group = Group(
        name=name,
        creator_id=creator_id,
        currency=currency,
        invitation_link=generate_invitation_link(),
    )

    statement = select(Group).where(Group.creator_id == creator_id).where(Group.name == name)
    group_exists = db.scalar(statement)

    if group_exists:
        raise HTTPException(status_code=400, detail=f"Group with name {name} already exists")

    db.add(group)
    db.flush()
    add_creator_to_user_group(db, group.id, creator_id)
    db.commit()
    db.refresh(group)
    return group


def get_group_by_id(
        db: Session,
        id: int
) -> GroupRead:
    statement = select(Group).where(Group.id == id)
    group = db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return group


def get_groups_by_user(
        db: Session,
        user: User
) -> list[GroupRead]:
    statement = (
        select(Group)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == user.id)
    )
    return list(db.scalars(statement))

def get_invitation_link_by_group_id(
        db: Session,
        id: int
)-> str:
    statement = select(Group).where(Group.id == id)
    group = db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail=f"Group with id {id} not found")

    return group.invitation_link

def update_group(
        db: Session,
        group_update: GroupUpdate
) -> GroupRead:
    statement = select(Group).where(Group.id == group_update.id)
    group = db.scalar(statement)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    group.name = group_update.name
    group.currency = group_update.currency
    db.commit()
    db.refresh(group)
    return group

def generate_invitation_link() -> str:
    return str("http://localhost:8001/invite/" + uuid.uuid4().__str__())


def add_creator_to_user_group(db: Session, group_id: int, creator_id: int) -> None:
    user_group = UserGroup(
        group_id=group_id,
        user_id=creator_id,
        group_role=GroupRole.CREATOR,
    )

    db.add(user_group)

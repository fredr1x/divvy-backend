import uuid

from app.models.enums import ActionType, ActionStatus
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Group, User, UserGroup, AuditLog
from app.models.enums.currency import Currency
from app.models.enums.group_role import GroupRole
from app.schemas.group import GroupRead, GroupUpdate
from app.services.audit.audit_logs_service import create_failed_audit_log


async def create_group(
    ip_address: str,
    db: AsyncSession,
    name: str,
    creator_id: int,
    currency: Currency,
    current_user: User,
) -> GroupRead:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.CREATE,
        ip_address=ip_address,
        entity_name="GROUP",
    )

    group_exists = await db.scalar(select(Group).where(Group.creator_id == creator_id).where(Group.name == name))

    if group_exists:
        message=f"Group with name {name} already exists"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    if len(name) > 255:
        message="Group name must be at most 255 characters"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    group = Group(
        name=name,
        creator_id=creator_id,
        currency=currency,
        invitation_link=generate_invitation_link(),
    )

    db.add(group)
    try:
        await db.flush()
    except DBAPIError as exc:
        await db.rollback()
        if _is_varchar_limit_error(exc):
            message="Group name must be at most 255 characters"
            await create_failed_audit_log(db, audit_log, message)
            raise HTTPException(status_code=400, detail=message) from exc
        raise

    audit_log.entity_id=group.id
    audit_log.message="Successfully created group"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    await add_creator_to_user_group(db, group.id, creator_id)
    await db.refresh(group)
    return GroupRead.model_validate(group)


async def get_group_by_id(
    ip_address: str,
    db: AsyncSession,
    id: int,
    current_user: User,
) -> GroupRead:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="GROUP",
    )

    group = await db.scalar(select(Group)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == current_user.id, UserGroup.group_id == id))

    if not group:
        message="Group not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id=group.id
    audit_log.message="Successfully retrieved group"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    return group


async def get_groups_by_user(db: AsyncSession, user: User) -> list[GroupRead]:
    statement = (
        select(Group)
        .join(UserGroup, UserGroup.group_id == Group.id)
        .where(UserGroup.user_id == user.id)
    )
    return list((await db.scalars(statement)).all())


async def get_invitation_link_by_group_id(
    ip_address: str,
    db: AsyncSession,
    id: int,
    current_user: User,
) -> str:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.READ,
        ip_address=ip_address,
        entity_name="GROUP",
    )

    group = await db.scalar(select(Group)
                            .join(UserGroup, UserGroup.group_id == Group.id)
                            .where(UserGroup.user_id == current_user.id, UserGroup.group_id == id))

    if not group:
        message = "Group not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.entity_id=group.id
    audit_log.message="Successfully retrieved group invitation link"
    audit_log.action_status=ActionStatus.SUCCESS

    db.add(audit_log)
    await db.commit()

    return group.invitation_link


async def update_group(
    ip_address: str,
    db: AsyncSession,
    group_id: int,
    group_update: GroupUpdate,
    current_user: User,
) -> GroupRead:

    audit_log: AuditLog = AuditLog(
        user_id=current_user.id,
        action_type=ActionType.UPDATE,
        ip_address=ip_address,
        entity_name="GROUP",
    )

    group = await db.scalar(select(Group)
                            .join(UserGroup, UserGroup.group_id == Group.id)
                            .where(UserGroup.user_id == current_user.id, UserGroup.group_id == group_id))

    if not group:
        message="Group not found"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=404, detail=message)

    audit_log.old_values=[GroupRead.model_validate(group).model_dump(mode="json")]

    group.name = group_update.name
    group.currency = group_update.currency
    if len(group.name) > 255:
        message = "Group name must be at most 255 characters"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    try:
        await db.flush()
    except DBAPIError as exc:
        await db.rollback()
        if _is_varchar_limit_error(exc):
            message = "Group name must be at most 255 characters"
            await create_failed_audit_log(db, audit_log, message)
            raise HTTPException(status_code=400, detail=message)
        raise

    audit_log.new_values=[GroupRead.model_validate(group).model_dump(mode="json")]
    audit_log.entity_id=group.id
    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Group updated successfully"

    db.add(audit_log)
    await db.commit()

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


def _is_varchar_limit_error(exc: DBAPIError) -> bool:
    return "value too long for type character varying(255)" in str(exc).lower()

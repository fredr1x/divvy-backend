from app.models.enums import ActionType, ActionStatus
from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User, UserGroup, AuditLog
from app.models.enums.media_category import MediaCategory
from app.models.group_media import GroupMedia
from app.schemas import GroupMediaCreate, GroupMediaRead
from app.services.minio.minio_service import minio_service
from app.services.user.user_group_service import is_member_of_group
from app.services.audit.audit_logs_service import create_failed_audit_log


async def find_by_id(media_id: int, db: AsyncSession) -> GroupMedia:
    group_media = await db.scalar(select(GroupMedia).where(GroupMedia.id == media_id))
    if not group_media:
        raise HTTPException(status_code=404, detail="Group media not found")
    return group_media


async def find_by_key(key: str, db: AsyncSession) -> GroupMedia:
    group_media = await db.scalar(select(GroupMedia).where(GroupMedia.file_url == key))
    if not group_media:
        raise HTTPException(status_code=404, detail="Group media not found")
    return group_media


async def get_group_media(
    id: int, db: AsyncSession, current_user_id: int
) -> GroupMediaRead:
    group_media = await find_by_id(id, db)
    if not await is_member_of_group(db, group_media.group_id, current_user_id):
        raise HTTPException(status_code=400, detail="User is not a member of the group")
    return GroupMediaRead.model_validate(group_media)


async def get_all_group_media(
    group_id: int, db: AsyncSession, current_user_id: int
) -> list[GroupMediaRead]:
    if not await is_member_of_group(db, group_id, current_user_id):
        raise HTTPException(status_code=400, detail="User is not a member of the group")

    group_media: list[GroupMedia] = list(
        (await db.scalars(select(GroupMedia).where(GroupMedia.group_id == group_id))).all()
    )
    return [GroupMediaRead.model_validate(m) for m in group_media]


async def create_group_media(
    ip_address: str,
    db: AsyncSession,
    payload: GroupMediaCreate,
    current_user_id: int,
) -> GroupMediaRead:

    audit_log: AuditLog = AuditLog(
        user_id=current_user_id,
        action_type=ActionType.CREATE,
        ip_address=ip_address,
        entity_name="GROUP_MEDIA",
    )

    group_id: int = payload.group_id

    user_group = await db.scalar(
        select(UserGroup).where(
            UserGroup.group_id == group_id, UserGroup.user_id == current_user_id
        )
    )

    if not user_group:
        message="User is not a member of the group"
        await create_failed_audit_log(db, audit_log, message)
        raise HTTPException(status_code=400, detail=message)

    group_media = GroupMedia(
        group_id=group_id,
        uploaded_by=current_user_id,
        expense_id=payload.expense_id,
        category=payload.category,
        file_url=payload.file_url,
        uploaded_at=payload.uploaded_at,
    )

    db.add(group_media)
    await db.flush()

    audit_log.entity_id=group_media.id
    audit_log.action_status=ActionStatus.SUCCESS
    audit_log.message="Successfully created group media"

    db.add(audit_log)
    await db.commit()

    return GroupMediaRead.model_validate(group_media)


async def validate_user_access(key: str, current_user_id: int, db: AsyncSession) -> None:
    media: GroupMedia = await find_by_key(key, db)
    if not await is_member_of_group(db, media.group_id, current_user_id):
        raise HTTPException(status_code=404, detail="User has no access to this media")


async def upload_photo(
    ip_address: str,
    group_id: int,
    db: AsyncSession,
    current_user: User,
    files: list[UploadFile],
):
    return await upload_media(ip_address,
                              group_id,
                              db,
                              current_user,
                              files,
                              MediaCategory.PHOTO
                              )


async def upload_receipt(
    ip_address: str,
    group_id: int,
    expense_id: int | None,
    db: AsyncSession,
    current_user: User,
    files: list[UploadFile],
):
    return await upload_media(
        ip_address,
        group_id,
        db,
        current_user,
        files,
        MediaCategory.RECEIPT,
        expense_id
    )


async def upload_media(
    ip_address: str,
    group_id: int,
    db: AsyncSession,
    current_user: User,
    files: list[UploadFile],
    media_category: MediaCategory,
    expense_id: int | None = None,
):
    created_media = []
    for f in files:
        key: str = minio_service.generate_object_key(group_id, media_category.name, f.filename)

        payload = GroupMediaCreate(
            group_id=group_id,
            expense_id=expense_id,
            file_url=key,
            category=media_category,
        )

        minio_service.upload(f.file.read(), key, f.content_type)
        created = await create_group_media(ip_address, db, payload, current_user.id)
        created_media.append(created)



    return {"items": created_media}

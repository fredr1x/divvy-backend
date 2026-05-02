from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog
from app.models.enums import ActionStatus


async def list_recent_audit_logs_for_user(
    db: AsyncSession,
    *,
    user_id: int,
    limit: int,
) -> list[AuditLog]:
    stmt = (
        select(AuditLog)
        .where(AuditLog.user_id == user_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def create_log(
    db: AsyncSession,
    audit_log: AuditLog,
    message: str,
) -> None:
    audit_log.message = message
    db.add(audit_log)
    await db.commit()


async def create_failed_audit_log(db: AsyncSession, audit_log: AuditLog, message: str):
    audit_log.message = message
    audit_log.action_status = ActionStatus.FAILED
    db.add(audit_log)
    await db.commit()

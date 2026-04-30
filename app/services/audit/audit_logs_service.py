from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_logs import AuditLog
from app.models.enums import ActionStatus


async def create_log(
    db: AsyncSession,
    audit_log: AuditLog,
    message: str,
) -> None:
    audit_log.message = message
    audit_log.action_status=ActionStatus.SUCCESS
    db.add(audit_log)
    await db.commit()


async def create_failed_audit_log(db: AsyncSession, audit_log: AuditLog, message: str):
    audit_log.message = message
    audit_log.action_status = ActionStatus.FAILED
    db.add(audit_log)
    await db.commit()

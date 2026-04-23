from app.models.audit_logs import AuditLog
from app.models.enums import ActionType, ActionStatus
from sqlalchemy.ext.asyncio import AsyncSession


async def create_log(
    db: AsyncSession,
    user_id: int,
    ip_address: str,
    action_type: ActionType,
    entity_id: int,
    entity_name: str,
    old_values: dict,
    new_values: dict,
    action_status: ActionStatus,
) -> None:
    audit_log = AuditLog(
        user_id=user_id,
        ip_address=ip_address,
        action_type=action_type,
        entity_id=entity_id,
        entity_name=entity_name,
        old_values=old_values,
        new_values=new_values,
        action_status=action_status,
    )

    db.add(audit_log)
    await db.commit()


async def create_failed_audit_log(db: AsyncSession, audit_log: AuditLog, message: str):
    audit_log.message=message
    audit_log.action_status=ActionStatus.FAILED
    db.add(audit_log)
    await db.commit()

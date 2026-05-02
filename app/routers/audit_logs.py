from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.dependencies import get_current_verified_user
from app.models.user import User
from app.schemas.audit_log import AuditLogRead
from app.services.audit.audit_logs_service import list_recent_audit_logs_for_user

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

_DEFAULT_LIMIT = 50
_MAX_LIMIT = 200


@router.get("", response_model=list[AuditLogRead])
async def list_audit_logs(
    limit: int = Query(
        default=_DEFAULT_LIMIT,
        ge=1,
        le=_MAX_LIMIT,
        description="Number of most recent logs to return (newest first).",
    ),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
) -> list[AuditLogRead]:
    """
    Return the last *limit* audit log rows for the authenticated user,
    ordered by timestamp descending.
    """
    rows = await list_recent_audit_logs_for_user(
        db, user_id=current_user.id, limit=limit
    )
    return [AuditLogRead.model_validate(r) for r in rows]

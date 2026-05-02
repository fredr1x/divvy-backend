from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import ActionStatus, ActionType


class AuditLogRead(BaseModel):
    id: int
    user_id: int | None
    ip_address: str
    action_type: ActionType
    entity_id: int | None
    entity_name: str
    old_values: list[dict] | None
    new_values: list[dict] | None
    action_status: ActionStatus
    message: str | None
    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)

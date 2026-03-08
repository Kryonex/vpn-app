from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


SystemStatusKind = Literal[
    'online',
    'degraded',
    'maintenance',
    'panel_unavailable',
    'server_unavailable',
]


class SystemStatusOut(BaseModel):
    status: SystemStatusKind = 'online'
    message: str | None = None
    maintenance_mode: bool = False
    show_to_all: bool = False
    scheduled_for: datetime | None = None
    updated_at: datetime | None = None


class AdminSystemStatusUpdateRequest(BaseModel):
    status: SystemStatusKind = 'online'
    message: str | None = Field(default=None, max_length=500)
    maintenance_mode: bool = False
    show_to_all: bool = True
    scheduled_for: datetime | None = None
    send_notification_to_all: bool = False


class AdminMessageSendRequest(BaseModel):
    message: str = Field(min_length=3, max_length=2000)
    user_id: UUID | None = None
    send_to_all: bool = False
    force: bool = False


class AdminMessageSendResponse(BaseModel):
    ok: bool
    target_count: int
    duplicate_blocked: bool = False
    audit_log_id: str | None = None

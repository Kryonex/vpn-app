from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


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
    message: str = Field(default='', max_length=2000)
    user_id: UUID | None = None
    send_to_all: bool = False
    force: bool = False
    image_data_url: str | None = Field(default=None, max_length=8_000_000)
    image_filename: str | None = Field(default=None, max_length=255)

    @model_validator(mode='after')
    def validate_payload(self) -> 'AdminMessageSendRequest':
        has_message = bool(self.message.strip())
        has_image = bool((self.image_data_url or '').strip())
        if not has_message and not has_image:
            raise ValueError('Message text or image is required')
        return self


class AdminMessageSendResponse(BaseModel):
    ok: bool
    target_count: int
    duplicate_blocked: bool = False
    audit_log_id: str | None = None


class NotificationQueueStatusOut(BaseModel):
    queue_key: str
    pending_count: int


class NotificationQueueClearResponse(BaseModel):
    ok: bool
    cleared_count: int

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
    publish_as_news: bool = False
    news_title: str | None = Field(default=None, max_length=120)

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


class PaymentSettingsOut(BaseModel):
    enabled: bool = True
    mode: str = 'direct'


class PaymentSettingsUpdateRequest(BaseModel):
    enabled: bool = True


class BackupAccessSettingsOut(BaseModel):
    enabled: bool = False
    url: str | None = None
    button_text: str = 'Открыть резервный доступ'
    message: str | None = None


class BackupAccessSettingsUpdateRequest(BaseModel):
    url: str | None = Field(default=None, max_length=2048)
    button_text: str = Field(default='Открыть резервный доступ', max_length=64)
    message: str | None = Field(default=None, max_length=500)


class TelegramProxyItemOut(BaseModel):
    id: str
    country: str
    proxy_url: str | None = None
    button_text: str = 'Подключить прокси'
    enabled: bool = False


class TelegramProxyItemUpdateRequest(BaseModel):
    id: str | None = None
    country: str = Field(min_length=1, max_length=64)
    proxy_url: str | None = Field(default=None, max_length=2048)
    button_text: str = Field(default='Подключить прокси', max_length=64)


class TelegramProxySettingsOut(BaseModel):
    proxy_url: str | None = None
    button_text: str = 'Подключить прокси'
    enabled: bool = False
    proxies: list[TelegramProxyItemOut] = Field(default_factory=list)


class TelegramProxySettingsUpdateRequest(BaseModel):
    proxy_url: str | None = Field(default=None, max_length=2048)
    button_text: str = Field(default='Подключить прокси', max_length=64)
    proxies: list[TelegramProxyItemUpdateRequest] = Field(default_factory=list)


class UserTelegramProxyOut(BaseModel):
    enabled: bool = False
    proxy_url: str | None = None
    button_text: str = 'Подключить прокси'
    proxies: list[TelegramProxyItemOut] = Field(default_factory=list)


class PublicTelegramAccessOut(BaseModel):
    enabled: bool = False
    bot_url: str | None = None
    proxies: list[TelegramProxyItemOut] = Field(default_factory=list)


class NewsItemOut(BaseModel):
    id: str
    title: str
    body: str
    image_data_url: str | None = None
    created_at: datetime


class SystemNewsListOut(BaseModel):
    items: list[NewsItemOut]


class AdminInboundOut(BaseModel):
    id: int
    remark: str | None = None
    protocol: str | None = None
    port: int | None = None


class PurchaseInboundSettingsOut(BaseModel):
    inbound_ids: list[int]


class PurchaseInboundSettingsUpdateRequest(BaseModel):
    inbound_ids: list[int] = Field(default_factory=list)


class FreeTrialSettingsOut(BaseModel):
    enabled: bool = False
    days: int = 3
    inbound_ids: list[int] = Field(default_factory=list)


class FreeTrialSettingsUpdateRequest(BaseModel):
    enabled: bool = False
    days: int = Field(default=3, ge=1, le=365)
    inbound_ids: list[int] = Field(default_factory=list)


class FreeTrialStatusOut(BaseModel):
    enabled: bool = False
    eligible: bool = False
    days: int = 3
    inbound_ids: list[int] = Field(default_factory=list)
    reason: str | None = None


class FreeTrialActivateResponse(BaseModel):
    ok: bool
    message: str
    key_id: UUID
    display_name: str
    expires_at: datetime
    connection_uri: str | None = None

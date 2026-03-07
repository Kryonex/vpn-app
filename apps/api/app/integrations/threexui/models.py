from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class ThreeXUIResponse(BaseModel):
    success: bool = False
    msg: str | None = None
    obj: Any | None = None


class ThreeXUIClientRecord(BaseModel):
    id: str
    email: str | None = None
    enable: bool | None = None
    expiryTime: int | None = None


class ThreeXUIInbound(BaseModel):
    id: int
    remark: str | None = None
    port: int | None = None
    protocol: str | None = None


class ThreeXUICreatedClient(BaseModel):
    client_uuid: str
    inbound_id: int
    email_remark: str
    connection_uri: str | None = None
    raw: dict[str, Any] | None = None


class ThreeXUIClientInfo(BaseModel):
    client_uuid: str
    inbound_id: int | None = None
    email_remark: str | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None
    raw: dict[str, Any] | None = None


class ThreeXUIPanelClientSnapshot(BaseModel):
    client_uuid: str
    inbound_id: int | None = None
    email_remark: str | None = None
    sub_id: str | None = None
    connection_uri: str | None = None
    raw: dict[str, Any] | None = None


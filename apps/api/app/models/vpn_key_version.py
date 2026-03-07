from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.vpn_key import VPNKey


class VPNKeyVersion(Base):
    __tablename__ = 'vpn_key_versions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vpn_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('vpn_keys.id', ondelete='CASCADE'), nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    threexui_client_uuid: Mapped[str] = mapped_column(String(64), nullable=False)
    inbound_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    email_remark: Mapped[str | None] = mapped_column(String(255), nullable=True)
    connection_uri: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    vpn_key: Mapped['VPNKey'] = relationship(back_populates='versions')


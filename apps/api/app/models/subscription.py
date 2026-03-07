from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import SubscriptionStatus, db_enum

if TYPE_CHECKING:
    from app.models.plan import Plan
    from app.models.vpn_key import VPNKey


class Subscription(Base):
    __tablename__ = 'subscriptions'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    vpn_key_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('vpn_keys.id', ondelete='CASCADE'), nullable=False)
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('plans.id', ondelete='RESTRICT'), nullable=False)
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        db_enum(SubscriptionStatus, name='subscriptionstatus'),
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )
    notified_expiring_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    notified_expired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    vpn_key: Mapped['VPNKey'] = relationship(back_populates='subscriptions', foreign_keys=[vpn_key_id])
    plan: Mapped['Plan'] = relationship(back_populates='subscriptions')


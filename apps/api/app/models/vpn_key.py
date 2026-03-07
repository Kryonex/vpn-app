from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import VPNKeyStatus, db_enum

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.subscription import Subscription
    from app.models.user import User
    from app.models.vpn_key_version import VPNKeyVersion


class VPNKey(Base):
    __tablename__ = 'vpn_keys'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[VPNKeyStatus] = mapped_column(
        db_enum(VPNKeyStatus, name='vpnkeystatus'),
        nullable=False,
        default=VPNKeyStatus.PENDING_PAYMENT,
    )
    display_name: Mapped[str] = mapped_column(String(128), nullable=False, default='My VPN Key')
    current_subscription_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey('subscriptions.id', use_alter=True, name='fk_vpn_keys_current_subscription_id'),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    owner: Mapped['User'] = relationship(back_populates='vpn_keys')
    versions: Mapped[list['VPNKeyVersion']] = relationship(back_populates='vpn_key', order_by='VPNKeyVersion.version')
    subscriptions: Mapped[list['Subscription']] = relationship(
        back_populates='vpn_key', foreign_keys='Subscription.vpn_key_id'
    )
    current_subscription: Mapped['Subscription | None'] = relationship(
        foreign_keys=[current_subscription_id], post_update=True
    )
    payments: Mapped[list['Payment']] = relationship(back_populates='vpn_key')


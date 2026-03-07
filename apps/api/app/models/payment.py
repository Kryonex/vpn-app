from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import Any, TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import PaymentOperation, PaymentProvider, PaymentStatus, db_enum

if TYPE_CHECKING:
    from app.models.payment_event import PaymentEvent
    from app.models.plan import Plan
    from app.models.user import User
    from app.models.vpn_key import VPNKey


class Payment(Base):
    __tablename__ = 'payments'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    vpn_key_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey('vpn_keys.id', ondelete='SET NULL'))
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('plans.id', ondelete='RESTRICT'), nullable=False)
    provider: Mapped[PaymentProvider] = mapped_column(
        db_enum(PaymentProvider, name='paymentprovider'),
        nullable=False,
        default=PaymentProvider.YOOKASSA,
    )
    operation: Mapped[PaymentOperation] = mapped_column(
        db_enum(PaymentOperation, name='paymentoperation'),
        nullable=False,
    )
    external_payment_id: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(8), nullable=False)
    status: Mapped[PaymentStatus] = mapped_column(
        db_enum(PaymentStatus, name='paymentstatus'),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    confirmation_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    idempotence_key: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    bonus_days_applied: Mapped[int] = mapped_column(nullable=False, default=0)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    succeeded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    user: Mapped['User'] = relationship(back_populates='payments')
    vpn_key: Mapped['VPNKey | None'] = relationship(back_populates='payments')
    plan: Mapped['Plan'] = relationship(back_populates='payments')
    events: Mapped[list['PaymentEvent']] = relationship(back_populates='payment')


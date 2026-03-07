from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.models.enums import ReferralStatus

if TYPE_CHECKING:
    from app.models.referral_reward import ReferralReward
    from app.models.user import User


class Referral(Base):
    __tablename__ = 'referrals'
    __table_args__ = (UniqueConstraint('referred_user_id', name='uq_referrals_referred_user_id'),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referrer_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    referred_user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    status: Mapped[ReferralStatus] = mapped_column(nullable=False, default=ReferralStatus.PENDING)
    qualified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rewarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())

    referrer: Mapped['User'] = relationship(back_populates='referrals_sent', foreign_keys=[referrer_user_id])
    referred: Mapped['User'] = relationship(back_populates='referrals_received', foreign_keys=[referred_user_id])
    reward: Mapped['ReferralReward | None'] = relationship(back_populates='referral', uselist=False)


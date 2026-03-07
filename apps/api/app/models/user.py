from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.payment import Payment
    from app.models.referral import Referral
    from app.models.telegram_account import TelegramAccount
    from app.models.vpn_key import VPNKey


class User(Base):
    __tablename__ = 'users'

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    referral_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    bonus_days_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    telegram_account: Mapped['TelegramAccount | None'] = relationship(back_populates='user', uselist=False)
    vpn_keys: Mapped[list['VPNKey']] = relationship(back_populates='owner')
    payments: Mapped[list['Payment']] = relationship(back_populates='user')
    referrals_sent: Mapped[list['Referral']] = relationship(
        back_populates='referrer', foreign_keys='Referral.referrer_user_id'
    )
    referrals_received: Mapped[list['Referral']] = relationship(
        back_populates='referred', foreign_keys='Referral.referred_user_id'
    )


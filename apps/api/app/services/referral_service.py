from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.bonus_day_ledger import BonusDayLedger
from app.models.enums import ReferralStatus
from app.models.payment import Payment
from app.models.referral import Referral
from app.models.referral_reward import ReferralReward
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository


class ReferralService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.referral_repo = ReferralRepository(session)

    @staticmethod
    def normalize_referral_code(raw: str | None) -> str | None:
        if not raw:
            return None
        if raw.startswith('ref_'):
            return raw[4:]
        return raw

    async def link_referred_user(self, referred_user: User, referral_code: str | None) -> None:
        normalized = self.normalize_referral_code(referral_code)
        if not normalized:
            return

        existing = await self.referral_repo.get_by_referred_user(referred_user.id)
        if existing:
            return

        referrer = await self.user_repo.get_by_referral_code(normalized)
        if not referrer or referrer.id == referred_user.id:
            return

        await self.referral_repo.create_pending(referrer_user_id=referrer.id, referred_user_id=referred_user.id)

    async def apply_referral_reward_if_eligible(self, referred_user_id: UUID, source_payment: Payment) -> None:
        referral = await self.referral_repo.get_by_referred_user(referred_user_id)
        if not referral or referral.status not in {ReferralStatus.PENDING, ReferralStatus.QUALIFIED}:
            return

        succeeded_count = await self.payment_repo.count_succeeded_by_user(referred_user_id)
        if succeeded_count != 1:
            return

        bonus_days = self.settings.referral_bonus_days
        referrer = await self.session.scalar(select(User).where(User.id == referral.referrer_user_id).with_for_update())
        if not referrer:
            return

        referrer.bonus_days_balance += bonus_days
        ledger = BonusDayLedger(
            user_id=referrer.id,
            related_referral_id=referral.id,
            related_payment_id=source_payment.id,
            days_delta=bonus_days,
            reason='referral_first_payment_reward',
            balance_after=referrer.bonus_days_balance,
        )
        reward = ReferralReward(
            referral_id=referral.id,
            user_id=referrer.id,
            source_payment_id=source_payment.id,
            bonus_days=bonus_days,
        )

        referral.status = ReferralStatus.REWARDED
        referral.qualified_at = datetime.now(timezone.utc)
        referral.rewarded_at = datetime.now(timezone.utc)

        self.session.add_all([ledger, reward])

    async def adjust_bonus_days(
        self,
        user_id: UUID,
        days_delta: int,
        reason: str,
        related_referral_id: UUID | None = None,
        related_payment_id: UUID | None = None,
    ) -> None:
        user = await self.session.scalar(select(User).where(User.id == user_id).with_for_update())
        if not user:
            raise ValueError('User not found')

        new_balance = user.bonus_days_balance + days_delta
        if new_balance < 0:
            raise ValueError('Insufficient bonus days balance')

        user.bonus_days_balance = new_balance
        ledger = BonusDayLedger(
            user_id=user.id,
            related_referral_id=related_referral_id,
            related_payment_id=related_payment_id,
            days_delta=days_delta,
            reason=reason,
            balance_after=new_balance,
        )
        self.session.add(ledger)


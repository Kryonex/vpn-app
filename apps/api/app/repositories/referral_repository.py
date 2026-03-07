from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import ReferralStatus
from app.models.referral import Referral


class ReferralRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_referred_user(self, referred_user_id: UUID) -> Referral | None:
        stmt = (
            select(Referral)
            .where(Referral.referred_user_id == referred_user_id)
            .options(selectinload(Referral.referrer), selectinload(Referral.referred), selectinload(Referral.reward))
        )
        return await self.session.scalar(stmt)

    async def create_pending(self, referrer_user_id: UUID, referred_user_id: UUID) -> Referral:
        referral = Referral(
            referrer_user_id=referrer_user_id,
            referred_user_id=referred_user_id,
            status=ReferralStatus.PENDING,
        )
        self.session.add(referral)
        await self.session.flush()
        return referral

    async def count_invited(self, referrer_user_id: UUID) -> int:
        stmt = select(func.count(Referral.id)).where(Referral.referrer_user_id == referrer_user_id)
        return int((await self.session.scalar(stmt)) or 0)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Referral]:
        stmt = (
            select(Referral)
            .options(selectinload(Referral.referrer), selectinload(Referral.referred), selectinload(Referral.reward))
            .order_by(Referral.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return result.all()


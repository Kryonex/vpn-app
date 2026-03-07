from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.enums import PaymentStatus
from app.models.payment import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, payment: Payment) -> Payment:
        self.session.add(payment)
        await self.session.flush()
        return payment

    async def get_by_external_id(self, external_payment_id: str) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.external_payment_id == external_payment_id)
            .options(selectinload(Payment.plan), selectinload(Payment.user), selectinload(Payment.vpn_key))
        )
        return await self.session.scalar(stmt)

    async def get_by_id_for_update(self, payment_id: UUID) -> Payment | None:
        stmt = (
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
            .options(selectinload(Payment.plan), selectinload(Payment.user), selectinload(Payment.vpn_key))
        )
        return await self.session.scalar(stmt)

    async def list_by_user(self, user_id: UUID) -> list[Payment]:
        stmt = (
            select(Payment)
            .where(Payment.user_id == user_id)
            .options(selectinload(Payment.plan), selectinload(Payment.vpn_key))
            .order_by(desc(Payment.created_at))
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        stmt = (
            select(Payment)
            .options(selectinload(Payment.plan), selectinload(Payment.user), selectinload(Payment.vpn_key))
            .order_by(desc(Payment.created_at))
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def count_succeeded_by_user(self, user_id: UUID) -> int:
        stmt = select(func.count(Payment.id)).where(Payment.user_id == user_id, Payment.status == PaymentStatus.SUCCEEDED)
        return int((await self.session.scalar(stmt)) or 0)


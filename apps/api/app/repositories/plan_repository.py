from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.plan import Plan


class PlanRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_active_plans(self) -> list[Plan]:
        stmt = select(Plan).where(Plan.is_active.is_(True)).order_by(Plan.sort_order.asc(), Plan.duration_days.asc())
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_all(self) -> list[Plan]:
        stmt = select(Plan).order_by(Plan.sort_order.asc(), Plan.duration_days.asc())
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_by_id(self, plan_id: UUID) -> Plan | None:
        return await self.session.scalar(select(Plan).where(Plan.id == plan_id))

    async def create(
        self,
        *,
        name: str,
        duration_days: int,
        price: Decimal,
        currency: str,
        is_active: bool,
        sort_order: int,
    ) -> Plan:
        plan = Plan(
            name=name,
            duration_days=duration_days,
            price=price,
            currency=currency.upper(),
            is_active=is_active,
            sort_order=sort_order,
        )
        self.session.add(plan)
        await self.session.flush()
        return plan


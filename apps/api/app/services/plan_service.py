from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.plan_repository import PlanRepository


class PlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.plan_repo = PlanRepository(session)

    async def list_active(self):
        return await self.plan_repo.get_active_plans()

    async def get_by_id(self, plan_id: UUID):
        return await self.plan_repo.get_by_id(plan_id)


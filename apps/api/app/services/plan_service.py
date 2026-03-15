from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.plan_repository import PlanRepository
from app.services.access_policy_service import AccessPolicyService


class PlanService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.plan_repo = PlanRepository(session)
        self.access_policy = AccessPolicyService(session)

    async def list_active(self):
        plans = await self.plan_repo.get_active_plans()
        for plan in plans:
            setattr(plan, 'inbound_ids', await self.access_policy.get_plan_inbound_ids(plan.id))
        return plans

    async def get_by_id(self, plan_id: UUID):
        return await self.plan_repo.get_by_id(plan_id)


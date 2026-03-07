from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.schemas.plan import PlanOut
from app.services.plan_service import PlanService

router = APIRouter(tags=['plans'])


@router.get('/plans', response_model=list[PlanOut])
async def list_plans(session: AsyncSession = Depends(get_session)) -> list[PlanOut]:
    service = PlanService(session)
    return await service.list_active()

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.system import SystemStatusOut
from app.services.system_service import SystemStatusService

router = APIRouter(prefix='/system', tags=['system'])


@router.get('/status', response_model=SystemStatusOut)
async def get_system_status(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SystemStatusOut:
    state = await SystemStatusService(session).get_status()
    return SystemStatusOut(**state.__dict__)

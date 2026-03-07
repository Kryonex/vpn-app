from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.support import SupportContactOut
from app.services.support_service import SupportService

router = APIRouter(prefix='/support', tags=['support'])


@router.get('', response_model=SupportContactOut)
async def get_support_contact(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SupportContactOut:
    service = SupportService(session)
    return await service.get_support_contact()

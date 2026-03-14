from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.system import SystemNewsListOut, SystemStatusOut, UserTelegramProxyOut
from app.services.system_service import SystemStatusService

router = APIRouter(prefix='/system', tags=['system'])


@router.get('/status', response_model=SystemStatusOut)
async def get_system_status(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SystemStatusOut:
    state = await SystemStatusService(session).get_status()
    return SystemStatusOut(**asdict(state))


@router.get('/telegram-proxy', response_model=UserTelegramProxyOut)
async def get_user_telegram_proxy(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> UserTelegramProxyOut:
    data = await SystemStatusService(session).get_user_telegram_proxy(current_user)
    return UserTelegramProxyOut(**data)


@router.get('/news', response_model=SystemNewsListOut)
async def get_system_news(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SystemNewsListOut:
    items = await SystemStatusService(session).get_news()
    return SystemNewsListOut(items=items)

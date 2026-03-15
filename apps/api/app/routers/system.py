from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.schemas.system import (
    FreeTrialActivateResponse,
    FreeTrialStatusOut,
    SystemNewsListOut,
    SystemStatusOut,
    UserTelegramProxyOut,
)
from app.services.auth_service import AuthService
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


@router.get('/free-trial', response_model=FreeTrialStatusOut)
async def get_free_trial_status(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FreeTrialStatusOut:
    data = await AuthService(session).get_free_trial_status(current_user)
    return FreeTrialStatusOut(**data)


@router.post('/free-trial/activate', response_model=FreeTrialActivateResponse)
async def activate_free_trial(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FreeTrialActivateResponse:
    try:
        data = await AuthService(session).activate_free_trial(current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return FreeTrialActivateResponse(**data)

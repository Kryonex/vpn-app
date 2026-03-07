from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import rate_limit
from app.core.security import TelegramAuthError
from app.db.session import get_session
from app.schemas.auth import AuthResponse, TelegramAuthRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix='/auth', tags=['auth'])


@router.post('/telegram', response_model=AuthResponse, dependencies=[Depends(rate_limit)])
async def auth_telegram(payload: TelegramAuthRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    settings = get_settings()
    if not settings.bot_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='BOT_TOKEN not configured')

    service = AuthService(session)
    try:
        _, token = await service.authenticate_telegram(payload.init_data, settings.bot_token)
    except TelegramAuthError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc

    return AuthResponse(access_token=token)

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import rate_limit
from app.core.security import TelegramAuthError
from app.db.session import get_session
from app.schemas.auth import AuthResponse, TelegramAuthRequest
from app.services.auth_service import AuthService

router = APIRouter(prefix='/auth', tags=['auth'])
logger = logging.getLogger(__name__)


@router.post('/telegram', response_model=AuthResponse, dependencies=[Depends(rate_limit)])
async def auth_telegram(payload: TelegramAuthRequest, session: AsyncSession = Depends(get_session)) -> AuthResponse:
    settings = get_settings()
    init_data_present = bool(payload.init_data)
    logger.info('Auth /auth/telegram request received | init_data_present=%s', init_data_present)

    if not settings.bot_token:
        logger.error('Auth /auth/telegram failed: BOT_TOKEN not configured')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='BOT_TOKEN not configured')

    service = AuthService(session)
    try:
        _, token = await service.authenticate_telegram(payload.init_data, settings.bot_token)
        logger.info('Auth /auth/telegram validation passed and token issued')
    except TelegramAuthError as exc:
        logger.warning('Auth /auth/telegram validation failed: %s', str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception('Auth /auth/telegram unexpected failure: %s', type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Internal auth error') from exc

    return AuthResponse(access_token=token)

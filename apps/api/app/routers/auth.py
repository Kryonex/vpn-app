from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import rate_limit
from app.core.security import TelegramAuthError, create_access_token
from app.db.session import get_session
from app.schemas.auth import (
    AuthResponse,
    PublicAuthConfigResponse,
    TelegramAuthRequest,
    TelegramWebsiteAuthRequest,
    WebAccessLoginRequest,
)
from app.services.auth_service import AuthService
from app.services.web_access_service import WebAccessService

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


@router.post('/telegram-website', response_model=AuthResponse, dependencies=[Depends(rate_limit)])
async def auth_telegram_website(
    payload: TelegramWebsiteAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    settings = get_settings()
    logger.info('Auth /auth/telegram-website request received')

    if not settings.bot_token:
        logger.error('Auth /auth/telegram-website failed: BOT_TOKEN not configured')
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='BOT_TOKEN not configured')

    service = AuthService(session)
    try:
        _, token = await service.authenticate_telegram_website(payload.model_dump(), settings.bot_token)
        logger.info('Auth /auth/telegram-website validation passed and token issued')
    except TelegramAuthError as exc:
        logger.warning('Auth /auth/telegram-website validation failed: %s', str(exc))
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception('Auth /auth/telegram-website unexpected failure: %s', type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Internal auth error') from exc

    return AuthResponse(access_token=token)


@router.post('/web-login', response_model=AuthResponse, dependencies=[Depends(rate_limit)])
async def auth_web_login(
    payload: WebAccessLoginRequest,
    session: AsyncSession = Depends(get_session),
) -> AuthResponse:
    logger.info('Auth /auth/web-login request received | login_id_present=%s', bool(payload.login_id))
    try:
        service = WebAccessService(session)
        user = await service.authenticate(payload.login_id, payload.password)
        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Неверный ID входа или пароль.')
        token = create_access_token(str(user.id))
        logger.info('Auth /auth/web-login validation passed and token issued')
        return AuthResponse(access_token=token)
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception('Auth /auth/web-login unexpected failure: %s', type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail='Internal auth error') from exc


@router.get('/public-config', response_model=PublicAuthConfigResponse)
async def public_auth_config() -> PublicAuthConfigResponse:
    settings = get_settings()
    enabled = bool(settings.bot_token and settings.bot_username)
    return PublicAuthConfigResponse(
        enabled=enabled,
        bot_username=settings.bot_username or None,
        mini_app_url=settings.mini_app_url or None,
    )


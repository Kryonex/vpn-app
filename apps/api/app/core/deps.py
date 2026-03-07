from __future__ import annotations

import logging
from datetime import timezone, datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.redis import redis_dependency
from app.core.security import decode_access_token
from app.db.session import get_session
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    session: Annotated[AsyncSession, Depends(get_session)],
) -> User:
    if not credentials:
        logger.warning('Auth bearer missing')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Missing auth token')

    payload = decode_access_token(credentials.credentials)
    subject = payload.get('sub')
    if not subject:
        logger.warning('Auth token decoded but sub missing')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token payload')

    user_id = UUID(subject)
    user = await session.scalar(
        select(User).where(User.id == user_id).options(selectinload(User.telegram_account))
    )
    if not user:
        logger.warning('Auth user not found for token subject')
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='User not found')
    logger.info('Auth user resolved')
    return user


async def require_admin(credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)]) -> None:
    settings = get_settings()
    if not credentials or credentials.credentials != settings.admin_bearer_token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid admin token')


async def rate_limit(
    request: Request,
    redis: Annotated[Redis, Depends(redis_dependency)],
) -> None:
    settings = get_settings()

    client_ip = request.client.host if request.client else 'unknown'
    key = f'rl:{request.url.path}:{client_ip}'
    current = await redis.incr(key)
    if current == 1:
        await redis.expire(key, settings.rate_limit_window_seconds)

    if current > settings.rate_limit_requests:
        ttl = await redis.ttl(key)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f'Rate limit exceeded. Retry in {max(ttl, 1)}s',
        )


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


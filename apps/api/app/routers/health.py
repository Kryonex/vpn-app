from __future__ import annotations

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redis import redis_dependency
from app.db.session import get_session

router = APIRouter(prefix='/health', tags=['health'])


@router.get('/live')
async def health_live() -> dict[str, str]:
    return {'status': 'ok'}


@router.get('/ready')
async def health_ready(
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
) -> dict[str, str]:
    await session.execute(text('SELECT 1'))
    await redis.ping()
    return {'status': 'ready'}

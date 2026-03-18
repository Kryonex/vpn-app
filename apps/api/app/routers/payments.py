from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.deps import get_current_user
from app.core.factories import threexui_dependency
from app.core.redis import redis_dependency
from app.db.session import get_session
from app.integrations.threexui.service import ThreeXUIService
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentOut
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService

router = APIRouter(prefix='/payments', tags=['payments'])


@router.get('', response_model=list[PaymentOut])
async def list_payments(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    repo = PaymentRepository(session)
    return await repo.list_by_user(current_user.id)


@router.post('/{payment_id}/refresh', response_model=PaymentOut)
async def refresh_payment(
    payment_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = PaymentService(
        session=session,
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    return await service.refresh_payment_for_user(payment_id, current_user.id)


@router.post('/platega/webhook')
async def platega_webhook(
    payload: dict = Body(default={}),
    x_merchant_id: str | None = Header(default=None, alias='X-MerchantId'),
    x_secret: str | None = Header(default=None, alias='X-Secret'),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    settings = get_settings()
    if settings.platega_merchant_id and x_merchant_id and x_merchant_id != settings.platega_merchant_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid merchant header')
    if settings.platega_secret and x_secret and x_secret != settings.platega_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid secret header')

    service = PaymentService(
        session=session,
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    processed = await service.process_platega_webhook(payload)
    return {'ok': True, 'processed': processed}


@router.post('/yookassa/webhook')
async def yookassa_webhook_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail='YooKassa integration is disabled. Use Platega or manual admin payment flow.',
    )

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.factories import get_yookassa_provider, threexui_dependency
from app.core.redis import redis_dependency
from app.db.session import get_session
from app.integrations.threexui.service import ThreeXUIService
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentOut, YooKassaWebhookResponse
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService

router = APIRouter(prefix='/payments', tags=['payments'])


@router.get('', response_model=list[PaymentOut])
async def list_payments(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    repo = PaymentRepository(session)
    return await repo.list_by_user(current_user.id)


@router.post('/yookassa/webhook', response_model=YooKassaWebhookResponse)
async def yookassa_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> YooKassaWebhookResponse:
    payload = await request.json()
    service = PaymentService(
        session=session,
        provider=get_yookassa_provider(),
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    await service.process_yookassa_webhook(payload)
    return YooKassaWebhookResponse(ok=True)

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.core.redis import redis_dependency
from app.db.session import get_session
from app.models.user import User
from app.schemas.support import SupportContactOut, SupportTicketCreateRequest, SupportTicketCreateResponse
from app.services.notification_service import NotificationService
from app.services.support_service import SupportService

router = APIRouter(prefix='/support', tags=['support'])


@router.get('', response_model=SupportContactOut)
async def get_support_contact(
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> SupportContactOut:
    service = SupportService(session)
    return await service.get_support_contact()


@router.post('/tickets', response_model=SupportTicketCreateResponse)
async def create_support_ticket(
    payload: SupportTicketCreateRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
) -> SupportTicketCreateResponse:
    service = SupportService(session)
    notification_service = NotificationService(redis)
    try:
        return await service.create_public_ticket(
            payload,
            enqueue_notification=notification_service.enqueue_telegram_notification,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

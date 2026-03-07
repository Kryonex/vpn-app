from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_session
from app.models.user import User
from app.repositories.payment_repository import PaymentRepository
from app.schemas.payment import PaymentOut

router = APIRouter(prefix='/payments', tags=['payments'])


@router.get('', response_model=list[PaymentOut])
async def list_payments(current_user: User = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    repo = PaymentRepository(session)
    return await repo.list_by_user(current_user.id)


@router.post('/yookassa/webhook')
async def yookassa_webhook_disabled():
    raise HTTPException(
        status_code=status.HTTP_410_GONE,
        detail='YooKassa integration is disabled. Use manual payment flow.',
    )

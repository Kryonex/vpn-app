from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user, rate_limit
from app.core.factories import get_yookassa_provider, threexui_dependency
from app.core.redis import redis_dependency
from app.db.session import get_session
from app.integrations.threexui.service import ThreeXUIService
from app.models.user import User
from app.schemas.key import PurchaseRequest, RenewRequest, RotateResponse, VPNKeyOut
from app.schemas.payment import PaymentIntentOut
from app.services.key_service import KeyService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService

router = APIRouter(prefix='/keys', tags=['keys'])


@router.get('', response_model=list[VPNKeyOut])
async def list_keys(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> list[VPNKeyOut]:
    service = KeyService(session, threexui_service)
    return await service.list_user_keys(current_user.id)


@router.get('/{key_id}', response_model=VPNKeyOut)
async def get_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> VPNKeyOut:
    service = KeyService(session, threexui_service)
    return await service.get_user_key(current_user.id, key_id)


@router.post('/purchase', response_model=PaymentIntentOut, dependencies=[Depends(rate_limit)])
async def purchase_key(
    payload: PurchaseRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> PaymentIntentOut:
    service = PaymentService(
        session=session,
        provider=get_yookassa_provider(),
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    payment = await service.create_purchase_intent(
        user=current_user,
        plan_id=payload.plan_id,
        key_name=payload.key_name,
        apply_bonus_days=payload.apply_bonus_days,
    )
    return PaymentIntentOut(
        payment_id=payment.id,
        provider=payment.provider,
        status=payment.status,
        confirmation_url=payment.confirmation_url,
    )


@router.post('/{key_id}/renew', response_model=PaymentIntentOut, dependencies=[Depends(rate_limit)])
async def renew_key(
    key_id: UUID,
    payload: RenewRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> PaymentIntentOut:
    service = PaymentService(
        session=session,
        provider=get_yookassa_provider(),
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    payment = await service.create_renew_intent(
        user=current_user,
        key_id=key_id,
        plan_id=payload.plan_id,
        apply_bonus_days=payload.apply_bonus_days,
    )
    return PaymentIntentOut(
        payment_id=payment.id,
        provider=payment.provider,
        status=payment.status,
        confirmation_url=payment.confirmation_url,
    )


@router.post('/{key_id}/rotate', response_model=RotateResponse, dependencies=[Depends(rate_limit)])
async def rotate_key(
    key_id: UUID,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
) -> RotateResponse:
    service = KeyService(session, threexui_service)
    version = await service.rotate_key(current_user.id, key_id)
    return RotateResponse(key_id=version.vpn_key_id, new_version=version.version, connection_uri=version.connection_uri)

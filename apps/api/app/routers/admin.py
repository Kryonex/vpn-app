from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.factories import threexui_dependency
from app.db.session import get_session
from app.integrations.threexui.service import ThreeXUIService
from app.schemas.admin import (
    AdminBonusDaysRequest,
    AdminGrantSubscriptionRequest,
    AdminKeyOut,
    AdminPaymentsListResponse,
    AdminReferralStatOut,
    AdminRevokeKeyRequest,
    AdminSubscriptionOut,
    AdminUserOut,
)
from app.services.admin_service import AdminService

router = APIRouter(prefix='/admin', tags=['admin'], dependencies=[Depends(require_admin)])


@router.get('/users', response_model=list[AdminUserOut])
async def admin_list_users(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.list_users(limit=limit, offset=offset)


@router.get('/payments', response_model=AdminPaymentsListResponse)
async def admin_list_payments(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    items = await service.list_payments(limit=limit, offset=offset)
    return AdminPaymentsListResponse(items=items)


@router.get('/keys', response_model=list[AdminKeyOut])
async def admin_list_keys(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.list_keys(limit=limit, offset=offset)


@router.get('/referrals', response_model=list[AdminReferralStatOut])
async def admin_list_referrals(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.list_referrals(limit=limit, offset=offset)


@router.get('/subscriptions', response_model=list[AdminSubscriptionOut])
async def admin_list_subscriptions(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.list_subscriptions(limit=limit, offset=offset)


@router.post('/keys/{key_id}/revoke', response_model=AdminKeyOut)
async def admin_revoke_key(
    key_id: UUID,
    payload: AdminRevokeKeyRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.revoke_key(key_id=key_id, reason=payload.reason)


@router.post('/users/{user_id}/bonus-days')
async def admin_add_bonus_days(
    user_id: UUID,
    payload: AdminBonusDaysRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    await service.add_bonus_days(user_id=user_id, days=payload.days, reason=payload.reason)
    return {'ok': True}


@router.post('/users/{user_id}/grant-subscription', response_model=AdminKeyOut)
async def admin_grant_subscription(
    user_id: UUID,
    payload: AdminGrantSubscriptionRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.grant_subscription(
        user_id=user_id,
        plan_id=payload.plan_id,
        key_id=payload.key_id,
        key_name=payload.key_name,
    )

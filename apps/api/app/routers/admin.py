from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, Query
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import require_admin
from app.core.factories import threexui_dependency
from app.core.redis import redis_dependency
from app.db.session import get_session
from app.integrations.threexui.service import ThreeXUIService
from app.schemas.admin import (
    AdminBonusDaysRequest,
    AdminBindPanelKeyRequest,
    AdminBindPanelKeyResponse,
    AdminGrantSubscriptionRequest,
    AdminKeyOut,
    AdminPaymentDecisionRequest,
    AdminPaymentsListResponse,
    AdminPlanCreateRequest,
    AdminResetKeysEarningsRequest,
    AdminReferralSettingsOut,
    AdminReferralSettingsUpdateRequest,
    AdminPlanUpdateRequest,
    AdminPlansListResponse,
    AdminReferralStatOut,
    AdminRevokeKeyRequest,
    AdminStatsOut,
    AdminSubscriptionOut,
    AdminUserOut,
)
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService

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


@router.post('/payments/{payment_id}/approve')
async def admin_approve_payment(
    payment_id: UUID,
    _: AdminPaymentDecisionRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    payment_service = PaymentService(
        session=session,
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    payment = await payment_service.mark_manual_payment_succeeded(payment_id)
    return {'ok': True, 'payment_id': str(payment.id), 'status': payment.status.value}


@router.post('/payments/{payment_id}/reject')
async def admin_reject_payment(
    payment_id: UUID,
    _: AdminPaymentDecisionRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    payment_service = PaymentService(
        session=session,
        threexui_service=threexui_service,
        notification_service=NotificationService(redis),
    )
    payment = await payment_service.mark_manual_payment_failed(payment_id)
    return {'ok': True, 'payment_id': str(payment.id), 'status': payment.status.value}


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


@router.get('/plans', response_model=AdminPlansListResponse)
async def admin_list_plans(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    items = await service.list_plans()
    return AdminPlansListResponse(items=items)


@router.get('/stats', response_model=AdminStatsOut)
async def admin_stats(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    stats = await service.get_stats()
    return AdminStatsOut(**stats)


@router.get('/settings/referral', response_model=AdminReferralSettingsOut)
async def admin_get_referral_settings(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    days = await service.get_referral_bonus_days()
    return AdminReferralSettingsOut(referral_bonus_days=days)


@router.patch('/settings/referral', response_model=AdminReferralSettingsOut)
async def admin_patch_referral_settings(
    payload: AdminReferralSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    days = await service.set_referral_bonus_days(payload.referral_bonus_days)
    return AdminReferralSettingsOut(referral_bonus_days=days)


@router.post('/system/reset-keys-and-earnings')
async def admin_reset_keys_and_earnings(
    payload: AdminResetKeysEarningsRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    stats = await service.reset_keys_and_earnings(payload.confirm_text)
    return {'ok': True, **stats}


@router.post('/keys/bind-by-username', response_model=AdminBindPanelKeyResponse)
async def admin_bind_panel_key_by_username(
    payload: AdminBindPanelKeyRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    version, owner_id = await service.bind_panel_key_to_username(
        username=payload.username,
        display_name=payload.display_name,
        client_uuid=payload.client_uuid,
        inbound_id=payload.inbound_id,
    )
    return AdminBindPanelKeyResponse(
        key_id=version.vpn_key_id,
        version_id=version.id,
        owner_id=owner_id,
        connection_uri=version.connection_uri,
    )


@router.post('/plans')
async def admin_create_plan(
    payload: AdminPlanCreateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    plan = await service.create_plan(
        name=payload.name,
        duration_days=payload.duration_days,
        price=payload.price,
        currency=payload.currency,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return {'ok': True, 'plan_id': str(plan.id)}


@router.patch('/plans/{plan_id}')
async def admin_update_plan(
    plan_id: UUID,
    payload: AdminPlanUpdateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    plan = await service.update_plan(
        plan_id=plan_id,
        name=payload.name,
        duration_days=payload.duration_days,
        price=payload.price,
        currency=payload.currency,
        is_active=payload.is_active,
        sort_order=payload.sort_order,
    )
    return {'ok': True, 'plan_id': str(plan.id)}


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

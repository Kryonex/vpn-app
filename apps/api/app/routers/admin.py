from __future__ import annotations

from dataclasses import asdict

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
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
    AdminDeleteKeyRequest,
    AdminDeletePlanResponse,
    AdminResetFreeTrialResponse,
    AdminDeleteUserRequest,
    AdminDeleteUserResponse,
    AdminGrantSubscriptionRequest,
    AdminClearPaymentsResponse,
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
    AdminUserLookupOut,
    AdminStatsOut,
    AdminSubscriptionOut,
    AdminUserOut,
)
from app.schemas.system import (
    AdminInboundOut,
    AdminMessageSendRequest,
    AdminMessageSendResponse,
    AdminSystemStatusUpdateRequest,
    FreeTrialSettingsOut,
    FreeTrialSettingsUpdateRequest,
    NotificationQueueClearResponse,
    NotificationQueueStatusOut,
    PaymentSettingsOut,
    PaymentSettingsUpdateRequest,
    PurchaseInboundSettingsOut,
    PurchaseInboundSettingsUpdateRequest,
    SystemStatusOut,
    TelegramProxySettingsOut,
    TelegramProxySettingsUpdateRequest,
)
from app.services.admin_service import AdminService
from app.services.notification_service import NotificationService
from app.services.payment_service import PaymentService
from app.services.system_service import SystemStatusService

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


@router.get('/users/lookup', response_model=AdminUserLookupOut)
async def admin_lookup_user_by_username(
    username: str = Query(min_length=1, max_length=64),
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    user = await service.lookup_user_by_username(username)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
    return AdminUserLookupOut(**user)


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


@router.post('/payments/clear-history', response_model=AdminClearPaymentsResponse)
async def admin_clear_payment_history(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    deleted_count = await service.clear_completed_payments()
    return AdminClearPaymentsResponse(ok=True, deleted_count=deleted_count)


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
    stats = await service.reset_keys_and_earnings(payload.confirm_text, payload.mode)
    return {'ok': True, **stats}


@router.post('/system/sync-panel')
async def admin_sync_panel(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    stats = await service.sync_keys_with_panel()
    return {'ok': True, **stats}


@router.get('/system/status', response_model=SystemStatusOut)
async def admin_get_system_status(
    session: AsyncSession = Depends(get_session),
):
    state = await SystemStatusService(session).get_status()
    return SystemStatusOut(**asdict(state))


@router.patch('/system/status', response_model=SystemStatusOut)
async def admin_update_system_status(
    payload: AdminSystemStatusUpdateRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
):
    system_service = SystemStatusService(session)
    state = await system_service.set_status(
        status_value=payload.status,
        message=payload.message,
        maintenance_mode=payload.maintenance_mode,
        show_to_all=payload.show_to_all,
        scheduled_for=payload.scheduled_for,
    )
    if payload.send_notification_to_all and payload.message:
        notifier = NotificationService(redis)
        await system_service.send_admin_message(
            actor_id='system_status',
            message=payload.message,
            send_to_all=True,
            force=False,
            enqueue_fn=notifier.enqueue_telegram_notification,
        )
    await session.commit()
    return SystemStatusOut(**asdict(state))


@router.post('/messages/send', response_model=AdminMessageSendResponse)
async def admin_send_message(
    payload: AdminMessageSendRequest,
    session: AsyncSession = Depends(get_session),
    redis: Redis = Depends(redis_dependency),
):
    notifier = NotificationService(redis)
    system_service = SystemStatusService(session)
    target_count = 0
    duplicate_blocked = False
    audit_log_id: str | None = None
    if payload.send_to_all or payload.user_id:
        target_count, duplicate_blocked, audit_log_id = await system_service.send_admin_message(
            actor_id='admin',
            message=payload.message,
            send_to_all=payload.send_to_all,
            force=payload.force,
            user_id=payload.user_id,
            image_data_url=payload.image_data_url,
            image_filename=payload.image_filename,
            enqueue_fn=notifier.enqueue_telegram_notification,
        )
    if payload.publish_as_news:
        await system_service.publish_news(
            title=payload.news_title,
            body=payload.message,
            image_data_url=payload.image_data_url,
        )
    if not payload.publish_as_news and not payload.send_to_all and not payload.user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Target user is required')
    await session.commit()
    return AdminMessageSendResponse(
        ok=True,
        target_count=target_count,
        duplicate_blocked=duplicate_blocked,
        audit_log_id=audit_log_id,
    )


@router.get('/system/notification-queue', response_model=NotificationQueueStatusOut)
async def admin_get_notification_queue(
    redis: Redis = Depends(redis_dependency),
):
    notifier = NotificationService(redis)
    return NotificationQueueStatusOut(
        queue_key=notifier.settings.notification_queue_key,
        pending_count=await notifier.get_queue_size(),
    )


@router.post('/system/notification-queue/clear', response_model=NotificationQueueClearResponse)
async def admin_clear_notification_queue(
    redis: Redis = Depends(redis_dependency),
):
    notifier = NotificationService(redis)
    cleared_count = await notifier.clear_queue()
    return NotificationQueueClearResponse(ok=True, cleared_count=cleared_count)


@router.get('/system/payments', response_model=PaymentSettingsOut)
async def admin_get_payment_settings(
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return PaymentSettingsOut(**await SystemStatusService(session).get_payment_settings())


@router.patch('/system/payments', response_model=PaymentSettingsOut)
async def admin_update_payment_settings(
    payload: PaymentSettingsUpdateRequest,
    response: Response,
    session: AsyncSession = Depends(get_session),
):
    data = await SystemStatusService(session).set_payment_settings(enabled=payload.enabled)
    await session.commit()
    response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    return PaymentSettingsOut(**data)


@router.get('/system/telegram-proxy', response_model=TelegramProxySettingsOut)
async def admin_get_telegram_proxy_settings(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return TelegramProxySettingsOut(**await service.get_telegram_proxy_settings())


@router.patch('/system/telegram-proxy', response_model=TelegramProxySettingsOut)
async def admin_update_telegram_proxy_settings(
    payload: TelegramProxySettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return TelegramProxySettingsOut(
        **await service.set_telegram_proxy_settings(
            proxy_url=payload.proxy_url,
            button_text=payload.button_text,
            proxies=[item.model_dump() for item in payload.proxies],
        )
    )


@router.delete('/system/news/{news_id}')
async def admin_delete_news(
    news_id: str,
    session: AsyncSession = Depends(get_session),
):
    deleted = await SystemStatusService(session).delete_news(news_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='News not found')
    await session.commit()
    return {'ok': True, 'news_id': news_id}


@router.get('/system/inbounds', response_model=list[AdminInboundOut])
async def admin_list_inbounds(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return [AdminInboundOut(**item) for item in await service.list_available_inbounds()]


@router.get('/system/purchase-inbounds', response_model=PurchaseInboundSettingsOut)
async def admin_get_purchase_inbounds(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return PurchaseInboundSettingsOut(**await service.get_purchase_inbound_settings())


@router.patch('/system/purchase-inbounds', response_model=PurchaseInboundSettingsOut)
async def admin_patch_purchase_inbounds(
    payload: PurchaseInboundSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return PurchaseInboundSettingsOut(**await service.set_purchase_inbound_settings(payload.inbound_ids))


@router.post('/system/purchase-inbounds/resync')
async def admin_resync_purchase_inbounds(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.resync_purchase_inbound_settings()


@router.get('/system/free-trial', response_model=FreeTrialSettingsOut)
async def admin_get_free_trial_settings(
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return FreeTrialSettingsOut(**await service.get_free_trial_settings())


@router.patch('/system/free-trial', response_model=FreeTrialSettingsOut)
async def admin_patch_free_trial_settings(
    payload: FreeTrialSettingsUpdateRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return FreeTrialSettingsOut(
        **await service.set_free_trial_settings(
            enabled=payload.enabled,
            days=payload.days,
            inbound_ids=payload.inbound_ids,
        )
    )


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
        inbound_ids=payload.inbound_ids,
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
        inbound_ids=payload.inbound_ids,
    )
    return {'ok': True, 'plan_id': str(plan.id)}


@router.delete('/plans/{plan_id}', response_model=AdminDeletePlanResponse)
async def admin_delete_plan(
    plan_id: UUID,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    result = await service.delete_plan(plan_id)
    return AdminDeletePlanResponse(**result)


@router.post('/keys/{key_id}/revoke', response_model=AdminKeyOut)
async def admin_revoke_key(
    key_id: UUID,
    payload: AdminRevokeKeyRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.revoke_key(key_id=key_id, reason=payload.reason)


@router.delete('/keys/{key_id}')
async def admin_delete_key(
    key_id: UUID,
    payload: AdminDeleteKeyRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    return await service.delete_key_from_history(key_id=key_id, reason=payload.reason)


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


@router.delete('/users/{user_id}', response_model=AdminDeleteUserResponse)
async def admin_delete_user(
    user_id: UUID,
    payload: AdminDeleteUserRequest,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    result = await service.delete_user_with_related_data(user_id=user_id, reason=payload.reason)
    return AdminDeleteUserResponse(**result)


@router.post('/users/{user_id}/reset-free-trial', response_model=AdminResetFreeTrialResponse)
async def admin_reset_free_trial(
    user_id: UUID,
    session: AsyncSession = Depends(get_session),
    threexui_service: ThreeXUIService = Depends(threexui_dependency),
):
    service = AdminService(session, threexui_service)
    result = await service.reset_user_free_trial(user_id)
    return AdminResetFreeTrialResponse(**result)

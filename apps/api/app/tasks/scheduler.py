from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.core.redis import get_redis
from app.db.session import SessionLocal
from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import SubscriptionStatus, VPNKeyStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.services.notification_service import NotificationService

logger = logging.getLogger(__name__)


async def run_scheduler(stop_event: asyncio.Event) -> None:
    settings = get_settings()
    redis = await get_redis()
    notifier = NotificationService(redis)

    while not stop_event.is_set():
        try:
            lock_key = 'scheduler:subscriptions:lock'
            got_lock = await redis.set(lock_key, '1', nx=True, ex=max(settings.scheduler_interval_seconds - 1, 5))
            if got_lock:
                await _process_subscriptions(notifier)
                await _sync_panel_clients()
        except Exception as exc:  # noqa: BLE001
            logger.exception('Scheduler loop error: %s', exc)

        try:
            await asyncio.wait_for(stop_event.wait(), timeout=settings.scheduler_interval_seconds)
        except asyncio.TimeoutError:
            pass


async def _process_subscriptions(notifier: NotificationService) -> None:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    expiring_until = now + timedelta(days=settings.expiring_notify_days)

    async with SessionLocal() as session:
        expiring_stmt = (
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at > now,
                Subscription.expires_at <= expiring_until,
                Subscription.notified_expiring_at.is_(None),
            )
            .options(selectinload(Subscription.vpn_key).selectinload(VPNKey.owner).selectinload(User.telegram_account))
        )
        expiring_items = (await session.scalars(expiring_stmt)).all()

        for sub in expiring_items:
            owner = sub.vpn_key.owner
            if owner.telegram_account:
                await notifier.enqueue_telegram_notification(
                    telegram_user_id=owner.telegram_account.telegram_user_id,
                    text=f'Подписка для ключа "{sub.vpn_key.display_name}" истекает {sub.expires_at.date().isoformat()}.',
                )
            sub.notified_expiring_at = now

        expired_stmt = (
            select(Subscription)
            .where(
                Subscription.status == SubscriptionStatus.ACTIVE,
                Subscription.expires_at <= now,
            )
            .options(selectinload(Subscription.vpn_key).selectinload(VPNKey.owner).selectinload(User.telegram_account))
        )
        expired_items = (await session.scalars(expired_stmt)).all()

        for sub in expired_items:
            sub.status = SubscriptionStatus.EXPIRED
            if sub.vpn_key.current_subscription_id == sub.id:
                sub.vpn_key.status = VPNKeyStatus.EXPIRED

            if sub.notified_expired_at is None and sub.vpn_key.owner.telegram_account:
                await notifier.enqueue_telegram_notification(
                    telegram_user_id=sub.vpn_key.owner.telegram_account.telegram_user_id,
                    text=f'Подписка для ключа "{sub.vpn_key.display_name}" истекла.',
                )
                sub.notified_expired_at = now

        await session.commit()


async def _sync_panel_clients() -> None:
    async with SessionLocal() as session:
        threexui = ThreeXUIService()
        try:
            stmt = (
                select(VPNKey)
                .where(VPNKey.status.in_([VPNKeyStatus.ACTIVE, VPNKeyStatus.PENDING_PAYMENT]))
                .options(
                    selectinload(VPNKey.current_subscription),
                    selectinload(VPNKey.versions),
                )
            )
            keys = (await session.scalars(stmt)).all()

            changed_count = 0
            for key in keys:
                if await threexui.sync_key_with_panel_state(key):
                    changed_count += 1

            if changed_count:
                await session.commit()
                logger.info('Scheduler panel sync: updated keys=%s', changed_count)
        finally:
            await threexui.client.close()

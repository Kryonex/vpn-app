from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal
import hashlib
import logging
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.threexui.service import ThreeXUIService
from app.models.bonus_day_ledger import BonusDayLedger
from app.models.enums import PaymentStatus, SubscriptionStatus, VPNKeyStatus
from app.models.payment import Payment
from app.models.payment_event import PaymentEvent
from app.models.plan import Plan
from app.models.referral import Referral
from app.models.referral_reward import ReferralReward
from app.models.subscription import Subscription
from app.models.user import User
from app.models.telegram_account import TelegramAccount
from app.models.audit_log import AuditLog
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vpn_key_repository import VPNKeyRepository
from app.repositories.app_settings_repository import AppSettingsRepository
from app.services.referral_service import ReferralService

logger = logging.getLogger(__name__)


class AdminService:
    def __init__(self, session: AsyncSession, threexui_service: ThreeXUIService) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.plan_repo = PlanRepository(session)
        self.key_repo = VPNKeyRepository(session)
        self.referral_repo = ReferralRepository(session)
        self.referral_service = ReferralService(session)
        self.threexui_service = threexui_service
        self.app_settings_repo = AppSettingsRepository(session)

    async def list_users(self, limit: int = 100, offset: int = 0):
        users = await self.user_repo.list_users(limit=limit, offset=offset)
        items: list[dict[str, object]] = []
        for user in users:
            account = user.telegram_account
            items.append(
                {
                    'id': user.id,
                    'referral_code': user.referral_code,
                    'bonus_days_balance': user.bonus_days_balance,
                    'created_at': user.created_at,
                    'telegram_username': account.username if account else None,
                    'telegram_user_id': account.telegram_user_id if account else None,
                    'total_keys_count': len(user.vpn_keys),
                }
            )
        return items

    async def list_payments(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        return await self.payment_repo.list_all(limit=limit, offset=offset)

    async def list_keys(self, limit: int = 100, offset: int = 0) -> list[VPNKey]:
        stmt = (
            select(VPNKey)
            .options(selectinload(VPNKey.owner).selectinload(User.telegram_account), selectinload(VPNKey.current_subscription))
            .order_by(VPNKey.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_referrals(self, limit: int = 100, offset: int = 0):
        return await self.referral_repo.list_all(limit=limit, offset=offset)

    async def list_subscriptions(self, limit: int = 100, offset: int = 0) -> list[Subscription]:
        stmt = select(Subscription).order_by(Subscription.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_plans(self) -> list[Plan]:
        return await self.plan_repo.list_all()

    async def get_stats(self) -> dict[str, Decimal | int]:
        total_payments = int((await self.session.scalar(select(func.count(Payment.id)))) or 0)
        succeeded_payments = int(
            (await self.session.scalar(select(func.count(Payment.id)).where(Payment.status == PaymentStatus.SUCCEEDED))) or 0
        )
        pending_payments = int(
            (
                await self.session.scalar(
                    select(func.count(Payment.id)).where(
                        Payment.status.in_([PaymentStatus.PENDING, PaymentStatus.WAITING_FOR_CAPTURE])
                    )
                )
            )
            or 0
        )
        failed_payments = int(
            (
                await self.session.scalar(
                    select(func.count(Payment.id)).where(Payment.status.in_([PaymentStatus.FAILED, PaymentStatus.CANCELED]))
                )
            )
            or 0
        )

        total_revenue = (
            await self.session.scalar(select(func.coalesce(func.sum(Payment.amount), 0)).where(Payment.status == PaymentStatus.SUCCEEDED))
        ) or Decimal('0')

        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        month_revenue = (
            await self.session.scalar(
                select(func.coalesce(func.sum(Payment.amount), 0)).where(
                    Payment.status == PaymentStatus.SUCCEEDED,
                    Payment.created_at >= month_start,
                )
            )
        ) or Decimal('0')

        return {
            'total_payments': total_payments,
            'succeeded_payments': succeeded_payments,
            'pending_payments': pending_payments,
            'failed_payments': failed_payments,
            'total_revenue': Decimal(total_revenue),
            'month_revenue': Decimal(month_revenue),
        }

    async def get_referral_bonus_days(self) -> int:
        return await self.referral_service.get_referral_bonus_days()

    async def set_referral_bonus_days(self, value: int) -> int:
        await self.app_settings_repo.set('referral_bonus_days', str(value))
        await self.session.commit()
        return value

    async def lookup_user_by_username(self, username: str) -> dict[str, object] | None:
        normalized_username = username.lstrip('@').strip().lower()
        if not normalized_username:
            return None

        user = await self.user_repo.get_by_telegram_username(normalized_username)
        if not user:
            return None

        account = user.telegram_account
        return {
            'id': user.id,
            'referral_code': user.referral_code,
            'bonus_days_balance': user.bonus_days_balance,
            'created_at': user.created_at,
            'telegram_username': account.username if account else None,
            'telegram_user_id': account.telegram_user_id if account else None,
        }

    async def sync_keys_with_panel(self) -> dict[str, int]:
        stmt = (
            select(VPNKey)
            .options(selectinload(VPNKey.versions), selectinload(VPNKey.current_subscription))
            .order_by(VPNKey.created_at.desc())
        )
        keys = (await self.session.scalars(stmt)).all()

        processed = 0
        changed = 0
        for key in keys:
            processed += 1
            if await self.threexui_service.sync_key_with_panel_state(key):
                changed += 1

        if changed:
            await self.session.commit()
        return {'processed': processed, 'changed': changed}

    async def reset_keys_and_earnings(self, confirm_text: str, mode: str = 'hard') -> dict[str, int]:
        if confirm_text.strip().upper() != 'RESET':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Invalid confirmation text')

        mode_normalized = (mode or 'hard').strip().lower()
        if mode_normalized not in {'soft', 'hard'}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Unsupported reset mode')

        if mode_normalized == 'soft':
            now = datetime.now(timezone.utc)
            keys_updated = (
                await self.session.execute(
                    update(VPNKey).values(status=VPNKeyStatus.REVOKED, current_subscription_id=None)
                )
            ).rowcount or 0
            subscriptions_updated = (
                await self.session.execute(
                    update(Subscription).values(status=SubscriptionStatus.REVOKED)
                )
            ).rowcount or 0
            versions_updated = (
                await self.session.execute(
                    update(VPNKeyVersion).values(is_active=False, revoked_at=now, connection_uri=None)
                )
            ).rowcount or 0
            payments_updated = (
                await self.session.execute(
                    update(Payment).values(status=PaymentStatus.CANCELED, amount=0, processed_at=now)
                )
            ).rowcount or 0
            payment_events_deleted = (await self.session.execute(delete(PaymentEvent))).rowcount or 0
            bonus_ledger_deleted = (await self.session.execute(delete(BonusDayLedger))).rowcount or 0
            referral_rewards_deleted = (await self.session.execute(delete(ReferralReward))).rowcount or 0
            users_updated = (await self.session.execute(update(User).values(bonus_days_balance=0))).rowcount or 0

            await self.session.commit()
            return {
                'mode': 'soft',
                'keys_revoked': int(keys_updated),
                'subscriptions_revoked': int(subscriptions_updated),
                'versions_deactivated': int(versions_updated),
                'payments_zeroed': int(payments_updated),
                'payment_events_deleted': int(payment_events_deleted),
                'bonus_ledger_deleted': int(bonus_ledger_deleted),
                'referral_rewards_deleted': int(referral_rewards_deleted),
                'users_bonus_reset': int(users_updated),
            }

        # Hard reset: wipe key/payment/referral history from DB.
        versions = (
            await self.session.scalars(
                select(VPNKeyVersion).where(VPNKeyVersion.is_active.is_(True))
            )
        ).all()

        panel_revoked = 0
        for version in versions:
            try:
                await self.threexui_service.revoke_vpn_client(version)
                panel_revoked += 1
            except Exception:  # noqa: BLE001
                logger.warning('Hard reset: failed to revoke panel client for version %s', version.id)

        keys_count_before = int((await self.session.scalar(select(func.count(VPNKey.id)))) or 0)
        subscriptions_count_before = int((await self.session.scalar(select(func.count(Subscription.id)))) or 0)
        versions_count_before = int((await self.session.scalar(select(func.count(VPNKeyVersion.id)))) or 0)

        bonus_ledger_deleted = (await self.session.execute(delete(BonusDayLedger))).rowcount or 0
        referral_rewards_deleted = (await self.session.execute(delete(ReferralReward))).rowcount or 0
        referrals_deleted = (await self.session.execute(delete(Referral))).rowcount or 0
        payment_events_deleted = (await self.session.execute(delete(PaymentEvent))).rowcount or 0
        payments_deleted = (await self.session.execute(delete(Payment))).rowcount or 0
        keys_deleted = (await self.session.execute(delete(VPNKey))).rowcount or 0
        # Safety pass in case some rows are orphaned and were not deleted via cascade.
        versions_cleanup_deleted = (await self.session.execute(delete(VPNKeyVersion))).rowcount or 0
        subscriptions_cleanup_deleted = (await self.session.execute(delete(Subscription))).rowcount or 0
        audit_logs_deleted = (await self.session.execute(delete(AuditLog))).rowcount or 0
        users_updated = (await self.session.execute(update(User).values(bonus_days_balance=0))).rowcount or 0

        await self.session.commit()
        return {
            'mode': 'hard',
            'panel_revoked': int(panel_revoked),
            'keys_deleted': int(keys_deleted),
            'subscriptions_deleted': int(subscriptions_count_before),
            'versions_deleted': int(versions_count_before),
            'subscriptions_cleanup_deleted': int(subscriptions_cleanup_deleted),
            'versions_cleanup_deleted': int(versions_cleanup_deleted),
            'keys_count_before': int(keys_count_before),
            'payments_deleted': int(payments_deleted),
            'payment_events_deleted': int(payment_events_deleted),
            'referrals_deleted': int(referrals_deleted),
            'referral_rewards_deleted': int(referral_rewards_deleted),
            'bonus_ledger_deleted': int(bonus_ledger_deleted),
            'audit_logs_deleted': int(audit_logs_deleted),
            'users_bonus_reset': int(users_updated),
        }

    @staticmethod
    def _placeholder_telegram_id_from_username(username: str) -> int:
        normalized = username.lstrip('@').strip().lower()
        digest = hashlib.sha256(normalized.encode('utf-8')).hexdigest()
        value = int(digest[:12], 16)
        return -value

    async def bind_panel_key_to_username(
        self,
        *,
        username: str,
        display_name: str | None = None,
        client_uuid: str | None = None,
        inbound_id: int | None = None,
    ) -> tuple[VPNKeyVersion, UUID]:
        normalized_username = username.lstrip('@').strip().lower()
        if not normalized_username:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Username is required')

        user = await self.user_repo.get_by_telegram_username(normalized_username)
        if not user:
            user = await self.user_repo.create_user()
            placeholder_tg_id = self._placeholder_telegram_id_from_username(normalized_username)
            self.session.add(
                TelegramAccount(
                    user_id=user.id,
                    telegram_user_id=placeholder_tg_id,
                    username=normalized_username,
                    first_name=None,
                    last_name=None,
                    language_code=None,
                    is_bot=False,
                )
            )
            await self.session.flush()

        if client_uuid:
            snapshot = await self.threexui_service.client.get_client_snapshot(
                inbound_id=inbound_id,
                client_uuid=client_uuid,
                email_remark=f'@{normalized_username}',
            )
            if not snapshot:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Panel client not found')
            snapshots = [snapshot]
        else:
            snapshots = await self.threexui_service.list_clients_by_username(normalized_username)
            if not snapshots:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='No panel clients for username')

        default_plan = await self.plan_repo.get_default_active_plan()
        if not default_plan:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='No active plan configured')

        picked = max(
            snapshots,
            key=lambda item: item.expires_at or datetime.now(timezone.utc),
        )

        if await self.key_repo.exists_by_client_uuid(picked.client_uuid):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Client is already linked')

        now = datetime.now(timezone.utc)
        expires_at = picked.expires_at or (now + timedelta(days=30))
        sub_status = SubscriptionStatus.ACTIVE if expires_at > now and (picked.is_active is not False) else SubscriptionStatus.EXPIRED
        key_status = VPNKeyStatus.ACTIVE if sub_status == SubscriptionStatus.ACTIVE else VPNKeyStatus.EXPIRED

        key = await self.key_repo.create(
            owner_id=user.id,
            display_name=display_name or f'VPN @{normalized_username}',
        )

        subscription = Subscription(
            vpn_key_id=key.id,
            plan_id=default_plan.id,
            starts_at=now,
            expires_at=expires_at,
            status=sub_status,
        )
        self.session.add(subscription)
        await self.session.flush()

        key.current_subscription_id = subscription.id
        key.status = key_status

        version = VPNKeyVersion(
            vpn_key_id=key.id,
            version=1,
            threexui_client_uuid=picked.client_uuid,
            inbound_id=picked.inbound_id,
            email_remark=picked.email_remark or f'@{normalized_username}',
            connection_uri=picked.connection_uri,
            raw_config=picked.raw,
            is_active=sub_status == SubscriptionStatus.ACTIVE,
            revoked_at=None if sub_status == SubscriptionStatus.ACTIVE else now,
        )
        self.session.add(version)
        await self.session.commit()
        await self.session.refresh(version)
        return version, user.id

    async def create_plan(
        self,
        *,
        name: str,
        duration_days: int,
        price: Decimal,
        currency: str,
        is_active: bool,
        sort_order: int,
    ) -> Plan:
        plan = await self.plan_repo.create(
            name=name,
            duration_days=duration_days,
            price=price,
            currency=currency,
            is_active=is_active,
            sort_order=sort_order,
        )
        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def update_plan(
        self,
        plan_id: UUID,
        *,
        name: str | None = None,
        duration_days: int | None = None,
        price: Decimal | None = None,
        currency: str | None = None,
        is_active: bool | None = None,
        sort_order: int | None = None,
    ) -> Plan:
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        if name is not None:
            plan.name = name
        if duration_days is not None:
            plan.duration_days = duration_days
        if price is not None:
            plan.price = price
        if currency is not None:
            plan.currency = currency.upper()
        if is_active is not None:
            plan.is_active = is_active
        if sort_order is not None:
            plan.sort_order = sort_order

        await self.session.commit()
        await self.session.refresh(plan)
        return plan

    async def revoke_key(self, key_id: UUID, reason: str) -> VPNKey:
        key = await self.session.scalar(
            select(VPNKey)
            .where(VPNKey.id == key_id)
            .options(selectinload(VPNKey.versions), selectinload(VPNKey.current_subscription))
        )
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        active_version = next((item for item in key.versions if item.is_active), None)
        if active_version:
            await self.threexui_service.revoke_vpn_client(active_version)
            active_version.is_active = False
            active_version.revoked_at = datetime.now(timezone.utc)

        if key.current_subscription:
            key.current_subscription.status = SubscriptionStatus.REVOKED

        key.status = VPNKeyStatus.REVOKED

        await self.session.commit()
        return key

    async def delete_key_from_history(self, key_id: UUID, reason: str) -> dict[str, str | bool]:
        key = await self.session.scalar(
            select(VPNKey)
            .where(VPNKey.id == key_id)
            .options(selectinload(VPNKey.versions), selectinload(VPNKey.current_subscription))
        )
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        active_version = next((item for item in key.versions if item.is_active), None)
        if active_version:
            try:
                await self.threexui_service.revoke_vpn_client(active_version)
            except Exception:  # noqa: BLE001
                logger.warning('Admin delete key: failed to revoke panel client for key %s', key_id)

        audit = AuditLog(
            actor_type='admin',
            actor_id=None,
            action='admin_delete_key',
            entity_type='vpn_key',
            entity_id=str(key.id),
            metadata_json={'reason': reason[:255]},
        )
        self.session.add(audit)
        await self.session.flush()
        await self.session.execute(
            update(Payment)
            .where(Payment.vpn_key_id == key.id)
            .values(vpn_key_id=None)
        )
        await self.session.execute(delete(VPNKey).where(VPNKey.id == key.id))
        await self.session.commit()
        return {'ok': True, 'key_id': str(key_id)}

    async def add_bonus_days(self, user_id: UUID, days: int, reason: str) -> None:
        await self.referral_service.adjust_bonus_days(user_id=user_id, days_delta=days, reason=reason)
        await self.session.commit()

    async def grant_subscription(self, user_id: UUID, plan_id: UUID, key_id: UUID | None, key_name: str | None) -> VPNKey:
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')

        if key_id:
            key = await self.session.scalar(
                select(VPNKey)
                .where(VPNKey.id == key_id, VPNKey.owner_id == user_id)
                .options(selectinload(VPNKey.current_subscription), selectinload(VPNKey.versions))
            )
            if not key:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')
        else:
            key = await self.key_repo.create(owner_id=user_id, display_name=key_name or 'Admin granted key')

        now = datetime.now(timezone.utc)
        add_days = plan.duration_days

        if key.current_subscription:
            base = key.current_subscription.expires_at if key.current_subscription.expires_at > now else now
            key.current_subscription.expires_at = base + timedelta(days=add_days)
            key.current_subscription.status = SubscriptionStatus.ACTIVE
            new_expiry = key.current_subscription.expires_at
            current_subscription = key.current_subscription
        else:
            new_expiry = now + timedelta(days=add_days)
            subscription = Subscription(
                vpn_key_id=key.id,
                plan_id=plan.id,
                starts_at=now,
                expires_at=new_expiry,
                status=SubscriptionStatus.ACTIVE,
            )
            self.session.add(subscription)
            await self.session.flush()
            key.current_subscription_id = subscription.id
            current_subscription = subscription

        key.status = VPNKeyStatus.ACTIVE

        # Async-safe: fetch active version via repository instead of lazy relationship access.
        active_version = await self.key_repo.get_active_version(key.id)
        try:
            if active_version:
                refreshed_uri = await self.threexui_service.extend_vpn_client(active_version, new_expiry)
                if refreshed_uri:
                    active_version.connection_uri = refreshed_uri
            else:
                next_version = await self.key_repo.get_next_version(key.id)
                created = await self.threexui_service.create_vpn_client(
                    user=user,
                    key=key,
                    subscription=current_subscription,
                    version_number=next_version,
                )
                self.session.add(
                    VPNKeyVersion(
                        vpn_key_id=key.id,
                        version=next_version,
                        threexui_client_uuid=created.client_uuid,
                        inbound_id=created.inbound_id,
                        email_remark=created.email_remark,
                        connection_uri=created.connection_uri,
                        raw_config=created.raw,
                        is_active=True,
                    )
                )
        except Exception as exc:  # noqa: BLE001
            logger.exception('Admin grant subscription failed in 3x-ui integration: user_id=%s key_id=%s', user_id, key.id)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Не удалось выдать доступ в 3x-ui. Проверьте доступность панели и настройки.',
            ) from exc

        await self.session.commit()
        return key


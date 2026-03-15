from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import PaymentOperation, PaymentProvider as PaymentProviderEnum, PaymentStatus, SubscriptionStatus, VPNKeyStatus
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.vpn_key_repository import VPNKeyRepository
from app.repositories.app_settings_repository import AppSettingsRepository
from app.services.access_policy_service import AccessPolicyService
from app.services.notification_service import NotificationService
from app.services.referral_service import ReferralService


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        threexui_service: ThreeXUIService,
        notification_service: NotificationService,
    ) -> None:
        self.session = session
        self.threexui_service = threexui_service
        self.notification_service = notification_service
        self.payment_repo = PaymentRepository(session)
        self.plan_repo = PlanRepository(session)
        self.key_repo = VPNKeyRepository(session)
        self.app_settings_repo = AppSettingsRepository(session)
        self.access_policy = AccessPolicyService(session)
        self.referral_service = ReferralService(session)
        self.settings = get_settings()

    async def create_purchase_intent(
        self,
        user: User,
        plan_id: UUID,
        key_name: str | None,
        apply_bonus_days: int,
    ) -> Payment:
        if not self.settings.payment_phone:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Payment phone is not configured')

        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        bonus_days = await self._validate_bonus_days(user, apply_bonus_days)
        transfer_note = self._build_transfer_note(operation=PaymentOperation.PURCHASE, plan_name=plan.name)

        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider=PaymentProviderEnum.YOOKASSA,  # legacy enum value in DB, used as generic provider marker
            operation=PaymentOperation.PURCHASE,
            amount=plan.price,
            currency=plan.currency,
            status=PaymentStatus.PENDING,
            idempotence_key=uuid.uuid4().hex,
            bonus_days_applied=bonus_days,
            metadata_json={
                'key_name': key_name or 'VPN Key',
                'transfer_phone': self.settings.payment_phone,
                'transfer_note': transfer_note,
            },
        )
        await self.payment_repo.create(payment)

        await self.session.commit()
        await self.session.refresh(payment)
        await self._notify_admin_about_payment_request(user=user, payment=payment, plan_name=plan.name)
        return payment

    async def create_renew_intent(
        self,
        user: User,
        key_id: UUID,
        plan_id: UUID,
        apply_bonus_days: int,
    ) -> Payment:
        if not self.settings.payment_phone:
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail='Payment phone is not configured')

        key = await self.key_repo.get_owned_key(key_id, user.id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        bonus_days = await self._validate_bonus_days(user, apply_bonus_days)
        transfer_note = self._build_transfer_note(operation=PaymentOperation.RENEW, plan_name=plan.name)

        payment = Payment(
            user_id=user.id,
            vpn_key_id=key.id,
            plan_id=plan.id,
            provider=PaymentProviderEnum.YOOKASSA,  # legacy enum value in DB, used as generic provider marker
            operation=PaymentOperation.RENEW,
            amount=plan.price,
            currency=plan.currency,
            status=PaymentStatus.PENDING,
            idempotence_key=uuid.uuid4().hex,
            bonus_days_applied=bonus_days,
            metadata_json={
                'key_name': key.display_name,
                'transfer_phone': self.settings.payment_phone,
                'transfer_note': transfer_note,
            },
        )
        await self.payment_repo.create(payment)

        await self.session.commit()
        await self.session.refresh(payment)
        await self._notify_admin_about_payment_request(user=user, payment=payment, plan_name=plan.name)
        return payment

    async def mark_manual_payment_succeeded(self, payment_id: UUID) -> Payment:
        locked_payment = await self.payment_repo.get_by_id_for_update(payment_id)
        if not locked_payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Payment not found')

        if locked_payment.status == PaymentStatus.SUCCEEDED:
            await self.session.commit()
            return locked_payment

        if locked_payment.status in {PaymentStatus.CANCELED, PaymentStatus.FAILED}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Payment is not payable')

        locked_payment.status = PaymentStatus.SUCCEEDED
        await self._apply_successful_payment(locked_payment)
        now = datetime.now(timezone.utc)
        locked_payment.succeeded_at = now
        locked_payment.processed_at = now

        await self.session.commit()
        await self.session.refresh(locked_payment)
        return locked_payment

    async def mark_manual_payment_failed(self, payment_id: UUID) -> Payment:
        locked_payment = await self.payment_repo.get_by_id_for_update(payment_id)
        if not locked_payment:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Payment not found')

        if locked_payment.status == PaymentStatus.SUCCEEDED:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Succeeded payment cannot be failed')

        locked_payment.status = PaymentStatus.FAILED
        locked_payment.processed_at = datetime.now(timezone.utc)
        await self.session.commit()
        await self.session.refresh(locked_payment)
        return locked_payment

    async def _apply_successful_payment(self, payment: Payment) -> None:
        user = await self.session.scalar(
            select(User).where(User.id == payment.user_id).options(selectinload(User.telegram_account)).with_for_update()
        )
        if not user:
            raise RuntimeError('User not found during payment processing')

        plan = await self.plan_repo.get_by_id(payment.plan_id)
        if not plan:
            raise RuntimeError('Plan missing during payment processing')

        if payment.bonus_days_applied > 0:
            await self.referral_service.adjust_bonus_days(
                user_id=user.id,
                days_delta=-payment.bonus_days_applied,
                reason='bonus_days_applied_on_payment',
                related_payment_id=payment.id,
            )

        duration_days = plan.duration_days + payment.bonus_days_applied

        if payment.operation == PaymentOperation.PURCHASE:
            await self._activate_purchase_payment(user, payment, duration_days)
        elif payment.operation == PaymentOperation.RENEW:
            await self._activate_renew_payment(user, payment, duration_days)

        await self.referral_service.apply_referral_reward_if_eligible(user.id, payment)

        if user.telegram_account:
            await self.notification_service.enqueue_telegram_notification(
                telegram_user_id=user.telegram_account.telegram_user_id,
                text=f'Платеж подтвержден. Статус: {payment.status.value}.',
            )

    async def _activate_purchase_payment(self, user: User, payment: Payment, duration_days: int) -> None:
        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=duration_days)

        key_name = (payment.metadata_json or {}).get('key_name') or 'VPN Key'
        key = await self.key_repo.create(owner_id=user.id, display_name=key_name)

        subscription = Subscription(
            vpn_key_id=key.id,
            plan_id=payment.plan_id,
            starts_at=now,
            expires_at=expires,
            status=SubscriptionStatus.ACTIVE,
        )
        self.session.add(subscription)
        await self.session.flush()

        key.current_subscription_id = subscription.id
        key.status = VPNKeyStatus.ACTIVE
        payment.vpn_key_id = key.id

        inbound_ids = await self.access_policy.resolve_plan_inbound_ids(
            plan_id=payment.plan_id,
            threexui_service=self.threexui_service,
        )
        created = await self.threexui_service.create_vpn_client(
            user=user,
            key=key,
            subscription=subscription,
            version_number=1,
            inbound_ids=inbound_ids,
        )
        version = VPNKeyVersion(
            vpn_key_id=key.id,
            version=1,
            threexui_client_uuid=created.client_uuid,
            inbound_id=created.inbound_id,
            email_remark=created.email_remark,
            connection_uri=created.connection_uri,
            raw_config=created.raw,
            is_active=True,
        )
        self.session.add(version)

        if user.telegram_account:
            proxy_url, proxy_button_text = await self._get_telegram_proxy_button()
            await self.notification_service.enqueue_telegram_notification(
                telegram_user_id=user.telegram_account.telegram_user_id,
                text=f'VPN ключ создан: {key.display_name}. Действует до {expires.date().isoformat()}.',
                button_url=proxy_url,
                button_text=proxy_button_text,
            )

    async def _activate_renew_payment(self, user: User, payment: Payment, duration_days: int) -> None:
        if not payment.vpn_key_id:
            raise RuntimeError('Renew payment without vpn_key_id')

        key = await self.key_repo.get_for_update(payment.vpn_key_id)
        if not key:
            raise RuntimeError('VPN key not found for renew payment')

        now = datetime.now(timezone.utc)
        if key.current_subscription:
            base = key.current_subscription.expires_at if key.current_subscription.expires_at > now else now
            key.current_subscription.expires_at = base + timedelta(days=duration_days)
            key.current_subscription.status = SubscriptionStatus.ACTIVE
            new_expires = key.current_subscription.expires_at
            current_subscription = key.current_subscription
        else:
            new_expires = now + timedelta(days=duration_days)
            subscription = Subscription(
                vpn_key_id=key.id,
                plan_id=payment.plan_id,
                starts_at=now,
                expires_at=new_expires,
                status=SubscriptionStatus.ACTIVE,
            )
            self.session.add(subscription)
            await self.session.flush()
            key.current_subscription_id = subscription.id
            current_subscription = subscription

        key.status = VPNKeyStatus.ACTIVE

        active_version = await self.key_repo.get_active_version(key.id)
        if active_version:
            refreshed_uri = await self.threexui_service.extend_vpn_client(active_version, new_expires)
            if refreshed_uri:
                active_version.connection_uri = refreshed_uri
        else:
            next_version = await self.key_repo.get_next_version(key.id)
            created = await self.threexui_service.create_vpn_client(
                user=user,
                key=key,
                subscription=current_subscription,
                version_number=next_version,
                inbound_ids=await self.access_policy.resolve_plan_inbound_ids(
                    plan_id=payment.plan_id,
                    threexui_service=self.threexui_service,
                ),
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

        if user.telegram_account:
            proxy_url, proxy_button_text = await self._get_telegram_proxy_button()
            await self.notification_service.enqueue_telegram_notification(
                telegram_user_id=user.telegram_account.telegram_user_id,
                text=f'Ключ {key.display_name} продлен до {new_expires.date().isoformat()}.',
                button_url=proxy_url,
                button_text=proxy_button_text,
            )

    async def _validate_bonus_days(self, user: User, apply_bonus_days: int) -> int:
        if apply_bonus_days <= 0:
            return 0
        if apply_bonus_days > user.bonus_days_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not enough bonus days')
        return apply_bonus_days

    def _build_transfer_note(self, operation: PaymentOperation, plan_name: str) -> str:
        operation_text = 'покупка' if operation == PaymentOperation.PURCHASE else 'продление'
        return f'VPN {operation_text} | {plan_name} | payment:{uuid.uuid4().hex[:10]}'

    async def _get_telegram_proxy_button(self) -> tuple[str | None, str]:
        proxy_url_setting = await self.app_settings_repo.get('telegram_proxy_url')
        button_text_setting = await self.app_settings_repo.get('telegram_proxy_button_text')
        proxy_url = proxy_url_setting.value.strip() if proxy_url_setting and proxy_url_setting.value.strip() else None
        button_text = (
            button_text_setting.value.strip()
            if button_text_setting and button_text_setting.value.strip()
            else 'Подключить прокси'
        )
        return proxy_url, button_text

    async def _notify_admin_about_payment_request(self, *, user: User, payment: Payment, plan_name: str) -> None:
        admin_telegram_id = self.settings.telegram_admin_id
        if not admin_telegram_id:
            return

        account = user.telegram_account
        user_label = (
            f'@{account.username}'
            if account and account.username
            else f'tg_{account.telegram_user_id}'
            if account
            else f'user_{str(user.id)[:8]}'
        )
        operation_text = 'покупку' if payment.operation == PaymentOperation.PURCHASE else 'продление'
        transfer_note = (payment.metadata_json or {}).get('transfer_note') or '-'
        text = (
            'Новый запрос на оплату\n\n'
            f'Пользователь: {user_label}\n'
            f'Операция: {operation_text}\n'
            f'Тариф: {plan_name}\n'
            f'Сумма: {payment.amount} {payment.currency}\n'
            f'Платёж: {payment.id}\n'
            f'Комментарий к переводу: {transfer_note}'
        )
        await self.notification_service.enqueue_telegram_notification(
            telegram_user_id=admin_telegram_id,
            text=text,
        )

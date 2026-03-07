from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.integrations.payments.base import PaymentProvider
from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import PaymentOperation, PaymentProvider as PaymentProviderEnum, PaymentStatus, SubscriptionStatus, VPNKeyStatus
from app.models.payment import Payment
from app.models.payment_event import PaymentEvent
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.vpn_key_repository import VPNKeyRepository
from app.services.notification_service import NotificationService
from app.services.referral_service import ReferralService


class PaymentService:
    def __init__(
        self,
        session: AsyncSession,
        provider: PaymentProvider,
        threexui_service: ThreeXUIService,
        notification_service: NotificationService,
    ) -> None:
        self.session = session
        self.provider = provider
        self.threexui_service = threexui_service
        self.notification_service = notification_service
        self.payment_repo = PaymentRepository(session)
        self.plan_repo = PlanRepository(session)
        self.key_repo = VPNKeyRepository(session)
        self.referral_service = ReferralService(session)
        self.settings = get_settings()

    async def create_purchase_intent(
        self,
        user: User,
        plan_id: UUID,
        key_name: str | None,
        apply_bonus_days: int,
    ) -> Payment:
        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        bonus_days = await self._validate_bonus_days(user, apply_bonus_days)
        payment = Payment(
            user_id=user.id,
            plan_id=plan.id,
            provider=PaymentProviderEnum.YOOKASSA,
            operation=PaymentOperation.PURCHASE,
            amount=plan.price,
            currency=plan.currency,
            status=PaymentStatus.PENDING,
            idempotence_key=uuid.uuid4().hex,
            bonus_days_applied=bonus_days,
            metadata_json={'key_name': key_name or 'VPN Key'},
        )
        await self.payment_repo.create(payment)

        provider_result = await self.provider.create_payment(
            amount=payment.amount,
            currency=payment.currency,
            description=f'VPN subscription: {plan.name}',
            return_url=self.settings.yookassa_return_url,
            idempotence_key=payment.idempotence_key,
            metadata={'internal_payment_id': str(payment.id), 'operation': payment.operation.value},
        )

        payment.external_payment_id = provider_result.payment_id
        payment.confirmation_url = provider_result.confirmation_url
        payment.status = self._map_provider_status(provider_result.status)

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def create_renew_intent(
        self,
        user: User,
        key_id: UUID,
        plan_id: UUID,
        apply_bonus_days: int,
    ) -> Payment:
        key = await self.key_repo.get_owned_key(key_id, user.id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        plan = await self.plan_repo.get_by_id(plan_id)
        if not plan or not plan.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Plan not found')

        bonus_days = await self._validate_bonus_days(user, apply_bonus_days)

        payment = Payment(
            user_id=user.id,
            vpn_key_id=key.id,
            plan_id=plan.id,
            provider=PaymentProviderEnum.YOOKASSA,
            operation=PaymentOperation.RENEW,
            amount=plan.price,
            currency=plan.currency,
            status=PaymentStatus.PENDING,
            idempotence_key=uuid.uuid4().hex,
            bonus_days_applied=bonus_days,
            metadata_json={'key_name': key.display_name},
        )
        await self.payment_repo.create(payment)

        provider_result = await self.provider.create_payment(
            amount=payment.amount,
            currency=payment.currency,
            description=f'Renew VPN key: {key.display_name}',
            return_url=self.settings.yookassa_return_url,
            idempotence_key=payment.idempotence_key,
            metadata={'internal_payment_id': str(payment.id), 'operation': payment.operation.value},
        )

        payment.external_payment_id = provider_result.payment_id
        payment.confirmation_url = provider_result.confirmation_url
        payment.status = self._map_provider_status(provider_result.status)

        await self.session.commit()
        await self.session.refresh(payment)
        return payment

    async def process_yookassa_webhook(self, payload: dict[str, Any]) -> None:
        event = await self.provider.parse_webhook(payload)

        existing_event = await self.session.scalar(
            select(PaymentEvent).where(PaymentEvent.provider_event_id == event.provider_event_id)
        )
        if existing_event:
            return

        payment = await self.payment_repo.get_by_external_id(event.payment_id)
        payment_event = PaymentEvent(
            payment_id=payment.id if payment else None,
            provider=PaymentProviderEnum.YOOKASSA,
            provider_event_id=event.provider_event_id,
            event_type=event.event_type,
            payload=event.raw,
        )
        self.session.add(payment_event)

        if not payment:
            await self.session.commit()
            return

        locked_payment = await self.payment_repo.get_by_id_for_update(payment.id)
        if not locked_payment:
            await self.session.commit()
            return

        provider_payment = await self.provider.get_payment(locked_payment.external_payment_id or '')
        if provider_payment.amount != locked_payment.amount or provider_payment.currency != locked_payment.currency:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Payment amount or currency mismatch',
            )
        locked_payment.status = self._map_provider_status(provider_payment.status)

        if locked_payment.status == PaymentStatus.SUCCEEDED and locked_payment.processed_at is None:
            await self._apply_successful_payment(locked_payment)
            locked_payment.succeeded_at = datetime.now(timezone.utc)
            locked_payment.processed_at = datetime.now(timezone.utc)

        await self.session.commit()

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

        created = await self.threexui_service.create_vpn_client(user=user, key=key, subscription=subscription, version_number=1)
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
            await self.notification_service.enqueue_telegram_notification(
                telegram_user_id=user.telegram_account.telegram_user_id,
                text=f'VPN ключ создан: {key.display_name}. Действует до {expires.date().isoformat()}.',
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
            await self.threexui_service.extend_vpn_client(active_version, new_expires)
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

        if user.telegram_account:
            await self.notification_service.enqueue_telegram_notification(
                telegram_user_id=user.telegram_account.telegram_user_id,
                text=f'Ключ {key.display_name} продлен до {new_expires.date().isoformat()}.',
            )

    async def _validate_bonus_days(self, user: User, apply_bonus_days: int) -> int:
        if apply_bonus_days <= 0:
            return 0
        if apply_bonus_days > user.bonus_days_balance:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Not enough bonus days')
        return apply_bonus_days

    @staticmethod
    def _map_provider_status(raw_status: str) -> PaymentStatus:
        mapping = {
            'pending': PaymentStatus.PENDING,
            'waiting_for_capture': PaymentStatus.WAITING_FOR_CAPTURE,
            'succeeded': PaymentStatus.SUCCEEDED,
            'canceled': PaymentStatus.CANCELED,
            'failed': PaymentStatus.FAILED,
        }
        return mapping.get(raw_status, PaymentStatus.PENDING)


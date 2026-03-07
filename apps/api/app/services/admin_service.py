from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import SubscriptionStatus, VPNKeyStatus
from app.models.payment import Payment
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion
from app.repositories.payment_repository import PaymentRepository
from app.repositories.plan_repository import PlanRepository
from app.repositories.referral_repository import ReferralRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vpn_key_repository import VPNKeyRepository
from app.services.referral_service import ReferralService


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

    async def list_users(self, limit: int = 100, offset: int = 0):
        return await self.user_repo.list_users(limit=limit, offset=offset)

    async def list_payments(self, limit: int = 100, offset: int = 0) -> list[Payment]:
        return await self.payment_repo.list_all(limit=limit, offset=offset)

    async def list_keys(self, limit: int = 100, offset: int = 0) -> list[VPNKey]:
        stmt = select(VPNKey).order_by(VPNKey.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all()

    async def list_referrals(self, limit: int = 100, offset: int = 0):
        return await self.referral_repo.list_all(limit=limit, offset=offset)

    async def list_subscriptions(self, limit: int = 100, offset: int = 0) -> list[Subscription]:
        stmt = select(Subscription).order_by(Subscription.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all()

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

        active_version = next((item for item in key.versions if item.is_active), None)
        if active_version:
            await self.threexui_service.extend_vpn_client(active_version, new_expiry)
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

        await self.session.commit()
        return key


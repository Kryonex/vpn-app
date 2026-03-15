from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import create_access_token, validate_telegram_init_data
from app.integrations.threexui.service import ThreeXUIService
from app.models.audit_log import AuditLog
from app.models.enums import SubscriptionStatus, VPNKeyStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key_version import VPNKeyVersion
from app.services.access_policy_service import AccessPolicyService
from app.repositories.plan_repository import PlanRepository
from app.repositories.user_repository import UserRepository
from app.repositories.vpn_key_repository import VPNKeyRepository
from app.services.referral_service import ReferralService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.referral_service = ReferralService(session)
        self.key_repo = VPNKeyRepository(session)
        self.plan_repo = PlanRepository(session)
        self.access_policy = AccessPolicyService(session)

    async def authenticate_telegram(self, init_data: str, bot_token: str) -> tuple[User, str]:
        validated = validate_telegram_init_data(init_data, bot_token)
        tg_user = validated['user']

        telegram_user_id = int(tg_user['id'])
        user = await self.user_repo.get_by_telegram_id(telegram_user_id)
        username = (tg_user.get('username') or '').strip().lower() or None

        # If user was pre-bound by username before first login, reuse that local account.
        if not user and username:
            user = await self.user_repo.get_by_telegram_username(username)
        if not user:
            user = await self.user_repo.create_user()

        await self.user_repo.upsert_telegram_account(
            user=user,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=tg_user.get('first_name'),
            last_name=tg_user.get('last_name'),
            language_code=tg_user.get('language_code'),
            is_bot=bool(tg_user.get('is_bot', False)),
        )

        await self.referral_service.link_referred_user(user, validated.get('start_param'))
        await self._import_panel_keys_for_username_if_needed(user=user, username=username)
        await self._maybe_grant_free_trial(user)

        await self.session.commit()
        await self.session.refresh(user)

        token = create_access_token(str(user.id))
        return user, token

    async def upsert_from_bot_start(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        referral_code: str | None,
    ) -> User:
        user = await self.user_repo.get_by_telegram_id(telegram_user_id)
        if not user:
            user = await self.user_repo.create_user()

        await self.user_repo.upsert_telegram_account(
            user=user,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_bot=False,
        )
        await self.referral_service.link_referred_user(user, referral_code)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def _import_panel_keys_for_username_if_needed(self, user: User, username: str | None) -> None:
        if not username:
            return
        existing_count = await self.key_repo.count_by_owner(user.id)
        if existing_count > 0:
            return

        default_plan = await self.plan_repo.get_default_active_plan()
        if not default_plan:
            return

        threexui = ThreeXUIService()
        try:
            snapshots = await threexui.list_clients_by_username(username)
        finally:
            await threexui.client.close()

        if not snapshots:
            return

        now = datetime.now(timezone.utc)
        grouped_snapshots: dict[str, list] = {}
        for snapshot in snapshots:
            grouped_snapshots.setdefault(snapshot.client_uuid, []).append(snapshot)

        for client_uuid, snapshot_group in grouped_snapshots.items():
            snapshot = snapshot_group[0]
            if await self.key_repo.exists_by_client_uuid(snapshot.client_uuid):
                continue

            expires_at = snapshot.expires_at or (now + timedelta(days=30))
            sub_status = (
                SubscriptionStatus.ACTIVE
                if expires_at > now and (snapshot.is_active is not False)
                else SubscriptionStatus.EXPIRED
            )
            key_status = VPNKeyStatus.ACTIVE if sub_status == SubscriptionStatus.ACTIVE else VPNKeyStatus.EXPIRED

            key = await self.key_repo.create(owner_id=user.id, display_name=f'VPN @{username}')
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
            self.session.add(
                VPNKeyVersion(
                    vpn_key_id=key.id,
                    version=1,
                    threexui_client_uuid=client_uuid,
                    inbound_id=snapshot.inbound_id,
                    email_remark=snapshot.email_remark or f'@{username}',
                    connection_uri=snapshot.connection_uri,
                    raw_config={
                        'imported_from_panel': True,
                        'managed_inbound_ids': [
                            item.inbound_id for item in snapshot_group if item.inbound_id is not None
                        ],
                        'sub_id': next((item.sub_id for item in snapshot_group if item.sub_id), None),
                        'snapshots': [item.raw for item in snapshot_group],
                    },
                    is_active=sub_status == SubscriptionStatus.ACTIVE,
                    revoked_at=None if sub_status == SubscriptionStatus.ACTIVE else now,
                )
            )

    async def _maybe_grant_free_trial(self, user: User) -> None:
        existing_grant = await self.session.scalar(
            select(AuditLog.id).where(
                AuditLog.action == 'free_trial_granted',
                AuditLog.entity_type == 'user',
                AuditLog.entity_id == str(user.id),
            ).limit(1)
        )
        if existing_grant:
            return

        if await self.key_repo.count_by_owner(user.id) > 0:
            return

        settings = await self.access_policy.get_free_trial_settings()
        if not settings['enabled']:
            return

        trial_plan = await self.access_policy.ensure_free_trial_plan(settings['days'])
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(days=settings['days'])
        key = await self.key_repo.create(owner_id=user.id, display_name='Пробный доступ')
        subscription = Subscription(
            vpn_key_id=key.id,
            plan_id=trial_plan.id,
            starts_at=now,
            expires_at=expires_at,
            status=SubscriptionStatus.ACTIVE,
        )
        self.session.add(subscription)
        await self.session.flush()

        key.current_subscription_id = subscription.id
        key.status = VPNKeyStatus.ACTIVE

        threexui = ThreeXUIService()
        try:
            inbound_ids = await self.access_policy.resolve_plan_inbound_ids(
                plan_id=None,
                threexui_service=threexui,
                fallback_to_free_trial=True,
            )
            created = await threexui.create_vpn_client(
                user=user,
                key=key,
                subscription=subscription,
                version_number=1,
                inbound_ids=inbound_ids,
            )
        finally:
            await threexui.client.close()

        self.session.add(
            VPNKeyVersion(
                vpn_key_id=key.id,
                version=1,
                threexui_client_uuid=created.client_uuid,
                inbound_id=created.inbound_id,
                email_remark=created.email_remark,
                connection_uri=created.connection_uri,
                raw_config=created.raw,
                is_active=True,
            )
        )
        self.session.add(
            AuditLog(
                actor_type='system',
                actor_id=None,
                action='free_trial_granted',
                entity_type='user',
                entity_id=str(user.id),
                metadata_json={'days': settings['days'], 'inbound_ids': inbound_ids},
            )
        )

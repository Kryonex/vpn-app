from __future__ import annotations

import logging
import re
from datetime import datetime, timezone

from app.integrations.threexui.client import ThreeXUIClient
from app.integrations.threexui.models import ThreeXUICreatedClient
from app.models.enums import SubscriptionStatus, VPNKeyStatus
from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion

logger = logging.getLogger(__name__)


class ThreeXUIService:
    def __init__(self, client: ThreeXUIClient | None = None) -> None:
        self.client = client or ThreeXUIClient()

    async def fetch_inbounds(self):
        return await self.client.get_inbounds()

    @staticmethod
    def _sanitize_label(value: str) -> str:
        return re.sub(r'[^a-zA-Z0-9_@.-]+', '_', value).strip('_')

    def _build_client_identity(self, user: User) -> str:
        account = user.telegram_account
        if account and account.username:
            return self._sanitize_label(f'@{account.username}')
        if account and account.telegram_user_id:
            return self._sanitize_label(f'tg_{account.telegram_user_id}')
        return self._sanitize_label(f'user_{str(user.id)[:8]}')

    def _build_email_remark(self, user: User, key: VPNKey, version_number: int) -> str:
        identity = self._build_client_identity(user)
        suffix = f'k{str(key.id)[:6]}v{version_number}'
        return self._sanitize_label(f'{identity}_{suffix}')

    async def create_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        version_number: int,
    ) -> ThreeXUICreatedClient:
        remark = self._build_email_remark(user, key, version_number)
        created = await self.client.create_client_on_default_inbound(email_remark=remark, expires_at=subscription.expires_at)
        if not created.connection_uri:
            snapshot = await self.client.get_client_snapshot(
                inbound_id=created.inbound_id,
                client_uuid=created.client_uuid,
                email_remark=created.email_remark,
            )
            if snapshot and snapshot.connection_uri:
                created.connection_uri = snapshot.connection_uri
        return created

    async def extend_vpn_client(self, version: VPNKeyVersion, new_expiry: datetime) -> str | None:
        if version.inbound_id is None:
            logger.warning('3x-ui extend skipped for key version %s: inbound_id missing', version.id)
            return version.connection_uri

        await self.client.update_client_expiry(
            inbound_id=version.inbound_id,
            client_uuid=version.threexui_client_uuid,
            email_remark=version.email_remark or version.threexui_client_uuid,
            expires_at=new_expiry,
        )

        snapshot = await self.client.get_client_snapshot(
            inbound_id=version.inbound_id,
            client_uuid=version.threexui_client_uuid,
            email_remark=version.email_remark,
        )
        return snapshot.connection_uri if snapshot and snapshot.connection_uri else version.connection_uri

    async def revoke_vpn_client(self, version: VPNKeyVersion) -> None:
        await self.client.delete_client(
            version.threexui_client_uuid,
            inbound_id=version.inbound_id,
            email_remark=version.email_remark,
        )

    async def rotate_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        current_version: VPNKeyVersion,
        new_version_number: int,
    ) -> ThreeXUICreatedClient:
        # Rotation is strict: old client must be removed/revoked in panel before issuing a replacement.
        await self.revoke_vpn_client(current_version)
        return await self.create_vpn_client(user=user, key=key, subscription=subscription, version_number=new_version_number)

    async def sync_key_with_panel_state(self, key: VPNKey) -> bool:
        changed = False
        now = datetime.now(timezone.utc)

        for version in key.versions:
            if not version.is_active:
                continue

            snapshot = await self.client.get_client_snapshot(
                inbound_id=version.inbound_id,
                client_uuid=version.threexui_client_uuid,
                email_remark=version.email_remark,
            )

            if not snapshot:
                version.is_active = False
                version.revoked_at = version.revoked_at or now
                changed = True
                logger.info('3x-ui sync: client missing in panel, revoke local version=%s', version.id)
                continue

            if snapshot.connection_uri and snapshot.connection_uri != version.connection_uri:
                version.connection_uri = snapshot.connection_uri
                changed = True

            if snapshot.email_remark and snapshot.email_remark != version.email_remark:
                version.email_remark = snapshot.email_remark
                changed = True

            if snapshot.inbound_id is not None and snapshot.inbound_id != version.inbound_id:
                version.inbound_id = snapshot.inbound_id
                changed = True

        has_active_version = any(item.is_active for item in key.versions)
        if not has_active_version:
            if key.status != VPNKeyStatus.REVOKED:
                key.status = VPNKeyStatus.REVOKED
                changed = True

            if key.current_subscription and key.current_subscription.status == SubscriptionStatus.ACTIVE:
                key.current_subscription.status = SubscriptionStatus.REVOKED
                changed = True

        return changed

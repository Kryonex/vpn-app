from __future__ import annotations

import logging
import re
import uuid
from datetime import datetime, timezone

from app.integrations.threexui.client import ThreeXUIClient
from app.integrations.threexui.models import ThreeXUICreatedClient, ThreeXUIPanelClientSnapshot
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

    async def list_clients_by_username(self, username: str) -> list[ThreeXUIPanelClientSnapshot]:
        return await self.client.list_client_snapshots_by_username(username)

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

    def _extract_managed_inbound_ids(self, version: VPNKeyVersion) -> list[int]:
        raw_config = version.raw_config if isinstance(version.raw_config, dict) else {}
        raw_ids = raw_config.get('managed_inbound_ids')
        if isinstance(raw_ids, list):
            normalized = sorted({int(item) for item in raw_ids if isinstance(item, int) or str(item).isdigit()})
            if normalized:
                return normalized
        return [version.inbound_id] if version.inbound_id is not None else []

    def _extract_sub_id(self, version: VPNKeyVersion) -> str | None:
        raw_config = version.raw_config if isinstance(version.raw_config, dict) else {}
        value = raw_config.get('sub_id')
        if isinstance(value, str) and value.strip():
            return value.strip()
        return None

    async def ensure_version_inbounds(
        self,
        version: VPNKeyVersion,
        *,
        expires_at: datetime,
        inbound_ids: list[int],
    ) -> bool:
        requested_inbound_ids = sorted({int(item) for item in inbound_ids if int(item) > 0})
        if not requested_inbound_ids:
            return False

        current_inbound_ids = self._extract_managed_inbound_ids(version)
        sub_id = self._extract_sub_id(version) or uuid.uuid4().hex[:16]
        missing_inbound_ids = [item for item in requested_inbound_ids if item not in current_inbound_ids]
        source_inbound_id = current_inbound_ids[0] if current_inbound_ids else version.inbound_id
        source_snapshot = None
        source_client_raw: dict[str, object] | None = None
        actual_email_remark = version.email_remark or version.threexui_client_uuid
        actual_expires_at = expires_at

        if source_inbound_id is not None:
            source_snapshot = await self.client.get_client_snapshot(
                inbound_id=source_inbound_id,
                client_uuid=version.threexui_client_uuid,
                email_remark=version.email_remark,
                fallback_sub_id=sub_id,
            )
        if source_snapshot:
            actual_email_remark = source_snapshot.email_remark or actual_email_remark
            actual_expires_at = source_snapshot.expires_at or actual_expires_at
            sub_id = source_snapshot.sub_id or sub_id
            raw = source_snapshot.raw if isinstance(source_snapshot.raw, dict) else {}
            source_client_raw = raw.get('client') if isinstance(raw.get('client'), dict) else None

        changed = False
        for inbound_id in missing_inbound_ids:
            existing_snapshot = await self.client.get_client_snapshot(
                inbound_id=inbound_id,
                client_uuid=version.threexui_client_uuid,
                email_remark=actual_email_remark,
                fallback_sub_id=sub_id,
            )
            if existing_snapshot:
                if not version.connection_uri and existing_snapshot.connection_uri:
                    version.connection_uri = existing_snapshot.connection_uri
                    changed = True
                continue

            created = await self.client.add_client(
                inbound_id=inbound_id,
                client_uuid=version.threexui_client_uuid,
                email_remark=actual_email_remark,
                expires_at=actual_expires_at,
                sub_id=sub_id,
                template_client=source_client_raw,
            )
            if not version.connection_uri and created.connection_uri:
                version.connection_uri = created.connection_uri
            changed = True

        raw_config = version.raw_config if isinstance(version.raw_config, dict) else {}
        merged_inbound_ids = sorted({*current_inbound_ids, *requested_inbound_ids})
        if raw_config.get('managed_inbound_ids') != merged_inbound_ids:
            raw_config['managed_inbound_ids'] = merged_inbound_ids
            changed = True
        if raw_config.get('sub_id') != sub_id:
            raw_config['sub_id'] = sub_id
            changed = True
        if changed:
            version.raw_config = raw_config
            version.email_remark = actual_email_remark
        return changed

    async def create_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        version_number: int,
        inbound_ids: list[int] | None = None,
    ) -> ThreeXUICreatedClient:
        remark = self._build_email_remark(user, key, version_number)
        target_inbound_ids = sorted({int(item) for item in (inbound_ids or []) if int(item) > 0})

        if not target_inbound_ids:
            created = await self.client.create_client_on_default_inbound(
                email_remark=remark,
                expires_at=subscription.expires_at,
            )
            created.managed_inbound_ids = [created.inbound_id]
            return created

        client_uuid = str(uuid.uuid4())
        sub_id = uuid.uuid4().hex[:16]
        created = await self.client.add_client(
            inbound_id=target_inbound_ids[0],
            client_uuid=client_uuid,
            email_remark=remark,
            expires_at=subscription.expires_at,
            sub_id=sub_id,
        )
        additional_payloads: list[dict[str, object]] = []
        for inbound_id in target_inbound_ids[1:]:
            extra = await self.client.add_client(
                inbound_id=inbound_id,
                client_uuid=client_uuid,
                email_remark=remark,
                expires_at=subscription.expires_at,
                sub_id=sub_id,
            )
            additional_payloads.append({'inbound_id': inbound_id, 'raw': extra.raw})

        created.managed_inbound_ids = target_inbound_ids
        created.sub_id = sub_id
        created.raw = {
            'primary': created.raw,
            'additional': additional_payloads,
            'managed_inbound_ids': target_inbound_ids,
            'sub_id': sub_id,
        }
        if not created.connection_uri:
            snapshot = await self.client.get_client_snapshot(
                inbound_id=created.inbound_id,
                client_uuid=created.client_uuid,
                email_remark=created.email_remark,
                fallback_sub_id=sub_id,
            )
            if snapshot and snapshot.connection_uri:
                created.connection_uri = snapshot.connection_uri
        return created

    async def extend_vpn_client(self, version: VPNKeyVersion, new_expiry: datetime) -> str | None:
        managed_inbound_ids = self._extract_managed_inbound_ids(version)
        if not managed_inbound_ids:
            logger.warning('3x-ui extend skipped for key version %s: inbound_id missing', version.id)
            return version.connection_uri

        sub_id = self._extract_sub_id(version)
        for inbound_id in managed_inbound_ids:
            await self.client.update_client_expiry(
                inbound_id=inbound_id,
                client_uuid=version.threexui_client_uuid,
                email_remark=version.email_remark or version.threexui_client_uuid,
                expires_at=new_expiry,
                sub_id=sub_id,
            )

        snapshot = await self.client.get_client_snapshot(
            inbound_id=managed_inbound_ids[0],
            client_uuid=version.threexui_client_uuid,
            email_remark=version.email_remark,
            fallback_sub_id=sub_id,
        )
        return snapshot.connection_uri if snapshot and snapshot.connection_uri else version.connection_uri

    async def revoke_vpn_client(self, version: VPNKeyVersion) -> None:
        managed_inbound_ids = self._extract_managed_inbound_ids(version)
        if not managed_inbound_ids:
            managed_inbound_ids = [version.inbound_id] if version.inbound_id is not None else []

        for inbound_id in managed_inbound_ids:
            await self.client.delete_client(
                version.threexui_client_uuid,
                inbound_id=inbound_id,
                email_remark=version.email_remark,
            )

    async def rotate_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        current_version: VPNKeyVersion,
        new_version_number: int,
        inbound_ids: list[int] | None = None,
    ) -> ThreeXUICreatedClient:
        await self.revoke_vpn_client(current_version)
        return await self.create_vpn_client(
            user=user,
            key=key,
            subscription=subscription,
            version_number=new_version_number,
            inbound_ids=inbound_ids or self._extract_managed_inbound_ids(current_version),
        )

    async def sync_key_with_panel_state(self, key: VPNKey) -> bool:
        changed = False
        now = datetime.now(timezone.utc)
        candidate_versions = [item for item in key.versions if item.is_active]
        if not candidate_versions and key.versions:
            candidate_versions = [max(key.versions, key=lambda item: item.version)]

        for version in candidate_versions:

            managed_inbound_ids = self._extract_managed_inbound_ids(version)
            sub_id = self._extract_sub_id(version)
            snapshots: list[ThreeXUIPanelClientSnapshot] = []
            missing_inbound = False

            for inbound_id in managed_inbound_ids:
                snapshot = await self.client.get_client_snapshot(
                    inbound_id=inbound_id,
                    client_uuid=version.threexui_client_uuid,
                    email_remark=version.email_remark,
                    fallback_sub_id=sub_id,
                )
                if not snapshot:
                    missing_inbound = True
                    break
                snapshots.append(snapshot)

            if missing_inbound or not snapshots:
                version.is_active = False
                version.revoked_at = version.revoked_at or now
                changed = True
                logger.info('3x-ui sync: client missing in panel, revoke local version=%s', version.id)
                continue

            snapshot = snapshots[0]
            panel_expires_at = min(
                (item.expires_at for item in snapshots if item.expires_at is not None),
                default=None,
            )
            panel_enabled = all(item.is_active is not False for item in snapshots)

            if snapshot.connection_uri and snapshot.connection_uri != version.connection_uri:
                version.connection_uri = snapshot.connection_uri
                changed = True

            if snapshot.email_remark and snapshot.email_remark != version.email_remark:
                version.email_remark = snapshot.email_remark
                changed = True

            if snapshot.inbound_id is not None and snapshot.inbound_id != version.inbound_id:
                version.inbound_id = snapshot.inbound_id
                changed = True

            raw_config = version.raw_config if isinstance(version.raw_config, dict) else {}
            actual_managed_inbound_ids = sorted({item.inbound_id for item in snapshots if item.inbound_id is not None})
            if raw_config.get('managed_inbound_ids') != actual_managed_inbound_ids:
                raw_config['managed_inbound_ids'] = actual_managed_inbound_ids
                changed = True
            resolved_sub_id = snapshot.sub_id or sub_id
            if resolved_sub_id and raw_config.get('sub_id') != resolved_sub_id:
                raw_config['sub_id'] = resolved_sub_id
                changed = True
            if changed:
                version.raw_config = raw_config

            if key.current_subscription and panel_expires_at and key.current_subscription.expires_at != panel_expires_at:
                key.current_subscription.expires_at = panel_expires_at
                changed = True

            if not panel_enabled:
                if version.is_active:
                    version.is_active = False
                    version.revoked_at = version.revoked_at or now
                    changed = True
                if key.current_subscription and key.current_subscription.status != SubscriptionStatus.REVOKED:
                    key.current_subscription.status = SubscriptionStatus.REVOKED
                    changed = True
                if key.status != VPNKeyStatus.REVOKED:
                    key.status = VPNKeyStatus.REVOKED
                    changed = True
                continue

            if panel_expires_at and panel_expires_at <= now:
                if version.is_active:
                    version.is_active = False
                    changed = True
                if key.current_subscription and key.current_subscription.status != SubscriptionStatus.EXPIRED:
                    key.current_subscription.status = SubscriptionStatus.EXPIRED
                    changed = True
                if key.status != VPNKeyStatus.EXPIRED:
                    key.status = VPNKeyStatus.EXPIRED
                    changed = True
                continue

            if not version.is_active:
                version.is_active = True
                version.revoked_at = None
                changed = True
            if key.current_subscription and key.current_subscription.status != SubscriptionStatus.ACTIVE:
                key.current_subscription.status = SubscriptionStatus.ACTIVE
                changed = True
            if key.status != VPNKeyStatus.ACTIVE:
                key.status = VPNKeyStatus.ACTIVE
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

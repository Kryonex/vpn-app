from __future__ import annotations

import logging
from datetime import datetime

from app.integrations.threexui.client import ThreeXUIClient
from app.integrations.threexui.models import ThreeXUICreatedClient
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

    async def create_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        version_number: int,
    ) -> ThreeXUICreatedClient:
        remark = f'u{str(user.id)[:8]}-k{str(key.id)[:8]}-v{version_number}'
        return await self.client.create_client_on_default_inbound(email_remark=remark, expires_at=subscription.expires_at)

    async def extend_vpn_client(self, version: VPNKeyVersion, new_expiry: datetime) -> None:
        if version.inbound_id is None:
            logger.warning('3x-ui extend skipped for key version %s: inbound_id missing', version.id)
            return
        await self.client.update_client_expiry(
            inbound_id=version.inbound_id,
            client_uuid=version.threexui_client_uuid,
            email_remark=version.email_remark or version.threexui_client_uuid,
            expires_at=new_expiry,
        )

    async def revoke_vpn_client(self, version: VPNKeyVersion) -> None:
        await self.client.delete_client(version.threexui_client_uuid)

    async def rotate_vpn_client(
        self,
        user: User,
        key: VPNKey,
        subscription: Subscription,
        current_version: VPNKeyVersion,
        new_version_number: int,
    ) -> ThreeXUICreatedClient:
        try:
            await self.revoke_vpn_client(current_version)
        except Exception:  # noqa: BLE001
            logger.warning('Failed to revoke old 3x-ui client %s during rotate', current_version.threexui_client_uuid)

        return await self.create_vpn_client(user=user, key=key, subscription=subscription, version_number=new_version_number)


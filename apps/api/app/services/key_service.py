from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import VPNKeyStatus
from app.models.audit_log import AuditLog
from app.models.vpn_key_version import VPNKeyVersion
from app.repositories.vpn_key_repository import VPNKeyRepository


class KeyService:
    def __init__(self, session: AsyncSession, threexui_service: ThreeXUIService) -> None:
        self.session = session
        self.repo = VPNKeyRepository(session)
        self.threexui_service = threexui_service

    async def list_user_keys(self, user_id: UUID):
        keys = await self.repo.list_by_owner(user_id)
        changed = False
        for key in keys:
            if await self.threexui_service.sync_key_with_panel_state(key):
                changed = True
        if changed:
            await self.session.commit()

        for key in keys:
            active_versions = [item for item in key.versions if item.is_active]
            active = max(active_versions, key=lambda item: item.version, default=None)
            setattr(key, 'active_version', active)
        return keys

    async def get_user_key(self, user_id: UUID, key_id: UUID):
        key = await self.repo.get_owned_key(key_id, user_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        if await self.threexui_service.sync_key_with_panel_state(key):
            await self.session.commit()

        active_versions = [item for item in key.versions if item.is_active]
        active = max(active_versions, key=lambda item: item.version, default=None)
        setattr(key, 'active_version', active)
        return key

    async def rotate_key(self, user_id: UUID, key_id: UUID):
        key = await self.repo.get_owned_key(key_id, user_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        subscription = key.current_subscription
        if not subscription or subscription.expires_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Cannot rotate expired key')

        old_version = next((item for item in key.versions if item.is_active), None)
        if not old_version:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Active key version not found')

        next_version = await self.repo.get_next_version(key.id)
        try:
            created = await self.threexui_service.rotate_vpn_client(
                user=key.owner,
                key=key,
                subscription=subscription,
                current_version=old_version,
                new_version_number=next_version,
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail='Failed to rotate key in 3x-ui panel',
            ) from exc

        old_version.is_active = False
        old_version.revoked_at = datetime.now(timezone.utc)

        new_version = VPNKeyVersion(
            vpn_key_id=key.id,
            version=next_version,
            threexui_client_uuid=created.client_uuid,
            inbound_id=created.inbound_id,
            email_remark=created.email_remark,
            connection_uri=created.connection_uri,
            raw_config=created.raw,
            is_active=True,
        )
        key.status = VPNKeyStatus.ACTIVE

        self.session.add(new_version)
        await self.session.commit()
        return new_version

    async def delete_user_key(self, user_id: UUID, key_id: UUID) -> dict[str, str | bool]:
        key = await self.repo.get_owned_key(key_id, user_id)
        if not key:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Key not found')

        if key.status == VPNKeyStatus.ACTIVE and any(item.is_active for item in key.versions):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail='Active key cannot be deleted. Revoke or rotate it first.',
            )

        active_version = next((item for item in key.versions if item.is_active), None)
        if active_version:
            try:
                await self.threexui_service.revoke_vpn_client(active_version)
            except Exception:  # noqa: BLE001
                pass

        self.session.add(
            AuditLog(
                actor_type='user',
                actor_id=str(user_id),
                action='user_delete_key',
                entity_type='vpn_key',
                entity_id=str(key_id),
                metadata_json=None,
            )
        )
        await self.session.flush()
        await self.session.delete(key)
        await self.session.commit()
        return {'ok': True, 'key_id': str(key_id)}


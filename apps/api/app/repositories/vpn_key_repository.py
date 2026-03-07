from __future__ import annotations

from uuid import UUID

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.subscription import Subscription
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion


class VPNKeyRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_by_owner(self, owner_id: UUID) -> list[VPNKey]:
        stmt = (
            select(VPNKey)
            .where(VPNKey.owner_id == owner_id)
            .options(
                selectinload(VPNKey.owner).selectinload(User.telegram_account),
                selectinload(VPNKey.current_subscription).selectinload(Subscription.plan),
                selectinload(VPNKey.versions),
            )
            .order_by(desc(VPNKey.created_at))
        )
        result = await self.session.scalars(stmt)
        return result.all()

    async def get_owned_key(self, key_id: UUID, owner_id: UUID) -> VPNKey | None:
        stmt = (
            select(VPNKey)
            .where(VPNKey.id == key_id, VPNKey.owner_id == owner_id)
            .options(
                selectinload(VPNKey.owner).selectinload(User.telegram_account),
                selectinload(VPNKey.current_subscription).selectinload(Subscription.plan),
                selectinload(VPNKey.versions),
            )
        )
        return await self.session.scalar(stmt)

    async def get_for_update(self, key_id: UUID) -> VPNKey | None:
        stmt = (
            select(VPNKey)
            .where(VPNKey.id == key_id)
            .with_for_update()
            .options(
                selectinload(VPNKey.owner).selectinload(User.telegram_account),
                selectinload(VPNKey.current_subscription),
                selectinload(VPNKey.versions),
            )
        )
        return await self.session.scalar(stmt)

    async def create(self, owner_id: UUID, display_name: str) -> VPNKey:
        key = VPNKey(owner_id=owner_id, display_name=display_name)
        self.session.add(key)
        await self.session.flush()
        return key

    async def get_next_version(self, key_id: UUID) -> int:
        stmt = select(VPNKeyVersion).where(VPNKeyVersion.vpn_key_id == key_id).order_by(VPNKeyVersion.version.desc()).limit(1)
        latest = await self.session.scalar(stmt)
        return (latest.version + 1) if latest else 1

    async def get_active_version(self, key_id: UUID) -> VPNKeyVersion | None:
        stmt = (
            select(VPNKeyVersion)
            .where(VPNKeyVersion.vpn_key_id == key_id, VPNKeyVersion.is_active.is_(True))
            .order_by(VPNKeyVersion.version.desc())
            .limit(1)
        )
        return await self.session.scalar(stmt)


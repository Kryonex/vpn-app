from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.enums import VPNKeyStatus
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion
from app.services.key_service import KeyService


class FakeRepo:
    def __init__(self, key: VPNKey | None) -> None:
        self.key = key

    async def get_owned_key(self, _key_id, _owner_id):
        return self.key


class FakeThreeXUIService:
    def __init__(self) -> None:
        self.revoked_client_uuid: str | None = None

    async def revoke_vpn_client(self, version: VPNKeyVersion) -> None:
        self.revoked_client_uuid = version.threexui_client_uuid


class FakeSession:
    def __init__(self) -> None:
        self.deleted: list[object] = []
        self.added: list[object] = []
        self.committed = False

    def add(self, item) -> None:
        self.added.append(item)

    async def flush(self) -> None:
        return None

    async def delete(self, item) -> None:
        self.deleted.append(item)

    async def commit(self) -> None:
        self.committed = True


def make_key(*, status: VPNKeyStatus, active_version: bool) -> VPNKey:
    key = VPNKey(
        id=uuid4(),
        owner_id=uuid4(),
        display_name='Test key',
        status=status,
    )
    version = VPNKeyVersion(
        id=uuid4(),
        vpn_key_id=key.id,
        version=1,
        threexui_client_uuid='client-1',
        inbound_id=1,
        email_remark='@tester',
        connection_uri='https://panel.example/sub/client-1',
        is_active=active_version,
        revoked_at=None if active_version else datetime.now(timezone.utc),
    )
    key.versions = [version]
    return key


@pytest.mark.asyncio
async def test_delete_user_key_rejects_active_key() -> None:
    session = FakeSession()
    threexui_service = FakeThreeXUIService()
    service = KeyService(session, threexui_service)  # type: ignore[arg-type]
    service.repo = FakeRepo(make_key(status=VPNKeyStatus.ACTIVE, active_version=True))

    with pytest.raises(HTTPException) as exc:
        await service.delete_user_key(uuid4(), uuid4())

    assert exc.value.status_code == 400
    assert session.committed is False


@pytest.mark.asyncio
async def test_delete_user_key_removes_revoked_key_from_history() -> None:
    session = FakeSession()
    threexui_service = FakeThreeXUIService()
    key = make_key(status=VPNKeyStatus.REVOKED, active_version=False)
    service = KeyService(session, threexui_service)  # type: ignore[arg-type]
    service.repo = FakeRepo(key)

    result = await service.delete_user_key(key.owner_id, key.id)

    assert result['ok'] is True
    assert session.deleted == [key]
    assert session.committed is True
    assert threexui_service.revoked_client_uuid is None

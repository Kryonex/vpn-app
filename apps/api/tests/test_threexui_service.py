import json
import uuid
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.integrations.threexui.client import ThreeXUIClient
from app.integrations.threexui.models import ThreeXUICreatedClient
from app.integrations.threexui.service import ThreeXUIService
from app.models.enums import SubscriptionStatus, VPNKeyStatus
from app.models.subscription import Subscription
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.vpn_key_version import VPNKeyVersion


class FakePanelClient:
    def __init__(self) -> None:
        self.deleted_client_uuid: str | None = None
        self.created_calls = 0
        self.raise_on_delete = False

    async def create_client_on_default_inbound(self, email_remark: str, expires_at: datetime) -> ThreeXUICreatedClient:
        self.created_calls += 1
        return ThreeXUICreatedClient(
            client_uuid='new-client',
            inbound_id=1,
            email_remark=email_remark,
            connection_uri='https://panel.example/sub/new-client',
            raw={},
        )

    async def delete_client(self, client_uuid: str, *, inbound_id: int | None = None, email_remark: str | None = None) -> None:
        if self.raise_on_delete:
            raise RuntimeError('delete failed')
        self.deleted_client_uuid = client_uuid

    async def get_client_snapshot(self, **_kwargs):
        return None

    async def update_client_expiry(self, **_kwargs):
        return None

    async def get_inbounds(self):
        return []


def make_user_key_version() -> tuple[User, VPNKey, Subscription, VPNKeyVersion]:
    user_id = uuid.uuid4()
    key_id = uuid.uuid4()
    now = datetime.now(timezone.utc)

    user = User(id=user_id, referral_code='refcode01', bonus_days_balance=0)
    user.telegram_account = TelegramAccount(
        user_id=user_id,
        telegram_user_id=123456789,
        username='someusername',
        first_name='Some',
        last_name='User',
        language_code='ru',
        is_bot=False,
    )

    key = VPNKey(id=key_id, owner_id=user_id, display_name='Test Key', status=VPNKeyStatus.ACTIVE)
    key.owner = user

    sub = Subscription(
        id=uuid.uuid4(),
        vpn_key_id=key_id,
        plan_id=uuid.uuid4(),
        starts_at=now,
        expires_at=now + timedelta(days=30),
        status=SubscriptionStatus.ACTIVE,
    )
    key.current_subscription = sub

    version = VPNKeyVersion(
        id=uuid.uuid4(),
        vpn_key_id=key_id,
        version=1,
        threexui_client_uuid='old-client',
        inbound_id=1,
        email_remark='@someusername_k111_v1',
        connection_uri='https://panel.example/sub/old',
        is_active=True,
    )
    key.versions = [version]

    return user, key, sub, version


@pytest.mark.asyncio
async def test_rotate_revoke_old_client_before_create() -> None:
    fake_client = FakePanelClient()
    service = ThreeXUIService(client=fake_client)  # type: ignore[arg-type]
    user, key, sub, version = make_user_key_version()

    created = await service.rotate_vpn_client(
        user=user,
        key=key,
        subscription=sub,
        current_version=version,
        new_version_number=2,
    )

    assert fake_client.deleted_client_uuid == 'old-client'
    assert fake_client.created_calls == 1
    assert created.connection_uri is not None
    assert created.email_remark.startswith('@someusername')


@pytest.mark.asyncio
async def test_rotate_fails_if_old_client_cannot_be_removed() -> None:
    fake_client = FakePanelClient()
    fake_client.raise_on_delete = True
    service = ThreeXUIService(client=fake_client)  # type: ignore[arg-type]
    user, key, sub, version = make_user_key_version()

    with pytest.raises(RuntimeError):
        await service.rotate_vpn_client(
            user=user,
            key=key,
            subscription=sub,
            current_version=version,
            new_version_number=2,
        )

    assert fake_client.created_calls == 0


@pytest.mark.asyncio
async def test_sync_marks_missing_panel_client_as_revoked() -> None:
    fake_client = FakePanelClient()
    service = ThreeXUIService(client=fake_client)  # type: ignore[arg-type]
    _, key, _, version = make_user_key_version()

    changed = await service.sync_key_with_panel_state(key)

    assert changed is True
    assert version.is_active is False
    assert key.status == VPNKeyStatus.REVOKED
    assert key.current_subscription is not None
    assert key.current_subscription.status == SubscriptionStatus.REVOKED


class SnapshotClient(ThreeXUIClient):
    def __init__(self) -> None:
        self.settings = SimpleNamespace(
            threexui_public_base_url='https://panel.example',
            threexui_base_url='https://panel.example',
        )
        self.base_url = 'https://panel.example'

    async def get_inbound_data(self, inbound_id: int):
        return {
            'id': inbound_id,
            'protocol': 'vless',
            'port': 443,
            'settings': json.dumps(
                {
                    'clients': [
                        {
                            'id': 'client-uuid',
                            'email': '@someusername_k111_v1',
                            'subId': 'sub-token-123',
                        }
                    ]
                }
            ),
        }

    async def get_inbounds_raw(self):
        return [await self.get_inbound_data(1)]

    async def get_client_info(self, client_uuid: str):
        return None


@pytest.mark.asyncio
async def test_connection_uri_is_built_from_panel_sub_id() -> None:
    client = SnapshotClient()
    snapshot = await client.get_client_snapshot(
        inbound_id=1,
        client_uuid='client-uuid',
        email_remark='@someusername_k111_v1',
    )

    assert snapshot is not None
    assert snapshot.sub_id == 'sub-token-123'
    assert snapshot.connection_uri == 'https://panel.example/sub/sub-token-123'

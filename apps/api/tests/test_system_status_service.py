from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi import HTTPException

from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.services.system_service import SystemStatusService


class FakeSetting:
    def __init__(self, value: str | None = None) -> None:
        self.value = value
        self.updated_at = datetime.now(timezone.utc)


class FakeSettingsRepo:
    def __init__(self) -> None:
        self.store: dict[str, FakeSetting] = {}

    async def get(self, key: str):
        return self.store.get(key)

    async def set(self, key: str, value: str) -> None:
        self.store[key] = FakeSetting(value)


class FakeSession:
    async def flush(self) -> None:
        return None


def make_user(telegram_user_id: int) -> User:
    user_id = uuid4()
    user = User(id=user_id, referral_code='refcode01', bonus_days_balance=0)
    user.telegram_account = TelegramAccount(
        user_id=user_id,
        telegram_user_id=telegram_user_id,
        username='tester',
        first_name='Test',
        last_name=None,
        language_code='ru',
        is_bot=False,
    )
    return user


@pytest.mark.asyncio
async def test_system_status_roundtrip_and_maintenance_block() -> None:
    service = SystemStatusService(FakeSession())  # type: ignore[arg-type]
    service.repo = FakeSettingsRepo()
    service.settings.telegram_admin_id = 777

    await service.set_status(
        status_value='maintenance',
        message='Технические работы',
        maintenance_mode=True,
        show_to_all=True,
        scheduled_for=None,
    )

    state = await service.get_status()
    assert state.status == 'maintenance'
    assert state.message == 'Технические работы'
    assert state.maintenance_mode is True
    assert state.show_to_all is True

    with pytest.raises(HTTPException) as exc:
        await service.ensure_user_operation_allowed(make_user(111))

    assert exc.value.status_code == 503

    await service.ensure_user_operation_allowed(make_user(777))

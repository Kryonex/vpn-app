import uuid

import pytest

from app.models.telegram_account import TelegramAccount
from app.services.support_service import SupportService


class FakeSession:
    def __init__(self, account: TelegramAccount | None) -> None:
        self._account = account

    async def scalar(self, _statement):
        return self._account


@pytest.mark.asyncio
async def test_support_service_returns_username_link() -> None:
    account = TelegramAccount(
        user_id=uuid.uuid4(),
        telegram_user_id=123456,
        username='adminname',
        first_name='Admin',
        last_name=None,
        language_code='ru',
        is_bot=False,
    )
    service = SupportService(FakeSession(account))
    service.settings.telegram_admin_id = 123456

    data = await service.get_support_contact()

    assert data.display_tag == '@adminname'
    assert data.telegram_link == 'https://t.me/adminname'


@pytest.mark.asyncio
async def test_support_service_returns_fallback_without_username() -> None:
    service = SupportService(FakeSession(None))
    service.settings.telegram_admin_id = 987654

    data = await service.get_support_contact()

    assert data.display_tag == 'tg_987654'
    assert data.telegram_link == 'tg://user?id=987654'

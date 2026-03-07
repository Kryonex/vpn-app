import uuid

import pytest
from fastapi.security import HTTPAuthorizationCredentials

from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.routers.me import me


class FakeSession:
    def __init__(self, user: User) -> None:
        self.user = user
        self.calls = 0

    async def scalar(self, statement):
        self.calls += 1

        # 1st call is from get_current_user() user lookup.
        if self.calls == 1:
            options = getattr(statement, '_with_options', ())
            assert options, 'Expected eager-loading options for User lookup'
            assert any('telegram_account' in repr(opt) for opt in options), (
                'User.telegram_account must be eagerly loaded to avoid MissingGreenlet in /me'
            )
            return self.user

        # 2nd, 3rd, 4th calls are from /me aggregate queries.
        if self.calls in (2, 3):
            return 0
        if self.calls == 4:
            return None

        return None


@pytest.mark.asyncio
async def test_me_flow_uses_eager_loaded_telegram_account() -> None:
    user_id = uuid.uuid4()
    user = User(id=user_id, referral_code='refcode01', bonus_days_balance=0)
    user.telegram_account = TelegramAccount(
        user_id=user_id,
        telegram_user_id=123456,
        username='tester',
        first_name='Test',
        last_name='User',
        language_code='en',
        is_bot=False,
    )

    token = create_access_token(str(user_id))
    credentials = HTTPAuthorizationCredentials(scheme='Bearer', credentials=token)

    session = FakeSession(user)
    current_user = await get_current_user(credentials=credentials, session=session)

    response = await me(current_user=current_user, session=session)

    assert response.id == user_id
    assert response.telegram is not None
    assert response.telegram.telegram_user_id == 123456

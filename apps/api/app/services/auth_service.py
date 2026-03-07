from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, validate_telegram_init_data
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.referral_service import ReferralService


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.user_repo = UserRepository(session)
        self.referral_service = ReferralService(session)

    async def authenticate_telegram(self, init_data: str, bot_token: str) -> tuple[User, str]:
        validated = validate_telegram_init_data(init_data, bot_token)
        tg_user = validated['user']

        telegram_user_id = int(tg_user['id'])
        user = await self.user_repo.get_by_telegram_id(telegram_user_id)
        if not user:
            user = await self.user_repo.create_user()

        await self.user_repo.upsert_telegram_account(
            user=user,
            telegram_user_id=telegram_user_id,
            username=tg_user.get('username'),
            first_name=tg_user.get('first_name'),
            last_name=tg_user.get('last_name'),
            language_code=tg_user.get('language_code'),
            is_bot=bool(tg_user.get('is_bot', False)),
        )

        await self.referral_service.link_referred_user(user, validated.get('start_param'))

        await self.session.commit()
        await self.session.refresh(user)

        token = create_access_token(str(user.id))
        return user, token

    async def upsert_from_bot_start(
        self,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        referral_code: str | None,
    ) -> User:
        user = await self.user_repo.get_by_telegram_id(telegram_user_id)
        if not user:
            user = await self.user_repo.create_user()

        await self.user_repo.upsert_telegram_account(
            user=user,
            telegram_user_id=telegram_user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            is_bot=False,
        )
        await self.referral_service.link_referred_user(user, referral_code)

        await self.session.commit()
        await self.session.refresh(user)
        return user


from __future__ import annotations

import secrets
import string
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.referral import Referral
from app.models.telegram_account import TelegramAccount
from app.models.user import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_id(self, user_id: UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .options(selectinload(User.telegram_account), selectinload(User.vpn_keys))
        )
        return await self.session.scalar(stmt)

    async def get_by_telegram_id(self, telegram_user_id: int) -> User | None:
        stmt = (
            select(User)
            .join(TelegramAccount, TelegramAccount.user_id == User.id)
            .where(TelegramAccount.telegram_user_id == telegram_user_id)
            .options(selectinload(User.telegram_account))
        )
        return await self.session.scalar(stmt)

    async def get_by_telegram_username(self, username: str) -> User | None:
        normalized = username.lstrip('@').strip().lower()
        if not normalized:
            return None
        stmt = (
            select(User)
            .join(TelegramAccount, TelegramAccount.user_id == User.id)
            .where(func.lower(TelegramAccount.username) == normalized)
            .options(selectinload(User.telegram_account))
        )
        return await self.session.scalar(stmt)

    async def get_by_referral_code(self, code: str) -> User | None:
        stmt = select(User).where(func.lower(User.referral_code) == code.lower())
        return await self.session.scalar(stmt)

    async def ensure_unique_referral_code(self) -> str:
        alphabet = string.ascii_lowercase + string.digits
        while True:
            candidate = ''.join(secrets.choice(alphabet) for _ in range(8))
            exists = await self.session.scalar(select(User.id).where(User.referral_code == candidate))
            if not exists:
                return candidate

    async def create_user(self) -> User:
        user = User(referral_code=await self.ensure_unique_referral_code())
        self.session.add(user)
        await self.session.flush()
        return user

    async def upsert_telegram_account(
        self,
        user: User,
        telegram_user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        is_bot: bool,
    ) -> TelegramAccount:
        account = await self.session.scalar(select(TelegramAccount).where(TelegramAccount.user_id == user.id))
        if not account:
            account = TelegramAccount(
                user_id=user.id,
                telegram_user_id=telegram_user_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                is_bot=is_bot,
            )
            self.session.add(account)
        else:
            account.telegram_user_id = telegram_user_id
            account.username = username
            account.first_name = first_name
            account.last_name = last_name
            account.language_code = language_code
            account.is_bot = is_bot

        await self.session.flush()
        return account

    async def list_users(self, limit: int = 100, offset: int = 0) -> Sequence[User]:
        stmt = select(User).order_by(User.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.scalars(stmt)
        return result.all()


from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.telegram_account import TelegramAccount
from app.schemas.support import SupportContactOut


class SupportService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()

    async def get_support_contact(self) -> SupportContactOut:
        admin_telegram_id = self.settings.telegram_admin_id
        if not admin_telegram_id:
            return SupportContactOut(
                telegram_admin_id=None,
                username=None,
                display_tag='Support unavailable',
                telegram_link=None,
            )

        account = await self.session.scalar(
            select(TelegramAccount).where(TelegramAccount.telegram_user_id == admin_telegram_id)
        )

        if account and account.username:
            username = account.username.lstrip('@')
            return SupportContactOut(
                telegram_admin_id=admin_telegram_id,
                username=username,
                display_tag=f'@{username}',
                telegram_link=f'https://t.me/{username}',
            )

        return SupportContactOut(
            telegram_admin_id=admin_telegram_id,
            username=None,
            display_tag=f'tg_{admin_telegram_id}',
            telegram_link=f'tg://user?id={admin_telegram_id}',
        )

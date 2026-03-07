from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.app_setting import AppSetting


class AppSettingsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, key: str) -> AppSetting | None:
        return await self.session.scalar(select(AppSetting).where(AppSetting.key == key))

    async def set(self, key: str, value: str) -> AppSetting:
        setting = await self.get(key)
        if setting:
            setting.value = value
            await self.session.flush()
            return setting

        setting = AppSetting(key=key, value=value)
        self.session.add(setting)
        await self.session.flush()
        return setting

from __future__ import annotations

import asyncio
from decimal import Decimal

from sqlalchemy import select

from app.core.config import get_settings
from app.models.app_setting import AppSetting
from app.db.session import SessionLocal
from app.models.plan import Plan

DEFAULT_PLANS = [
    {'name': '1 month', 'duration_days': 30, 'price': Decimal('299.00'), 'currency': 'RUB', 'sort_order': 10},
    {'name': '3 months', 'duration_days': 90, 'price': Decimal('799.00'), 'currency': 'RUB', 'sort_order': 20},
    {'name': '6 months', 'duration_days': 180, 'price': Decimal('1499.00'), 'currency': 'RUB', 'sort_order': 30},
    {'name': '12 months', 'duration_days': 365, 'price': Decimal('2499.00'), 'currency': 'RUB', 'sort_order': 40},
]


async def seed() -> None:
    settings = get_settings()
    async with SessionLocal() as session:
        for plan_data in DEFAULT_PLANS:
            existing = await session.scalar(select(Plan).where(Plan.name == plan_data['name']))
            if existing:
                continue
            session.add(Plan(**plan_data, is_active=True))

        referral_setting = await session.scalar(
            select(AppSetting).where(AppSetting.key == 'referral_bonus_days')
        )
        if not referral_setting:
            session.add(
                AppSetting(
                    key='referral_bonus_days',
                    value=str(settings.referral_bonus_days),
                )
            )

        await session.commit()


if __name__ == '__main__':
    asyncio.run(seed())

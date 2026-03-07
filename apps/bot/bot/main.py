from __future__ import annotations

import asyncio
import json
import logging

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

from app.core.config import get_settings
from app.core.redis import close_redis, get_redis
from app.db.session import SessionLocal
from app.services.auth_service import AuthService

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

settings = get_settings()


def extract_referral_code(message: Message) -> str | None:
    text = (message.text or '').strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    start_arg = parts[1].strip()
    if start_arg.startswith('ref_'):
        return start_arg[4:]
    return start_arg


def mini_app_keyboard() -> InlineKeyboardMarkup | None:
    if not settings.mini_app_url:
        return None

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Open VPN App',
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ]
        ]
    )


async def start_handler(message: Message) -> None:
    referral_code = extract_referral_code(message)
    if not message.from_user:
        return

    async with SessionLocal() as session:
        service = AuthService(session)
        await service.upsert_from_bot_start(
            telegram_user_id=message.from_user.id,
            username=message.from_user.username,
            first_name=message.from_user.first_name,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
            referral_code=referral_code,
        )

    text = (
        'VPN service is ready.\n\n'
        'Open Mini App to buy or renew subscription, manage keys and view payments.'
    )
    await message.answer(text, reply_markup=mini_app_keyboard())


async def notification_worker(bot: Bot, stop_event: asyncio.Event) -> None:
    redis = await get_redis()
    queue_key = settings.notification_queue_key

    while not stop_event.is_set():
        try:
            item = await redis.brpop(queue_key, timeout=5)
            if not item:
                continue

            _, raw_payload = item
            payload = json.loads(raw_payload)
            telegram_user_id = payload.get('telegram_user_id')
            text = payload.get('text')
            if telegram_user_id and text:
                await bot.send_message(chat_id=int(telegram_user_id), text=str(text))
        except Exception as exc:  # noqa: BLE001
            logger.exception('Notification worker error: %s', exc)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError(
            'BOT_TOKEN is not configured. Set BOT_TOKEN in environment variables or in .env before starting bot.'
        )
    if not settings.mini_app_url:
        logger.warning('MINI_APP_URL is not configured. /start will work without WebApp button.')

    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.message.register(start_handler, CommandStart())

    stop_event = asyncio.Event()
    notify_task = asyncio.create_task(notification_worker(bot, stop_event))

    try:
        await dp.start_polling(bot)
    finally:
        stop_event.set()
        await notify_task
        await bot.session.close()
        await close_redis()


if __name__ == '__main__':
    asyncio.run(main())

from __future__ import annotations

import asyncio
import base64
import json
import logging
from urllib.parse import urljoin

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

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

    info_url = urljoin(settings.mini_app_url.rstrip('/') + '/', 'info.html')
    ticket_url = urljoin(settings.mini_app_url.rstrip('/') + '/', 'contact.html')

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text='Открыть ZERO',
                    web_app=WebAppInfo(url=settings.mini_app_url),
                )
            ],
            [
                InlineKeyboardButton(
                    text='Информация',
                    url=info_url,
                ),
                InlineKeyboardButton(
                    text='Создать тикет',
                    url=ticket_url,
                ),
            ],
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

    first_name = message.from_user.first_name.strip() if message.from_user.first_name else 'друг'
    text = (
        f'Здравствуйте, {first_name}.\n\n'
        'ZERO уже готов к работе.\n'
        'В мини-приложении можно подключить ускорение, продлить доступ, открыть свои конфигурации и проверить заявки.\n'
        'Если нужен ответ от поддержки, воспользуйтесь кнопкой создания тикета.\n\n'
        'Нажмите кнопку ниже, чтобы перейти в ZERO.'
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
            image_data_url = payload.get('image_data_url')
            image_filename = payload.get('image_filename') or 'image.jpg'
            button_url = payload.get('button_url')
            button_text = payload.get('button_text') or 'Открыть'
            if not telegram_user_id or (not text and not image_data_url):
                logger.warning('Notification worker received malformed payload for queue %s', queue_key)
                continue

            logger.info('Notification worker dequeued message for telegram_user_id=%s', telegram_user_id)
            reply_markup = None
            if button_url:
                reply_markup = InlineKeyboardMarkup(
                    inline_keyboard=[
                        [InlineKeyboardButton(text=str(button_text), url=str(button_url))]
                    ]
                )
            if image_data_url:
                try:
                    _, encoded = str(image_data_url).split(',', 1)
                    image_bytes = base64.b64decode(encoded)
                except Exception:  # noqa: BLE001
                    logger.warning('Notification worker received invalid image payload for telegram_user_id=%s', telegram_user_id)
                    continue

                await bot.send_photo(
                    chat_id=int(telegram_user_id),
                    photo=BufferedInputFile(image_bytes, filename=str(image_filename)),
                    caption=str(text) if text else None,
                    reply_markup=reply_markup,
                )
            else:
                await bot.send_message(chat_id=int(telegram_user_id), text=str(text), reply_markup=reply_markup)
            logger.info('Notification worker sent message for telegram_user_id=%s', telegram_user_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception('Notification worker error: %s', exc)


async def main() -> None:
    if not settings.bot_token:
        raise RuntimeError(
            'BOT_TOKEN не задан. Укажите BOT_TOKEN в переменных окружения или в .env перед запуском бота.'
        )
    if not settings.mini_app_url:
        logger.warning('MINI_APP_URL не задан. Команда /start будет работать без кнопки WebApp.')

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

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from app.core.config import get_settings


class NotificationService:
    def __init__(self, redis: Redis) -> None:
        self.redis = redis
        self.settings = get_settings()

    async def enqueue_telegram_notification(self, telegram_user_id: int, text: str) -> None:
        payload = json.dumps({'telegram_user_id': telegram_user_id, 'text': text}, ensure_ascii=False)
        await self.redis.lpush(self.settings.notification_queue_key, payload)

    async def enqueue_raw(self, payload: dict[str, Any]) -> None:
        await self.redis.lpush(self.settings.notification_queue_key, json.dumps(payload, ensure_ascii=False))


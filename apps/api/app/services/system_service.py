from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.telegram_account import TelegramAccount
from app.models.user import User
from app.models.vpn_key import VPNKey
from app.models.enums import VPNKeyStatus
from app.repositories.app_settings_repository import AppSettingsRepository


@dataclass(slots=True)
class SystemStatusState:
    status: str = 'online'
    message: str | None = None
    maintenance_mode: bool = False
    show_to_all: bool = False
    scheduled_for: datetime | None = None
    updated_at: datetime | None = None


class SystemStatusService:
    STATUS_KEY = 'system_status'
    TELEGRAM_PROXY_URL_KEY = 'telegram_proxy_url'
    TELEGRAM_PROXY_BUTTON_TEXT_KEY = 'telegram_proxy_button_text'
    NEWS_KEY = 'system_news'
    PAYMENTS_ENABLED_KEY = 'payments_enabled'

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings = get_settings()
        self.repo = AppSettingsRepository(session)

    async def get_status(self) -> SystemStatusState:
        setting = await self.repo.get(self.STATUS_KEY)
        if not setting:
            return SystemStatusState()

        try:
            payload = json.loads(setting.value)
        except json.JSONDecodeError:
            return SystemStatusState(updated_at=setting.updated_at)

        scheduled_for = payload.get('scheduled_for')
        updated_at = payload.get('updated_at')
        return SystemStatusState(
            status=str(payload.get('status') or 'online'),
            message=payload.get('message'),
            maintenance_mode=bool(payload.get('maintenance_mode', False)),
            show_to_all=bool(payload.get('show_to_all', False)),
            scheduled_for=datetime.fromisoformat(scheduled_for) if scheduled_for else None,
            updated_at=datetime.fromisoformat(updated_at) if updated_at else setting.updated_at,
        )

    async def set_status(
        self,
        *,
        status_value: str,
        message: str | None,
        maintenance_mode: bool,
        show_to_all: bool,
        scheduled_for: datetime | None,
    ) -> SystemStatusState:
        now = datetime.now(timezone.utc)
        state = SystemStatusState(
            status=status_value,
            message=message.strip() if message else None,
            maintenance_mode=maintenance_mode,
            show_to_all=show_to_all,
            scheduled_for=scheduled_for,
            updated_at=now,
        )
        payload = asdict(state)
        payload['scheduled_for'] = scheduled_for.isoformat() if scheduled_for else None
        payload['updated_at'] = now.isoformat()
        await self.repo.set(self.STATUS_KEY, json.dumps(payload, ensure_ascii=False))
        await self.session.flush()
        return state

    async def get_payment_settings(self) -> dict[str, object]:
        setting = await self.repo.get(self.PAYMENTS_ENABLED_KEY)
        enabled = True
        if setting and setting.value.strip():
            enabled = setting.value.strip().lower() not in {'0', 'false', 'off', 'disabled'}
        return {
            'enabled': enabled,
            'mode': 'direct' if enabled else 'admin_contact',
        }

    async def set_payment_settings(self, *, enabled: bool) -> dict[str, object]:
        await self.repo.set(self.PAYMENTS_ENABLED_KEY, 'true' if enabled else 'false')
        await self.session.flush()
        return await self.get_payment_settings()

    async def payments_enabled(self) -> bool:
        data = await self.get_payment_settings()
        return bool(data['enabled'])

    async def get_user_telegram_proxy(self, user: User) -> dict[str, object]:
        active_keys_count = int(
            (
                await self.session.scalar(
                    select(func.count(VPNKey.id)).where(
                        VPNKey.owner_id == user.id,
                        VPNKey.status == VPNKeyStatus.ACTIVE,
                    )
                )
            )
            or 0
        )
        if active_keys_count <= 0:
            return {'enabled': False, 'proxy_url': None, 'button_text': 'Подключить прокси'}

        proxy_url_setting = await self.repo.get(self.TELEGRAM_PROXY_URL_KEY)
        button_text_setting = await self.repo.get(self.TELEGRAM_PROXY_BUTTON_TEXT_KEY)
        proxy_url = proxy_url_setting.value.strip() if proxy_url_setting and proxy_url_setting.value.strip() else None
        button_text = (
            button_text_setting.value.strip()
            if button_text_setting and button_text_setting.value.strip()
            else 'Подключить прокси'
        )
        return {
            'enabled': bool(proxy_url),
            'proxy_url': proxy_url,
            'button_text': button_text,
        }

    async def get_news(self) -> list[dict[str, object]]:
        setting = await self.repo.get(self.NEWS_KEY)
        if not setting or not setting.value.strip():
            return []
        try:
            raw_items = json.loads(setting.value)
        except json.JSONDecodeError:
            return []
        items: list[dict[str, object]] = []
        for item in raw_items:
            created_at_raw = item.get('created_at')
            created_at = (
                datetime.fromisoformat(created_at_raw)
                if isinstance(created_at_raw, str) and created_at_raw
                else datetime.now(timezone.utc)
            )
            items.append(
                {
                    'id': str(item.get('id') or uuid.uuid4()),
                    'title': str(item.get('title') or 'Новость'),
                    'body': str(item.get('body') or ''),
                    'image_data_url': item.get('image_data_url'),
                    'created_at': created_at,
                }
            )
        return items

    async def publish_news(
        self,
        *,
        title: str | None,
        body: str,
        image_data_url: str | None = None,
    ) -> str:
        normalized_body = body.strip()
        if not normalized_body and not (image_data_url or '').strip():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='News text or image is required')

        derived_title = (title or '').strip() or normalized_body.splitlines()[0][:80] or 'Новость'
        items = await self.get_news()
        news_id = str(uuid.uuid4())
        items.insert(
            0,
            {
                'id': news_id,
                'title': derived_title,
                'body': normalized_body,
                'image_data_url': (image_data_url or '').strip() or None,
                'created_at': datetime.now(timezone.utc),
            },
        )
        serialized_items = [
            {
                **item,
                'created_at': item['created_at'].isoformat() if isinstance(item.get('created_at'), datetime) else item.get('created_at'),
            }
            for item in items[:12]
        ]
        await self.repo.set(self.NEWS_KEY, json.dumps(serialized_items, ensure_ascii=False))
        await self.session.flush()
        return news_id

    async def ensure_user_operation_allowed(self, user: User) -> None:
        state = await self.get_status()
        if not state.maintenance_mode:
            return
        if self.is_admin_user(user):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=state.message or 'Сервис временно находится на техническом обслуживании.',
        )

    def is_admin_user(self, user: User) -> bool:
        admin_id = self.settings.telegram_admin_id
        account = user.telegram_account
        return bool(admin_id and account and account.telegram_user_id == admin_id)

    async def send_admin_message(
        self,
        *,
        actor_id: str | None,
        message: str,
        send_to_all: bool,
        force: bool,
        user_id: UUID | None = None,
        image_data_url: str | None = None,
        image_filename: str | None = None,
        enqueue_fn,
    ) -> tuple[int, bool, str]:
        normalized = message.strip()
        normalized_image = (image_data_url or '').strip() or None
        if not normalized and not normalized_image:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Message text or image is required')
        if send_to_all and user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Use either send_to_all or user_id')
        if not send_to_all and not user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Target user is required')

        if send_to_all:
            target_users = (
                await self.session.scalars(
                    select(User)
                    .join(TelegramAccount, TelegramAccount.user_id == User.id)
                    .options(selectinload(User.telegram_account))
                )
            ).all()
        else:
            target = await self.session.scalar(
                select(User)
                .where(User.id == user_id)
                .join(TelegramAccount, TelegramAccount.user_id == User.id)
                .options(selectinload(User.telegram_account))
            )
            if not target:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='User not found')
            target_users = [target]

        message_hash = hashlib.sha256(
            f'{normalized}|{normalized_image or ""}|{send_to_all}|{user_id or ""}'.encode('utf-8')
        ).hexdigest()
        duplicate_blocked = False
        if not force:
            recent_cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
            recent = await self.session.scalar(
                select(AuditLog)
                .where(
                    AuditLog.action == 'admin_message_sent',
                    AuditLog.created_at >= recent_cutoff,
                )
                .order_by(desc(AuditLog.created_at))
            )
            if recent and (recent.metadata_json or {}).get('message_hash') == message_hash:
                duplicate_blocked = True
                return 0, duplicate_blocked, str(recent.id)

        sent_count = 0
        for target in target_users:
            account = target.telegram_account
            if not account:
                continue
            await enqueue_fn(
                account.telegram_user_id,
                normalized,
                image_data_url=normalized_image,
                image_filename=image_filename,
            )
            sent_count += 1

        audit = AuditLog(
            actor_type='admin',
            actor_id=actor_id,
            action='admin_message_sent',
            entity_type='broadcast' if send_to_all else 'user',
            entity_id='all' if send_to_all else str(user_id),
            metadata_json={
                'message_hash': message_hash,
                'message_preview': normalized[:120],
                'has_image': bool(normalized_image),
                'target_count': sent_count,
                'send_to_all': send_to_all,
            },
        )
        self.session.add(audit)
        await self.session.flush()
        return sent_count, duplicate_blocked, str(audit.id)

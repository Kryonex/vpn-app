from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.audit_log import AuditLog
from app.models.telegram_account import TelegramAccount
from app.schemas.support import SupportContactOut, SupportTicketCreateRequest, SupportTicketCreateResponse


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

    async def create_public_ticket(
        self,
        payload: SupportTicketCreateRequest,
        *,
        enqueue_notification=None,
    ) -> SupportTicketCreateResponse:
        normalized_email = payload.email.strip().lower()
        if '@' not in normalized_email or '.' not in normalized_email.split('@', 1)[-1]:
            raise ValueError('Укажите корректный email для обратной связи.')

        ticket_id = uuid.uuid4()
        ticket = AuditLog(
            actor_type='public',
            actor_id=normalized_email,
            action='support_ticket_created',
            entity_type='support_ticket',
            entity_id=str(ticket_id),
            metadata_json={
                'name': payload.name.strip(),
                'email': normalized_email,
                'telegram_username': (payload.telegram_username or '').strip().lstrip('@') or None,
                'subject': payload.subject.strip(),
                'message': payload.message.strip(),
            },
        )
        self.session.add(ticket)
        await self.session.commit()

        if enqueue_notification and self.settings.telegram_admin_id:
            telegram_line = (
                f"Telegram: @{payload.telegram_username.strip().lstrip('@')}\n"
                if (payload.telegram_username or '').strip()
                else ''
            )
            await enqueue_notification(
                self.settings.telegram_admin_id,
                (
                    'Новый тикет поддержки ZERO\n\n'
                    f'Тикет: {ticket_id}\n'
                    f'Имя: {payload.name.strip()}\n'
                    f'Email: {normalized_email}\n'
                    f'{telegram_line}'
                    f'Тема: {payload.subject.strip()}\n\n'
                    f'{payload.message.strip()}'
                ),
            )

        return SupportTicketCreateResponse(
            ok=True,
            ticket_id=ticket_id,
            message='Обращение отправлено. Ответ придёт на указанный email.',
        )

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User
from app.repositories.app_settings_repository import AppSettingsRepository
from app.repositories.user_repository import UserRepository


class WebAccessService:
    USER_KEY_PREFIX = 'web_access:'
    INDEX_KEY_PREFIX = 'web_access:index:'
    LOGIN_ALPHABET = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.settings_repo = AppSettingsRepository(session)
        self.user_repo = UserRepository(session)

    async def get_status(self, user: User) -> dict[str, Any]:
        record = await self._ensure_record(user.id)
        await self.session.commit()
        return {
            'login_id': record['login_id'],
            'has_password': bool(record.get('password_hash')),
            'updated_at': record.get('updated_at'),
        }

    async def set_password(
        self,
        user: User,
        password: str,
        regenerate_login_id: bool = False,
    ) -> dict[str, Any]:
        normalized_password = password.strip()
        if len(normalized_password) < 8:
            raise ValueError('Пароль для сайта должен содержать не менее 8 символов.')

        record = await self._ensure_record(user.id)
        old_login_id = str(record['login_id'])
        login_id = await self._generate_login_id() if regenerate_login_id else old_login_id

        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(normalized_password, salt)
        updated_at = datetime.now(timezone.utc).isoformat()

        record.update(
            {
                'login_id': login_id,
                'salt': base64.urlsafe_b64encode(salt).decode('ascii'),
                'password_hash': password_hash,
                'updated_at': updated_at,
            }
        )

        await self.settings_repo.set(self._index_key(login_id), str(user.id))

        await self.settings_repo.set(self._user_key(user.id), json.dumps(record, ensure_ascii=False))
        await self.session.commit()

        return {
            'login_id': login_id,
            'has_password': True,
            'updated_at': updated_at,
        }

    async def authenticate(self, login_id: str, password: str) -> User | None:
        normalized_login_id = self._normalize_login_id(login_id)
        if not normalized_login_id or not password:
            return None

        index = await self.settings_repo.get(self._index_key(normalized_login_id))
        if not index:
            return None

        try:
            user_id = UUID(index.value)
        except ValueError:
            return None

        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return None

        record = await self._load_record(user.id)
        if not record or not record.get('password_hash') or not record.get('salt'):
            return None
        if self._normalize_login_id(str(record.get('login_id', ''))) != normalized_login_id:
            return None

        salt = base64.urlsafe_b64decode(str(record['salt']).encode('ascii'))
        expected_hash = str(record['password_hash'])
        provided_hash = self._hash_password(password, salt)
        if not hmac.compare_digest(expected_hash, provided_hash):
            return None

        return user

    async def ensure_bot_credentials(self, user: User) -> dict[str, Any]:
        record = await self._ensure_record(user.id)
        temporary_password: str | None = None

        if not record.get('password_hash'):
            temporary_password = self._generate_temporary_password()
            salt = secrets.token_bytes(16)
            record['salt'] = base64.urlsafe_b64encode(salt).decode('ascii')
            record['password_hash'] = self._hash_password(temporary_password, salt)
            record['updated_at'] = datetime.now(timezone.utc).isoformat()
            await self.settings_repo.set(self._user_key(user.id), json.dumps(record, ensure_ascii=False))
            await self.settings_repo.set(self._index_key(str(record['login_id'])), str(user.id))
            await self.session.commit()

        return {
            'login_id': str(record['login_id']),
            'temporary_password': temporary_password,
            'has_password': bool(record.get('password_hash')),
        }

    async def _load_record(self, user_id: UUID) -> dict[str, Any] | None:
        setting = await self.settings_repo.get(self._user_key(user_id))
        if not setting:
            return None
        try:
            data = json.loads(setting.value)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, dict):
            return None
        return data

    async def _ensure_record(self, user_id: UUID) -> dict[str, Any]:
        record = await self._load_record(user_id)
        if record and record.get('login_id'):
            await self.settings_repo.set(self._index_key(str(record['login_id'])), str(user_id))
            return record

        login_id = await self._generate_login_id()
        record = {
            'login_id': login_id,
            'salt': None,
            'password_hash': None,
            'updated_at': None,
        }
        await self.settings_repo.set(self._user_key(user_id), json.dumps(record, ensure_ascii=False))
        await self.settings_repo.set(self._index_key(login_id), str(user_id))
        await self.session.flush()
        return record

    async def _generate_login_id(self) -> str:
        while True:
            suffix = ''.join(secrets.choice(self.LOGIN_ALPHABET) for _ in range(6))
            login_id = f'ZERO{suffix}'
            if not await self.settings_repo.get(self._index_key(login_id)):
                return login_id

    @staticmethod
    def _normalize_login_id(login_id: str) -> str:
        return ''.join(ch for ch in login_id.upper().strip() if ch.isalnum())

    @staticmethod
    def _generate_temporary_password() -> str:
        alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
        return ''.join(secrets.choice(alphabet) for _ in range(10))

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> str:
        digest = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 150_000)
        return base64.urlsafe_b64encode(digest).decode('ascii')

    @classmethod
    def _user_key(cls, user_id: UUID) -> str:
        return f'{cls.USER_KEY_PREFIX}{user_id}'

    @classmethod
    def _index_key(cls, login_id: str) -> str:
        return f'{cls.INDEX_KEY_PREFIX}{cls._normalize_login_id(login_id)}'


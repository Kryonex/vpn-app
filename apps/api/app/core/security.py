import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings


class TelegramAuthError(ValueError):
    pass


def _build_data_check_string(init_data: str) -> tuple[str, str]:
    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    provided_hash = pairs.pop('hash', None)
    if not provided_hash:
        raise TelegramAuthError('Missing hash in initData')

    data_check_string = '\n'.join(f'{key}={value}' for key, value in sorted(pairs.items()))
    return data_check_string, provided_hash


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> dict[str, Any]:
    data_check_string, provided_hash = _build_data_check_string(init_data)
    secret = hashlib.sha256(bot_token.encode('utf-8')).digest()
    computed_hash = hmac.new(secret, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, provided_hash):
        raise TelegramAuthError('Invalid Telegram initData signature')

    payload = dict(parse_qsl(init_data, keep_blank_values=True))
    auth_date_raw = payload.get('auth_date')
    if not auth_date_raw:
        raise TelegramAuthError('Missing auth_date')

    auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_date > timedelta(seconds=max_age_seconds):
        raise TelegramAuthError('Telegram initData is too old')

    user_raw = payload.get('user')
    if not user_raw:
        raise TelegramAuthError('Missing user payload')

    user = json.loads(user_raw)
    start_param = payload.get('start_param') or payload.get('startapp')

    return {
        'user': user,
        'auth_date': auth_date,
        'query_id': payload.get('query_id'),
        'start_param': start_param,
        'raw': payload,
    }


def create_access_token(subject: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    exp = now + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        'sub': subject,
        'iat': int(now.timestamp()),
        'exp': int(exp.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc


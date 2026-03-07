import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import parse_qsl

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TelegramAuthError(ValueError):
    pass


def _parse_init_data(init_data: str) -> list[tuple[str, str]]:
    return parse_qsl(init_data, keep_blank_values=True, strict_parsing=False)


def _build_data_check_string(parsed_pairs: list[tuple[str, str]]) -> tuple[str, str, list[str]]:
    items: list[tuple[str, str]] = []
    provided_hash: str | None = None

    for key, value in parsed_pairs:
        if key == 'hash':
            provided_hash = value
            continue
        items.append((key, value))

    if not provided_hash:
        raise TelegramAuthError('Missing hash in initData')

    items.sort(key=lambda item: item[0])
    data_check_string = '\n'.join(f'{key}={value}' for key, value in items)
    keys_present = [key for key, _ in items]
    return data_check_string, provided_hash, keys_present


def validate_telegram_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> dict[str, Any]:
    bot_token_loaded = bool(bot_token and bot_token.strip())
    init_data_empty = not bool(init_data)

    if not bot_token_loaded:
        logger.warning('Telegram initData validation failed: BOT_TOKEN missing')
        raise TelegramAuthError('Server BOT_TOKEN is not configured')
    if init_data_empty:
        logger.warning('Telegram initData validation failed: initData is empty')
        raise TelegramAuthError('Empty initData')

    parsed_pairs = _parse_init_data(init_data)
    parsed_payload = dict(parsed_pairs)
    hash_exists = 'hash' in parsed_payload

    try:
        data_check_string, provided_hash, keys_present = _build_data_check_string(parsed_pairs)
    except TelegramAuthError:
        logger.warning(
            'Telegram initData validation failed: hash missing | bot_token_loaded=%s init_data_empty=%s hash_exists=%s keys=%s',
            bot_token_loaded,
            init_data_empty,
            hash_exists,
            sorted(parsed_payload.keys()),
        )
        raise

    # Telegram WebApp validation spec:
    # secret_key = HMAC_SHA256(key="WebAppData", message=BOT_TOKEN)
    secret_key = hmac.new(b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected_hash, provided_hash):
        logger.warning(
            'Telegram initData validation failed: signature mismatch | bot_token_loaded=%s init_data_empty=%s hash_exists=%s keys=%s',
            bot_token_loaded,
            init_data_empty,
            hash_exists,
            keys_present,
        )
        raise TelegramAuthError('Invalid Telegram initData signature')

    payload = parsed_payload
    auth_date_raw = payload.get('auth_date')
    if not auth_date_raw:
        logger.warning('Telegram initData validation failed: auth_date missing | keys=%s', sorted(payload.keys()))
        raise TelegramAuthError('Missing auth_date')

    auth_date = datetime.fromtimestamp(int(auth_date_raw), tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_date > timedelta(seconds=max_age_seconds):
        logger.warning('Telegram initData validation failed: auth_date expired | auth_date=%s', auth_date.isoformat())
        raise TelegramAuthError('Telegram initData is too old')

    user_raw = payload.get('user')
    if not user_raw:
        logger.warning('Telegram initData validation failed: user missing | keys=%s', sorted(payload.keys()))
        raise TelegramAuthError('Missing user payload')

    try:
        user = json.loads(user_raw)
    except json.JSONDecodeError as exc:
        logger.warning('Telegram initData validation failed: user JSON malformed')
        raise TelegramAuthError('Malformed user payload in initData') from exc

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


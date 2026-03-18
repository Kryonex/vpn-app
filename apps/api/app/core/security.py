import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import unquote

import jwt
from fastapi import HTTPException, status

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class TelegramAuthError(ValueError):
    pass


def _parse_init_data(init_data: str) -> list[tuple[str, str]]:
    # Important: parse manually and decode with unquote (not unquote_plus),
    # so '+' stays '+' and signed content remains intact.
    raw = init_data[1:] if init_data.startswith('?') else init_data
    if not raw:
        return []

    pairs: list[tuple[str, str]] = []
    for chunk in raw.split('&'):
        if not chunk:
            continue
        if '=' in chunk:
            key_raw, value_raw = chunk.split('=', 1)
        else:
            key_raw, value_raw = chunk, ''
        pairs.append((unquote(key_raw), unquote(value_raw)))
    return pairs


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


def validate_telegram_login_data(auth_data: dict[str, Any], bot_token: str, max_age_seconds: int = 86400) -> dict[str, Any]:
    if not bot_token or not bot_token.strip():
        logger.warning('Telegram login validation failed: BOT_TOKEN missing')
        raise TelegramAuthError('Server BOT_TOKEN is not configured')

    payload = {key: value for key, value in auth_data.items() if value is not None}
    provided_hash = str(payload.pop('hash', '')).strip()
    if not provided_hash:
        raise TelegramAuthError('Missing hash in Telegram login payload')

    auth_date_raw = payload.get('auth_date')
    if auth_date_raw in (None, ''):
        raise TelegramAuthError('Missing auth_date in Telegram login payload')

    try:
        auth_date_value = int(auth_date_raw)
    except (TypeError, ValueError) as exc:
        raise TelegramAuthError('Invalid auth_date in Telegram login payload') from exc

    auth_date = datetime.fromtimestamp(auth_date_value, tz=timezone.utc)
    if datetime.now(timezone.utc) - auth_date > timedelta(seconds=max_age_seconds):
        raise TelegramAuthError('Telegram login data is too old')

    data_check_string = '\n'.join(
        f'{key}={payload[key]}'
        for key in sorted(payload.keys())
        if payload[key] not in (None, '')
    )
    secret_key = hashlib.sha256(bot_token.encode('utf-8')).digest()
    expected_hash = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected_hash, provided_hash):
        raise TelegramAuthError('Invalid Telegram login signature')

    telegram_user_id = payload.get('id')
    if telegram_user_id in (None, ''):
        raise TelegramAuthError('Missing Telegram user id')

    return {
        'user': {
            'id': int(telegram_user_id),
            'username': payload.get('username'),
            'first_name': payload.get('first_name'),
            'last_name': payload.get('last_name'),
            'photo_url': payload.get('photo_url'),
        },
        'auth_date': auth_date,
        'raw': {**payload, 'hash': provided_hash},
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
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    logger.info('JWT issued | sub_present=%s exp_unix=%s', bool(subject), payload['exp'])
    return token


def decode_access_token(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        logger.info('JWT decoded | sub_present=%s', bool(payload.get('sub')))
        return payload
    except jwt.PyJWTError as exc:
        logger.warning('JWT decode failed: %s', type(exc).__name__)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail='Invalid token') from exc


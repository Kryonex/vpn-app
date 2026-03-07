import hashlib
import hmac
import json
from datetime import datetime, timezone
from urllib.parse import quote

import pytest

from app.core.security import TelegramAuthError, validate_telegram_init_data


def build_signed_init_data(payload: dict[str, str], bot_token: str, *, encode_plus: bool = True) -> str:
    data_check_string = '\n'.join(f'{k}={v}' for k, v in sorted(payload.items(), key=lambda item: item[0]))
    secret_key = hmac.new(b'WebAppData', bot_token.encode('utf-8'), hashlib.sha256).digest()
    signature = hmac.new(secret_key, data_check_string.encode('utf-8'), hashlib.sha256).hexdigest()

    parts = []
    for key, value in payload.items():
        key_encoded = quote(key, safe='')
        if encode_plus:
            value_encoded = quote(value, safe='')
        else:
            # Keep raw '+' to ensure parser does not convert it to space.
            value_encoded = value
        parts.append(f'{key_encoded}={value_encoded}')
    parts.append(f'hash={signature}')
    return '&'.join(parts)


def test_validate_telegram_init_data_success() -> None:
    bot_token = '123456:ABCDEF'
    user_json = json.dumps({'id': 42, 'first_name': 'Ivan', 'username': 'ivan'}, separators=(',', ':'))
    payload = {
        'auth_date': str(int(datetime.now(timezone.utc).timestamp())),
        'query_id': 'AAEAAAE',
        'start_param': 'ref_abc123',
        'user': user_json,
    }
    init_data = build_signed_init_data(payload, bot_token)

    validated = validate_telegram_init_data(init_data, bot_token)

    assert validated['user']['id'] == 42
    assert validated['start_param'] == 'ref_abc123'


def test_validate_telegram_init_data_plus_sign_preserved() -> None:
    bot_token = '123456:ABCDEF'
    user_json = json.dumps({'id': 77, 'first_name': 'Pavel'}, separators=(',', ':'))
    payload = {
        'auth_date': str(int(datetime.now(timezone.utc).timestamp())),
        'query_id': 'AAEAAAE',
        'start_param': 'ref+a+b',
        'user': user_json,
    }
    init_data = build_signed_init_data(payload, bot_token, encode_plus=False)

    validated = validate_telegram_init_data(init_data, bot_token)
    assert validated['start_param'] == 'ref+a+b'


def test_validate_telegram_init_data_invalid_signature() -> None:
    bot_token = '123456:ABCDEF'
    user_json = json.dumps({'id': 1}, separators=(',', ':'))
    payload = {
        'auth_date': str(int(datetime.now(timezone.utc).timestamp())),
        'query_id': 'AAEAAAE',
        'user': user_json,
    }
    init_data = build_signed_init_data(payload, bot_token) + '00'

    with pytest.raises(TelegramAuthError):
        validate_telegram_init_data(init_data, bot_token)

from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_env: str = Field(default='development', alias='APP_ENV')

    api_host: str = Field(default='0.0.0.0', alias='API_HOST')
    api_port: int = Field(default=8000, alias='API_PORT')

    bot_token: str = Field(default='', alias='BOT_TOKEN')
    bot_username: str = Field(default='', alias='BOT_USERNAME')
    mini_app_url: str = Field(default='', alias='MINI_APP_URL')

    jwt_secret: str = Field(default='change_me', alias='JWT_SECRET')
    jwt_algorithm: str = Field(default='HS256', alias='JWT_ALGORITHM')
    jwt_expire_minutes: int = Field(default=120, alias='JWT_EXPIRE_MINUTES')

    admin_bearer_token: str = Field(default='change_me_admin_token', alias='ADMIN_BEARER_TOKEN')
    telegram_admin_id: int | None = Field(default=None, alias='TELEGRAM_ADMIN_ID')
    payment_phone: str = Field(default='', alias='PAYMENT_PHONE')
    platega_base_url: str = Field(default='https://app.platega.io', alias='PLATEGA_BASE_URL')
    platega_merchant_id: str = Field(default='', alias='PLATEGA_MERCHANT_ID')
    platega_secret: str = Field(default='', alias='PLATEGA_SECRET')
    platega_payment_method: int = Field(default=2, alias='PLATEGA_PAYMENT_METHOD')

    database_url: str = Field(default='postgresql+asyncpg://vpn:vpn@postgres:5432/vpn', alias='DATABASE_URL')
    redis_url: str = Field(default='redis://redis:6379/0', alias='REDIS_URL')
    notification_queue_key: str = Field(default='notifications:telegram', alias='NOTIFICATION_QUEUE_KEY')

    cors_origins_raw: str = Field(default='http://localhost:15173', alias='CORS_ORIGINS')

    rate_limit_requests: int = Field(default=30, alias='RATE_LIMIT_REQUESTS')
    rate_limit_window_seconds: int = Field(default=60, alias='RATE_LIMIT_WINDOW_SECONDS')

    referral_bonus_days: int = Field(default=7, alias='REFERRAL_BONUS_DAYS')

    expiring_notify_days: int = Field(default=3, alias='EXPIRING_NOTIFY_DAYS')
    scheduler_interval_seconds: int = Field(default=120, alias='SCHEDULER_INTERVAL_SECONDS')

    threexui_base_url: str = Field(default='', alias='THREEXUI_BASE_URL')
    threexui_public_base_url: str = Field(default='', alias='THREEXUI_PUBLIC_BASE_URL')
    threexui_username: str = Field(default='', alias='THREEXUI_USERNAME')
    threexui_password: str = Field(default='', alias='THREEXUI_PASSWORD')
    threexui_default_inbound_id: int | None = Field(default=None, alias='THREEXUI_DEFAULT_INBOUND_ID')
    threexui_verify_ssl: bool = Field(default=False, alias='THREEXUI_VERIFY_SSL')
    threexui_timeout_seconds: int = Field(default=15, alias='THREEXUI_TIMEOUT_SECONDS')
    threexui_retry_attempts: int = Field(default=3, alias='THREEXUI_RETRY_ATTEMPTS')

    @field_validator('telegram_admin_id', 'threexui_default_inbound_id', mode='before')
    @classmethod
    def _parse_optional_int(cls, value):  # noqa: ANN001
        if value in (None, ''):
            return None
        return int(value)

    @property
    def cors_origins(self) -> List[str]:
        return [item.strip() for item in self.cors_origins_raw.split(',') if item.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


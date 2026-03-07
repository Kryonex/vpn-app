from datetime import datetime
from uuid import UUID

from app.schemas.base import BaseSchema


class TelegramAccountOut(BaseSchema):
    telegram_user_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None


class MeResponse(BaseSchema):
    id: UUID
    referral_code: str
    bonus_days_balance: int
    invited_count: int
    active_keys_count: int
    nearest_expiry: datetime | None
    telegram: TelegramAccountOut | None


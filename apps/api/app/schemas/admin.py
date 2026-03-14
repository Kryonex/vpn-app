from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import VPNKeyStatus
from app.schemas.base import BaseSchema
from app.schemas.payment import PaymentOut
from app.schemas.plan import PlanOut


class AdminUserOut(BaseSchema):
    id: UUID
    referral_code: str
    bonus_days_balance: int
    created_at: datetime
    telegram_username: str | None = None
    telegram_user_id: int | None = None
    total_keys_count: int = 0


class AdminKeyOut(BaseSchema):
    id: UUID
    owner_id: UUID
    display_name: str
    status: VPNKeyStatus
    current_subscription_id: UUID | None
    created_at: datetime


class AdminBonusDaysRequest(BaseModel):
    days: int = Field(ge=1)
    reason: str = Field(min_length=3, max_length=255)


class AdminRevokeKeyRequest(BaseModel):
    reason: str = Field(default='manual_revoke', min_length=3, max_length=255)


class AdminGrantSubscriptionRequest(BaseModel):
    plan_id: UUID
    key_id: UUID | None = None
    key_name: str | None = Field(default=None, max_length=128)


class AdminPaymentsListResponse(BaseModel):
    items: list[PaymentOut]


class AdminReferralStatOut(BaseSchema):
    id: UUID
    referrer_user_id: UUID
    referred_user_id: UUID
    status: str
    created_at: datetime


class AdminSubscriptionOut(BaseSchema):
    id: UUID
    vpn_key_id: UUID
    plan_id: UUID
    starts_at: datetime
    expires_at: datetime
    status: str


class AdminPlanCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=64)
    duration_days: int = Field(ge=1, le=3650)
    price: Decimal = Field(gt=0)
    currency: str = Field(min_length=3, max_length=8)
    is_active: bool = True
    sort_order: int = 0


class AdminPlanUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=64)
    duration_days: int | None = Field(default=None, ge=1, le=3650)
    price: Decimal | None = Field(default=None, gt=0)
    currency: str | None = Field(default=None, min_length=3, max_length=8)
    is_active: bool | None = None
    sort_order: int | None = None


class AdminPaymentDecisionRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=255)


class AdminPlansListResponse(BaseModel):
    items: list[PlanOut]


class AdminClearPaymentsResponse(BaseModel):
    ok: bool
    deleted_count: int


class AdminStatsOut(BaseModel):
    total_payments: int
    succeeded_payments: int
    pending_payments: int
    failed_payments: int
    total_revenue: Decimal
    month_revenue: Decimal


class AdminReferralSettingsOut(BaseModel):
    referral_bonus_days: int


class AdminReferralSettingsUpdateRequest(BaseModel):
    referral_bonus_days: int = Field(ge=0, le=3650)


class AdminResetKeysEarningsRequest(BaseModel):
    confirm_text: str = Field(min_length=5, max_length=32)
    mode: Literal['soft', 'hard'] = 'hard'


class AdminUserLookupOut(BaseModel):
    id: UUID
    referral_code: str
    bonus_days_balance: int
    created_at: datetime
    telegram_username: str | None = None
    telegram_user_id: int | None = None


class AdminBindPanelKeyRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    display_name: str | None = Field(default=None, max_length=128)
    client_uuid: str | None = Field(default=None, max_length=128)
    inbound_id: int | None = None


class AdminBindPanelKeyResponse(BaseModel):
    key_id: UUID
    version_id: UUID
    owner_id: UUID
    connection_uri: str | None


class AdminDeleteKeyRequest(BaseModel):
    reason: str = Field(default='delete_from_history', min_length=3, max_length=255)


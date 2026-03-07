from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import VPNKeyStatus
from app.schemas.base import BaseSchema
from app.schemas.payment import PaymentOut


class AdminUserOut(BaseSchema):
    id: UUID
    referral_code: str
    bonus_days_balance: int
    created_at: datetime


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


class AdminReferralStatOut(BaseModel):
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


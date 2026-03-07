from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.enums import VPNKeyStatus
from app.schemas.base import BaseSchema
from app.schemas.plan import PlanOut


class SubscriptionOut(BaseSchema):
    id: UUID
    starts_at: datetime
    expires_at: datetime
    status: str
    plan: PlanOut


class VPNKeyVersionOut(BaseSchema):
    id: UUID
    version: int
    inbound_id: int | None
    email_remark: str | None
    connection_uri: str | None
    is_active: bool
    created_at: datetime


class VPNKeyOut(BaseSchema):
    id: UUID
    display_name: str
    status: VPNKeyStatus
    created_at: datetime
    updated_at: datetime
    current_subscription: SubscriptionOut | None
    active_version: VPNKeyVersionOut | None = None


class PurchaseRequest(BaseModel):
    plan_id: UUID
    key_name: str | None = Field(default=None, max_length=128)
    apply_bonus_days: int = Field(default=0, ge=0)


class RenewRequest(BaseModel):
    plan_id: UUID
    apply_bonus_days: int = Field(default=0, ge=0)


class RotateResponse(BaseModel):
    key_id: UUID
    new_version: int
    connection_uri: str | None


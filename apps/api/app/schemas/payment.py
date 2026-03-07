from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel

from app.models.enums import PaymentOperation, PaymentProvider, PaymentStatus
from app.schemas.base import BaseSchema


class PaymentOut(BaseSchema):
    id: UUID
    user_id: UUID
    vpn_key_id: UUID | None
    plan_id: UUID
    provider: PaymentProvider
    operation: PaymentOperation
    amount: Decimal
    currency: str
    status: PaymentStatus
    confirmation_url: str | None
    external_payment_id: str | None
    bonus_days_applied: int
    created_at: datetime
    updated_at: datetime


class PaymentIntentOut(BaseModel):
    payment_id: UUID
    provider: PaymentProvider
    status: PaymentStatus
    confirmation_url: str | None
    transfer_phone: str | None = None
    transfer_note: str | None = None


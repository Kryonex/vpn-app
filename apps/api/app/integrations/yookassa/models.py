from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class YooKassaAmount(BaseModel):
    value: Decimal
    currency: str


class YooKassaConfirmation(BaseModel):
    type: str | None = None
    confirmation_url: str | None = Field(default=None, alias='confirmation_url')


class YooKassaPaymentObject(BaseModel):
    id: str
    status: str
    amount: YooKassaAmount
    description: str | None = None
    paid: bool | None = None
    confirmation: YooKassaConfirmation | None = None
    metadata: dict[str, Any] | None = None


class YooKassaWebhookEvent(BaseModel):
    event: str
    object: YooKassaPaymentObject


from __future__ import annotations

from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class PlategaPaymentDetails(BaseModel):
    amount: Decimal
    currency: str


class PlategaCreateTransactionResponse(BaseModel):
    model_config = ConfigDict(extra='allow')

    paymentMethod: str | int | None = None
    transactionId: str
    redirect: str | None = None
    return_: str | None = Field(default=None, alias='return')
    paymentDetails: str | PlategaPaymentDetails | None = None
    status: str
    expiresIn: str | None = None
    merchantId: str | None = None
    usdtRate: Decimal | None = None
    qr: str | None = None


class PlategaTransactionStatusResponse(BaseModel):
    model_config = ConfigDict(extra='allow')

    id: str
    status: str
    paymentDetails: PlategaPaymentDetails | None = None
    merchantName: str | None = None
    mechantId: str | None = None
    merchantId: str | None = None
    comission: Decimal | None = None
    paymentMethod: str | int | None = None
    expiresIn: str | None = None
    return_: str | None = Field(default=None, alias='return')
    comissionUsdt: Decimal | None = None
    amountUsdt: Decimal | None = None
    qr: str | None = None
    payformSuccessUrl: str | None = None
    payload: str | None = None
    comissionType: int | None = None
    externalId: str | None = None
    description: str | None = None


class PlategaCallbackPayload(BaseModel):
    model_config = ConfigDict(extra='allow')

    id: str
    amount: Decimal | None = None
    currency: str | None = None
    status: str
    paymentMethod: int | str | None = None
    payload: str | None = None
    description: str | None = None
    extra: dict[str, Any] | None = None

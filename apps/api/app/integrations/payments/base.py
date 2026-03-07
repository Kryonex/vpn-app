from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Protocol


@dataclass(slots=True)
class ProviderPaymentResult:
    payment_id: str
    status: str
    confirmation_url: str | None
    amount: Decimal
    currency: str
    raw: dict[str, Any]


@dataclass(slots=True)
class ProviderWebhookEvent:
    provider_event_id: str
    event_type: str
    payment_id: str
    status: str
    raw: dict[str, Any]


class PaymentProvider(Protocol):
    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        return_url: str,
        idempotence_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderPaymentResult: ...

    async def get_payment(self, payment_id: str) -> ProviderPaymentResult: ...

    async def parse_webhook(self, payload: dict[str, Any]) -> ProviderWebhookEvent: ...


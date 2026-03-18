from __future__ import annotations

from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.payments.base import PaymentProvider, ProviderPaymentResult, ProviderWebhookEvent
from app.integrations.platega.models import (
    PlategaCallbackPayload,
    PlategaCreateTransactionResponse,
    PlategaTransactionStatusResponse,
)


class PlategaProvider(PaymentProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.platega_base_url.rstrip('/')

    def is_configured(self) -> bool:
        return bool(self.settings.platega_merchant_id and self.settings.platega_secret)

    def build_auth_headers(self) -> dict[str, str]:
        return {
            'X-MerchantId': self.settings.platega_merchant_id,
            'X-Secret': self.settings.platega_secret,
        }

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop('headers', {})
        headers.update(self.build_auth_headers())
        headers.setdefault('Accept', 'application/json')
        headers.setdefault('Content-Type', 'application/json')

        async with httpx.AsyncClient(base_url=self.base_url, timeout=20.0) as client:
            response = await client.request(method, path, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def create_payment(
        self,
        amount: Decimal,
        currency: str,
        description: str,
        return_url: str,
        idempotence_key: str,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderPaymentResult:
        payload = {
            'paymentMethod': self.settings.platega_payment_method,
            'paymentDetails': {
                'amount': int(amount),
                'currency': currency,
            },
            'description': description,
            'return': return_url,
            'failedUrl': return_url,
            'payload': (metadata or {}).get('payload') or idempotence_key,
        }
        data = await self._request('POST', '/transaction/process', json=payload)
        parsed = PlategaCreateTransactionResponse.model_validate(data)
        return ProviderPaymentResult(
            payment_id=parsed.transactionId,
            status=parsed.status,
            confirmation_url=parsed.redirect,
            amount=amount,
            currency=currency,
            raw=data,
        )

    async def get_payment(self, payment_id: str) -> ProviderPaymentResult:
        data = await self._request('GET', f'/transaction/{payment_id}')
        parsed = PlategaTransactionStatusResponse.model_validate(data)
        amount = parsed.paymentDetails.amount if parsed.paymentDetails else Decimal('0')
        currency = parsed.paymentDetails.currency if parsed.paymentDetails else 'RUB'
        return ProviderPaymentResult(
            payment_id=parsed.id,
            status=parsed.status,
            confirmation_url=parsed.payformSuccessUrl,
            amount=amount,
            currency=currency,
            raw=data,
        )

    async def parse_webhook(self, payload: dict[str, Any]) -> ProviderWebhookEvent:
        event = PlategaCallbackPayload.model_validate(payload)
        provider_event_id = f'{event.id}:{event.status}'
        return ProviderWebhookEvent(
            provider_event_id=provider_event_id,
            event_type=event.status,
            payment_id=event.id,
            status=event.status,
            raw=payload,
        )

from __future__ import annotations

import base64
from decimal import Decimal
from typing import Any

import httpx

from app.core.config import get_settings
from app.integrations.payments.base import PaymentProvider, ProviderPaymentResult, ProviderWebhookEvent
from app.integrations.yookassa.models import YooKassaPaymentObject, YooKassaWebhookEvent


class YooKassaProvider(PaymentProvider):
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = 'https://api.yookassa.ru'

    def _auth_header(self) -> str:
        raw = f'{self.settings.yookassa_shop_id}:{self.settings.yookassa_secret_key}'.encode('utf-8')
        return f'Basic {base64.b64encode(raw).decode("utf-8")}'

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        headers = kwargs.pop('headers', {})
        headers['Authorization'] = self._auth_header()
        headers['Content-Type'] = 'application/json'

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
            'amount': {'value': f'{amount:.2f}', 'currency': currency},
            'capture': True,
            'confirmation': {'type': 'redirect', 'return_url': return_url},
            'description': description,
            'metadata': metadata or {},
        }
        data = await self._request('POST', '/v3/payments', json=payload, headers={'Idempotence-Key': idempotence_key})
        parsed = YooKassaPaymentObject.model_validate(data)
        return ProviderPaymentResult(
            payment_id=parsed.id,
            status=parsed.status,
            confirmation_url=parsed.confirmation.confirmation_url if parsed.confirmation else None,
            amount=parsed.amount.value,
            currency=parsed.amount.currency,
            raw=data,
        )

    async def get_payment(self, payment_id: str) -> ProviderPaymentResult:
        data = await self._request('GET', f'/v3/payments/{payment_id}')
        parsed = YooKassaPaymentObject.model_validate(data)
        return ProviderPaymentResult(
            payment_id=parsed.id,
            status=parsed.status,
            confirmation_url=parsed.confirmation.confirmation_url if parsed.confirmation else None,
            amount=parsed.amount.value,
            currency=parsed.amount.currency,
            raw=data,
        )

    async def parse_webhook(self, payload: dict[str, Any]) -> ProviderWebhookEvent:
        event = YooKassaWebhookEvent.model_validate(payload)
        provider_event_id = f'{event.event}:{event.object.id}'
        return ProviderWebhookEvent(
            provider_event_id=provider_event_id,
            event_type=event.event,
            payment_id=event.object.id,
            status=event.object.status,
            raw=payload,
        )


from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.integrations.threexui.models import ThreeXUICreatedClient, ThreeXUIInbound, ThreeXUIResponse

logger = logging.getLogger(__name__)


class ThreeXUIClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.threexui_base_url.rstrip('/')
        self._client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.settings.threexui_timeout_seconds,
            verify=self.settings.threexui_verify_ssl,
        )
        self._auth_ok = False

    @staticmethod
    def _extract_connection_uri(obj: Any) -> str | None:
        if isinstance(obj, str):
            value = obj.strip()
            if value.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'tuic://')):
                return value
            if value.startswith(('http://', 'https://')) and '/sub/' in value:
                return value
            return None
        if isinstance(obj, dict):
            for value in obj.values():
                extracted = ThreeXUIClient._extract_connection_uri(value)
                if extracted:
                    return extracted
        if isinstance(obj, list):
            for value in obj:
                extracted = ThreeXUIClient._extract_connection_uri(value)
                if extracted:
                    return extracted
        return None

    def _build_subscription_url(self, sub_id: str, client_uuid: str) -> str | None:
        base = (self.settings.threexui_public_base_url or self.base_url).strip()
        if not base:
            return None
        parsed = urlparse(base)
        if not parsed.scheme or not parsed.netloc:
            return None
        # Different 3x-ui builds may use either subId or client UUID in subscription endpoint.
        return f'{parsed.scheme}://{parsed.netloc}/sub/{sub_id or client_uuid}'

    async def close(self) -> None:
        await self._client.aclose()

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1), reraise=True)
    async def login(self) -> None:
        payload = {'username': self.settings.threexui_username, 'password': self.settings.threexui_password}
        response = await self._client.post('/login', data=payload)
        if response.status_code >= 400:
            response.raise_for_status()
        self._auth_ok = True

    async def _ensure_auth(self) -> None:
        if self._auth_ok:
            return
        await self.login()

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        await self._ensure_auth()
        response = await self._client.request(method, path, **kwargs)
        if response.status_code == 401:
            self._auth_ok = False
            await self.login()
            response = await self._client.request(method, path, **kwargs)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict):
            return data
        return {'success': True, 'obj': data}

    async def _request_with_fallback(self, method: str, paths: list[str], **kwargs: Any) -> dict[str, Any]:
        last_error: Exception | None = None
        for path in paths:
            try:
                return await self._request(method, path, **kwargs)
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning('3x-ui endpoint fallback: %s failed (%s)', path, type(exc).__name__)
        if last_error:
            raise last_error
        raise RuntimeError('No endpoint candidates provided')

    def _unwrap_obj(self, data: dict[str, Any]) -> Any:
        parsed = ThreeXUIResponse.model_validate(data)
        if parsed.obj is not None:
            return parsed.obj
        return data

    async def get_inbounds(self) -> list[ThreeXUIInbound]:
        data = await self._request_with_fallback('GET', ['/panel/api/inbounds/list', '/xui/API/inbounds/list'])
        obj = self._unwrap_obj(data)
        if isinstance(obj, list):
            return [ThreeXUIInbound.model_validate(item) for item in obj if isinstance(item, dict)]
        return []

    async def add_client(
        self,
        inbound_id: int,
        client_uuid: str,
        email_remark: str,
        expires_at: datetime,
        sub_id: str,
    ) -> ThreeXUICreatedClient:
        expiry_ms = int(expires_at.astimezone(timezone.utc).timestamp() * 1000)
        client_payload = {
            'id': client_uuid,
            'email': email_remark,
            'enable': True,
            'expiryTime': expiry_ms,
            'limitIp': 0,
            'totalGB': 0,
            'tgId': '',
            'subId': sub_id,
        }

        payload_primary = {'id': inbound_id, 'settings': json.dumps({'clients': [client_payload]})}
        payload_fallback = {'inboundId': inbound_id, 'clients': [client_payload]}

        data = await self._request_with_fallback(
            'POST',
            ['/panel/api/inbounds/addClient', '/xui/API/inbounds/addClient'],
            json=payload_primary,
        )

        if not data.get('success', True):
            # Some 3x-ui builds use another shape. Try fallback payload.
            data = await self._request_with_fallback(
                'POST',
                ['/panel/api/inbounds/addClient', '/xui/API/inbounds/addClient'],
                json=payload_fallback,
            )

        connection_uri = self._extract_connection_uri(data)
        if not connection_uri:
            info = await self.get_client_info(client_uuid)
            connection_uri = self._extract_connection_uri(info or {})

        if not connection_uri:
            connection_uri = self._build_subscription_url(sub_id=sub_id, client_uuid=client_uuid)
        if not connection_uri:
            # final best-effort fallback for installations that expect UUID in sub endpoint
            base = (self.settings.threexui_public_base_url or self.base_url).strip().rstrip('/')
            if base:
                connection_uri = f'{base}/sub/{client_uuid}'

        return ThreeXUICreatedClient(
            client_uuid=client_uuid,
            inbound_id=inbound_id,
            email_remark=email_remark,
            connection_uri=connection_uri,
            raw=data,
        )

    async def update_client_expiry(self, inbound_id: int, client_uuid: str, email_remark: str, expires_at: datetime) -> None:
        expiry_ms = int(expires_at.astimezone(timezone.utc).timestamp() * 1000)
        client_payload = {
            'id': client_uuid,
            'email': email_remark,
            'enable': True,
            'expiryTime': expiry_ms,
            'limitIp': 0,
            'totalGB': 0,
            'tgId': '',
            'subId': '',
        }

        payload = {'id': inbound_id, 'settings': json.dumps({'clients': [client_payload]})}
        await self._request_with_fallback(
            'POST',
            [f'/panel/api/inbounds/updateClient/{client_uuid}', '/panel/api/inbounds/updateClient'],
            json=payload,
        )

    async def delete_client(self, client_uuid: str) -> None:
        await self._request_with_fallback(
            'POST',
            [f'/panel/api/inbounds/delClient/{client_uuid}', f'/xui/API/inbounds/delClient/{client_uuid}'],
        )

    async def get_client_info(self, client_uuid: str) -> dict[str, Any] | None:
        try:
            data = await self._request_with_fallback(
                'GET',
                [f'/panel/api/inbounds/getClientTraffics/{client_uuid}', f'/xui/API/inbounds/getClientTraffics/{client_uuid}'],
            )
            return data
        except Exception as exc:  # noqa: BLE001
            logger.warning('3x-ui get_client_info not available for %s: %s', client_uuid, type(exc).__name__)
            return None

    async def create_client_on_default_inbound(self, email_remark: str, expires_at: datetime) -> ThreeXUICreatedClient:
        inbound_id = self.settings.threexui_default_inbound_id
        if inbound_id is None:
            inbounds = await self.get_inbounds()
            if not inbounds:
                raise RuntimeError('No 3x-ui inbounds available')
            inbound_id = inbounds[0].id

        client_uuid = str(uuid.uuid4())
        sub_id = uuid.uuid4().hex[:16]
        return await self.add_client(
            inbound_id=inbound_id,
            client_uuid=client_uuid,
            email_remark=email_remark,
            expires_at=expires_at,
            sub_id=sub_id,
        )


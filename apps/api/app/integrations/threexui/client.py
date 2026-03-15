from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any
from urllib.parse import quote, urlencode, urlparse

import httpx
from tenacity import retry, stop_after_attempt, wait_fixed

from app.core.config import get_settings
from app.integrations.threexui.models import (
    ThreeXUICreatedClient,
    ThreeXUIInbound,
    ThreeXUIPanelClientSnapshot,
    ThreeXUIResponse,
)

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
    def _parse_json_field(value: Any) -> dict[str, Any] | list[Any] | None:
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                if isinstance(parsed, (dict, list)):
                    return parsed
            except json.JSONDecodeError:
                return None
        return None

    @staticmethod
    def _extract_connection_uri(obj: Any) -> str | None:
        known_keys = {
            'link',
            'url',
            'uri',
            'subscription',
            'subscriptionurl',
            'subscription_url',
            'suburl',
            'sub_url',
            'subscribe',
            'sub',
        }

        if isinstance(obj, str):
            value = obj.strip()
            if value.startswith(('vless://', 'vmess://', 'trojan://', 'ss://', 'hysteria2://', 'tuic://')):
                return value
            if value.startswith(('http://', 'https://')) and '/sub/' in value:
                return value
            return None

        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in known_keys and isinstance(value, str):
                    extracted = ThreeXUIClient._extract_connection_uri(value)
                    if extracted:
                        return extracted
                extracted = ThreeXUIClient._extract_connection_uri(value)
                if extracted:
                    return extracted

        if isinstance(obj, list):
            for value in obj:
                extracted = ThreeXUIClient._extract_connection_uri(value)
                if extracted:
                    return extracted

        return None

    @staticmethod
    def _extract_expiry_time(client_obj: dict[str, Any]) -> datetime | None:
        raw = client_obj.get('expiryTime')
        if raw in (None, 0, '0', ''):
            return None
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None
        # 3x-ui usually returns milliseconds.
        if value > 10_000_000_000:
            value = value // 1000
        try:
            return datetime.fromtimestamp(value, tz=timezone.utc)
        except (OverflowError, OSError, ValueError):
            return None

    @staticmethod
    def _extract_enable_flag(client_obj: dict[str, Any]) -> bool | None:
        value = client_obj.get('enable')
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, str):
            return value.lower() in {'true', '1', 'yes'}
        return None

    def _build_subscription_url(self, sub_id: str | None, client_uuid: str) -> str | None:
        base = (self.settings.threexui_public_base_url or self.base_url).strip()
        if not base:
            return None

        parsed = urlparse(base)
        if not parsed.scheme or not parsed.netloc:
            return None

        token = sub_id or client_uuid
        return f'{parsed.scheme}://{parsed.netloc}/sub/{token}'

    def _build_vless_uri_from_panel(self, inbound_obj: dict[str, Any], client_obj: dict[str, Any]) -> str | None:
        protocol = str(inbound_obj.get('protocol') or '').lower()
        if protocol != 'vless':
            return None

        client_uuid = str(client_obj.get('id') or '').strip()
        if not client_uuid:
            return None

        base = (self.settings.threexui_public_base_url or self.base_url).strip()
        parsed = urlparse(base)
        host = parsed.hostname or '127.0.0.1'

        port = inbound_obj.get('port')
        if not isinstance(port, int):
            return None

        stream = self._parse_json_field(inbound_obj.get('streamSettings'))
        stream_dict = stream if isinstance(stream, dict) else {}

        network = str(stream_dict.get('network') or 'tcp')
        security = str(stream_dict.get('security') or 'none')

        params: dict[str, str] = {
            'type': network,
            'security': security,
            'encryption': 'none',
        }

        if security == 'tls':
            tls_settings = self._parse_json_field(stream_dict.get('tlsSettings'))
            if isinstance(tls_settings, dict):
                server_name = tls_settings.get('serverName')
                if isinstance(server_name, str) and server_name:
                    params['sni'] = server_name
        elif security == 'reality':
            reality = self._parse_json_field(stream_dict.get('realitySettings'))
            if isinstance(reality, dict):
                server_names = reality.get('serverNames')
                if isinstance(server_names, list) and server_names:
                    params['sni'] = str(server_names[0])
                public_key = reality.get('publicKey')
                if isinstance(public_key, str) and public_key:
                    params['pbk'] = public_key
                short_ids = reality.get('shortIds')
                if isinstance(short_ids, list) and short_ids:
                    params['sid'] = str(short_ids[0])

        if network == 'ws':
            ws_settings = self._parse_json_field(stream_dict.get('wsSettings'))
            if isinstance(ws_settings, dict):
                path = ws_settings.get('path')
                if isinstance(path, str) and path:
                    params['path'] = path
                headers = ws_settings.get('headers')
                if isinstance(headers, dict):
                    host_header = headers.get('Host')
                    if isinstance(host_header, str) and host_header:
                        params['host'] = host_header
        elif network == 'grpc':
            grpc_settings = self._parse_json_field(stream_dict.get('grpcSettings'))
            if isinstance(grpc_settings, dict):
                service_name = grpc_settings.get('serviceName')
                if isinstance(service_name, str) and service_name:
                    params['serviceName'] = service_name

        remark = str(client_obj.get('email') or inbound_obj.get('remark') or 'VPN')
        query = urlencode(params)
        return f'vless://{client_uuid}@{host}:{port}?{query}#{quote(remark)}'

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

    async def get_inbounds_raw(self) -> list[dict[str, Any]]:
        data = await self._request_with_fallback('GET', ['/panel/api/inbounds/list', '/xui/API/inbounds/list'])
        obj = self._unwrap_obj(data)
        if not isinstance(obj, list):
            return []
        return [item for item in obj if isinstance(item, dict)]

    async def get_inbounds(self) -> list[ThreeXUIInbound]:
        rows = await self.get_inbounds_raw()
        return [ThreeXUIInbound.model_validate(item) for item in rows]

    async def get_inbound_data(self, inbound_id: int) -> dict[str, Any] | None:
        try:
            data = await self._request_with_fallback(
                'GET',
                [f'/panel/api/inbounds/get/{inbound_id}', f'/xui/API/inbounds/get/{inbound_id}'],
            )
            obj = self._unwrap_obj(data)
            if isinstance(obj, dict):
                return obj
        except Exception as exc:  # noqa: BLE001
            logger.warning('3x-ui get inbound by id failed for %s: %s', inbound_id, type(exc).__name__)

        inbounds = await self.get_inbounds_raw()
        for item in inbounds:
            try:
                if int(item.get('id', -1)) == inbound_id:
                    return item
            except (TypeError, ValueError):
                continue
        return None

    @staticmethod
    def _extract_clients_from_inbound(inbound_obj: dict[str, Any]) -> list[dict[str, Any]]:
        clients: list[dict[str, Any]] = []

        settings = ThreeXUIClient._parse_json_field(inbound_obj.get('settings'))
        if isinstance(settings, dict):
            raw_clients = settings.get('clients')
            if isinstance(raw_clients, list):
                clients.extend(item for item in raw_clients if isinstance(item, dict))

        for key in ('clients', 'clientStats', 'client_stats'):
            data = inbound_obj.get(key)
            if isinstance(data, list):
                clients.extend(item for item in data if isinstance(item, dict))

        unique: list[dict[str, Any]] = []
        seen: set[str] = set()
        for item in clients:
            marker = f"{item.get('id', '')}|{item.get('email', '')}"
            if marker in seen:
                continue
            seen.add(marker)
            unique.append(item)

        return unique

    async def get_client_snapshot(
        self,
        *,
        inbound_id: int | None,
        client_uuid: str,
        email_remark: str | None,
        fallback_sub_id: str | None = None,
    ) -> ThreeXUIPanelClientSnapshot | None:
        candidate_inbounds: list[dict[str, Any]] = []

        if inbound_id is not None:
            inbound = await self.get_inbound_data(inbound_id)
            if inbound:
                candidate_inbounds.append(inbound)

        if not candidate_inbounds:
            candidate_inbounds = await self.get_inbounds_raw()

        for inbound in candidate_inbounds:
            clients = self._extract_clients_from_inbound(inbound)
            for client in clients:
                row_uuid = str(client.get('id') or '').strip()
                row_email = str(client.get('email') or '').strip()
                if row_uuid != client_uuid and (not email_remark or row_email != email_remark):
                    continue

                sub_id = str(client.get('subId') or client.get('sub_id') or fallback_sub_id or '').strip() or None
                connection_uri = (
                    self._extract_connection_uri(client)
                    or self._extract_connection_uri(inbound)
                    or self._build_subscription_url(sub_id=sub_id, client_uuid=client_uuid)
                    or self._build_vless_uri_from_panel(inbound, client)
                )

                inbound_value = inbound.get('id')
                inbound_value_int = int(inbound_value) if isinstance(inbound_value, int) else inbound_id

                return ThreeXUIPanelClientSnapshot(
                    client_uuid=client_uuid,
                    inbound_id=inbound_value_int,
                    email_remark=row_email or email_remark,
                    sub_id=sub_id,
                    expires_at=self._extract_expiry_time(client),
                    is_active=self._extract_enable_flag(client),
                    connection_uri=connection_uri,
                    raw={'inbound': inbound, 'client': client},
                )

        info = await self.get_client_info(client_uuid)
        if info:
            connection_uri = self._extract_connection_uri(info)
            if connection_uri:
                return ThreeXUIPanelClientSnapshot(
                    client_uuid=client_uuid,
                    inbound_id=inbound_id,
                    email_remark=email_remark,
                    sub_id=fallback_sub_id,
                    expires_at=None,
                    is_active=None,
                    connection_uri=connection_uri,
                    raw={'traffic': info},
                )

        return None

    async def list_client_snapshots_by_username(self, username: str) -> list[ThreeXUIPanelClientSnapshot]:
        normalized = username.lstrip('@').strip().lower()
        if not normalized:
            return []

        tag = f'@{normalized}'
        inbounds = await self.get_inbounds_raw()
        result: list[ThreeXUIPanelClientSnapshot] = []

        for inbound in inbounds:
            inbound_id_raw = inbound.get('id')
            inbound_id = inbound_id_raw if isinstance(inbound_id_raw, int) else None
            clients = self._extract_clients_from_inbound(inbound)
            for client in clients:
                email = str(client.get('email') or '').strip()
                if not email:
                    continue
                if tag not in email.lower() and normalized not in email.lower():
                    continue

                sub_id = str(client.get('subId') or client.get('sub_id') or '').strip() or None
                connection_uri = (
                    self._extract_connection_uri(client)
                    or self._extract_connection_uri(inbound)
                    or self._build_subscription_url(sub_id=sub_id, client_uuid=str(client.get('id') or ''))
                    or self._build_vless_uri_from_panel(inbound, client)
                )

                result.append(
                    ThreeXUIPanelClientSnapshot(
                        client_uuid=str(client.get('id') or ''),
                        inbound_id=inbound_id,
                        email_remark=email or None,
                        sub_id=sub_id,
                        expires_at=self._extract_expiry_time(client),
                        is_active=self._extract_enable_flag(client),
                        connection_uri=connection_uri,
                        raw={'inbound': inbound, 'client': client},
                    )
                )

        return [item for item in result if item.client_uuid]

    async def add_client(
        self,
        inbound_id: int,
        client_uuid: str,
        email_remark: str,
        expires_at: datetime,
        sub_id: str,
        *,
        template_client: dict[str, Any] | None = None,
    ) -> ThreeXUICreatedClient:
        expiry_ms = int(expires_at.astimezone(timezone.utc).timestamp() * 1000)
        template = template_client if isinstance(template_client, dict) else {}
        client_payload = {
            'id': client_uuid,
            'email': email_remark,
            'enable': bool(template.get('enable', True)),
            'expiryTime': expiry_ms,
            'limitIp': int(template.get('limitIp', 0) or 0),
            'totalGB': int(template.get('totalGB', 0) or 0),
            'tgId': str(template.get('tgId', '') or ''),
            'subId': sub_id,
        }
        for optional_key in ('flow', 'comment', 'reset', 'telegramId'):
            value = template.get(optional_key)
            if value not in (None, ''):
                client_payload[optional_key] = value

        payload_primary = {'id': inbound_id, 'settings': json.dumps({'clients': [client_payload]})}
        payload_fallback = {'inboundId': inbound_id, 'clients': [client_payload]}

        data = await self._request_with_fallback(
            'POST',
            ['/panel/api/inbounds/addClient', '/xui/API/inbounds/addClient'],
            json=payload_primary,
        )

        if not data.get('success', True):
            data = await self._request_with_fallback(
                'POST',
                ['/panel/api/inbounds/addClient', '/xui/API/inbounds/addClient'],
                json=payload_fallback,
            )

        snapshot: ThreeXUIPanelClientSnapshot | None = None
        for _ in range(3):
            snapshot = await self.get_client_snapshot(
                inbound_id=inbound_id,
                client_uuid=client_uuid,
                email_remark=email_remark,
                fallback_sub_id=sub_id,
            )
            if snapshot and snapshot.connection_uri:
                break
            await asyncio.sleep(0.35)

        connection_uri = snapshot.connection_uri if snapshot else self._build_subscription_url(sub_id, client_uuid)

        return ThreeXUICreatedClient(
            client_uuid=client_uuid,
            inbound_id=inbound_id,
            email_remark=email_remark,
            connection_uri=connection_uri,
            raw={'create_response': data, 'panel_snapshot': snapshot.raw if snapshot else None},
        )

    async def update_client_expiry(
        self,
        inbound_id: int,
        client_uuid: str,
        email_remark: str,
        expires_at: datetime,
        *,
        enable: bool = True,
        sub_id: str | None = None,
    ) -> None:
        expiry_ms = int(expires_at.astimezone(timezone.utc).timestamp() * 1000)
        client_payload = {
            'id': client_uuid,
            'email': email_remark,
            'enable': enable,
            'expiryTime': expiry_ms,
            'limitIp': 0,
            'totalGB': 0,
            'tgId': '',
            'subId': sub_id or '',
        }

        payload = {'id': inbound_id, 'settings': json.dumps({'clients': [client_payload]})}
        await self._request_with_fallback(
            'POST',
            [
                f'/panel/api/inbounds/updateClient/{client_uuid}',
                '/panel/api/inbounds/updateClient',
                f'/xui/API/inbounds/updateClient/{client_uuid}',
            ],
            json=payload,
        )

    async def delete_client(self, client_uuid: str, *, inbound_id: int | None = None, email_remark: str | None = None) -> None:
        try:
            await self._request_with_fallback(
                'POST',
                [f'/panel/api/inbounds/delClient/{client_uuid}', f'/xui/API/inbounds/delClient/{client_uuid}'],
            )
            return
        except Exception as exc:  # noqa: BLE001
            logger.warning('3x-ui delete client failed for %s: %s', client_uuid, type(exc).__name__)
            if inbound_id is None:
                raise

        await self.update_client_expiry(
            inbound_id=inbound_id,
            client_uuid=client_uuid,
            email_remark=email_remark or client_uuid,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
            enable=False,
            sub_id=None,
        )

    async def get_client_info(self, client_uuid: str) -> dict[str, Any] | None:
        try:
            data = await self._request_with_fallback(
                'GET',
                [
                    f'/panel/api/inbounds/getClientTraffics/{client_uuid}',
                    f'/xui/API/inbounds/getClientTraffics/{client_uuid}',
                ],
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

from __future__ import annotations

import json
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.integrations.threexui.service import ThreeXUIService
from app.models.plan import Plan
from app.repositories.app_settings_repository import AppSettingsRepository


class AccessPolicyService:
    PURCHASE_INBOUND_IDS_KEY = 'purchase_inbound_ids'
    FREE_TRIAL_SETTINGS_KEY = 'free_trial_settings'
    PLAN_INBOUND_MAP_KEY = 'plan_inbound_map'
    FREE_TRIAL_PLAN_NAME = 'Пробный доступ'

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = AppSettingsRepository(session)
        self.settings = get_settings()

    @staticmethod
    def _normalize_inbound_ids(values: list[int] | None) -> list[int]:
        if not values:
            return []
        normalized = sorted({int(value) for value in values if int(value) > 0})
        return normalized

    async def _get_json(self, key: str, default: Any) -> Any:
        setting = await self.repo.get(key)
        if not setting or not setting.value.strip():
            return default
        try:
            return json.loads(setting.value)
        except json.JSONDecodeError:
            return default

    async def _set_json(self, key: str, value: Any) -> None:
        await self.repo.set(key, json.dumps(value, ensure_ascii=False))

    async def get_available_inbounds(self, threexui_service: ThreeXUIService) -> list[dict[str, Any]]:
        inbounds = await threexui_service.fetch_inbounds()
        return [
            {
                'id': item.id,
                'remark': item.remark,
                'protocol': item.protocol,
                'port': item.port,
            }
            for item in inbounds
        ]

    async def get_purchase_inbound_ids(self) -> list[int]:
        raw = await self._get_json(self.PURCHASE_INBOUND_IDS_KEY, [])
        if not isinstance(raw, list):
            return []
        return self._normalize_inbound_ids(raw)

    async def set_purchase_inbound_ids(self, inbound_ids: list[int]) -> list[int]:
        normalized = self._normalize_inbound_ids(inbound_ids)
        await self._set_json(self.PURCHASE_INBOUND_IDS_KEY, normalized)
        await self.session.flush()
        return normalized

    async def get_free_trial_settings(self) -> dict[str, Any]:
        raw = await self._get_json(
            self.FREE_TRIAL_SETTINGS_KEY,
            {'enabled': False, 'days': 3, 'inbound_ids': []},
        )
        if not isinstance(raw, dict):
            raw = {}
        return {
            'enabled': bool(raw.get('enabled', False)),
            'days': max(int(raw.get('days', 3) or 3), 1),
            'inbound_ids': self._normalize_inbound_ids(raw.get('inbound_ids') if isinstance(raw.get('inbound_ids'), list) else []),
        }

    async def set_free_trial_settings(self, *, enabled: bool, days: int, inbound_ids: list[int]) -> dict[str, Any]:
        payload = {
            'enabled': bool(enabled),
            'days': max(int(days), 1),
            'inbound_ids': self._normalize_inbound_ids(inbound_ids),
        }
        await self._set_json(self.FREE_TRIAL_SETTINGS_KEY, payload)
        await self.session.flush()
        return payload

    async def get_plan_inbound_map(self) -> dict[str, list[int]]:
        raw = await self._get_json(self.PLAN_INBOUND_MAP_KEY, {})
        if not isinstance(raw, dict):
            return {}
        result: dict[str, list[int]] = {}
        for key, value in raw.items():
            if not isinstance(key, str) or not isinstance(value, list):
                continue
            result[key] = self._normalize_inbound_ids(value)
        return result

    async def get_plan_inbound_ids(self, plan_id: UUID) -> list[int]:
        mapping = await self.get_plan_inbound_map()
        return mapping.get(str(plan_id), [])

    async def set_plan_inbound_ids(self, plan_id: UUID, inbound_ids: list[int]) -> list[int]:
        mapping = await self.get_plan_inbound_map()
        normalized = self._normalize_inbound_ids(inbound_ids)
        mapping[str(plan_id)] = normalized
        await self._set_json(self.PLAN_INBOUND_MAP_KEY, mapping)
        await self.session.flush()
        return normalized

    async def resolve_plan_inbound_ids(
        self,
        *,
        plan_id: UUID | None,
        threexui_service: ThreeXUIService,
        fallback_to_free_trial: bool = False,
    ) -> list[int]:
        if plan_id:
            plan_specific = await self.get_plan_inbound_ids(plan_id)
            if plan_specific:
                return plan_specific

        if fallback_to_free_trial:
            free_trial = await self.get_free_trial_settings()
            if free_trial['inbound_ids']:
                return list(free_trial['inbound_ids'])

        global_ids = await self.get_purchase_inbound_ids()
        if global_ids:
            return global_ids

        if self.settings.threexui_default_inbound_id is not None:
            return [self.settings.threexui_default_inbound_id]

        inbounds = await self.get_available_inbounds(threexui_service)
        return [inbounds[0]['id']] if inbounds else []

    async def ensure_free_trial_plan(self, days: int) -> Plan:
        plan = await self.session.scalar(
            select(Plan).where(Plan.name == self.FREE_TRIAL_PLAN_NAME).limit(1)
        )
        if not plan:
            plan = Plan(
                name=self.FREE_TRIAL_PLAN_NAME,
                duration_days=max(int(days), 1),
                price=Decimal('0'),
                currency='RUB',
                is_active=False,
                sort_order=-100,
            )
            self.session.add(plan)
            await self.session.flush()
            return plan

        plan.duration_days = max(int(days), 1)
        plan.price = Decimal('0')
        plan.currency = 'RUB'
        plan.is_active = False
        return plan

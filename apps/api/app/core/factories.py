from collections.abc import AsyncIterator
from functools import lru_cache

from app.integrations.threexui.service import ThreeXUIService
from app.integrations.yookassa.provider import YooKassaProvider


@lru_cache(maxsize=1)
def get_yookassa_provider() -> YooKassaProvider:
    return YooKassaProvider()


async def threexui_dependency() -> AsyncIterator[ThreeXUIService]:
    service = ThreeXUIService()
    try:
        yield service
    finally:
        await service.client.close()

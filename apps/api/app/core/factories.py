from collections.abc import AsyncIterator

from app.integrations.threexui.service import ThreeXUIService


async def threexui_dependency() -> AsyncIterator[ThreeXUIService]:
    service = ThreeXUIService()
    try:
        yield service
    finally:
        await service.client.close()

import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware, Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import TelegramObject

from bot.handlers import add_toilet, location, payment, report, start

logger = logging.getLogger(__name__)


class MetricsMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        logger.info("update received", extra={"tags": {"event_type": "update"}})
        return await handler(event, data)


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.outer_middleware(MetricsMiddleware())
    dp.include_router(start.router)
    dp.include_router(add_toilet.router)
    dp.include_router(report.router)
    dp.include_router(payment.router)
    dp.include_router(location.router)
    return dp

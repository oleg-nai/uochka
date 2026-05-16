"""Tests for bot/app.py — dispatcher assembly and metrics middleware."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from bot.app import MetricsMiddleware, create_dispatcher


class TestCreateDispatcher:
    """Routers in bot/handlers/* are module-level singletons. aiogram raises if a
    router is included into more than one Dispatcher, so we build the dispatcher
    ONCE per session and share it across the assertions in this class."""

    @pytest.fixture(scope="class")
    def dp(self):
        return create_dispatcher()

    def test_returns_dispatcher_with_memory_storage(self, dp):
        assert isinstance(dp, Dispatcher)
        assert isinstance(dp.fsm.storage, MemoryStorage)

    def test_includes_all_five_routers(self, dp):
        # The dispatcher must register start, add_toilet, report, payment, location.
        # `Dispatcher.sub_routers` lists directly attached child routers.
        assert len(dp.sub_routers) == 5

    def test_attaches_metrics_middleware_to_update(self, dp):
        middlewares = list(dp.update.outer_middleware)
        # Ensure a MetricsMiddleware is wired in as an outer middleware on update.
        assert any(isinstance(m, MetricsMiddleware) for m in middlewares)


class TestMetricsMiddleware:
    async def test_calls_handler_and_returns_its_result(self):
        mw = MetricsMiddleware()
        handler = AsyncMock(return_value="result")
        event = MagicMock()
        data = {"foo": "bar"}

        result = await mw(handler, event, data)

        handler.assert_awaited_once_with(event, data)
        assert result == "result"

    async def test_propagates_handler_exceptions(self):
        mw = MetricsMiddleware()

        async def boom(event, data):
            raise RuntimeError("boom")

        with pytest.raises(RuntimeError, match="boom"):
            await mw(boom, MagicMock(), {})

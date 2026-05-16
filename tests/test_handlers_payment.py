"""Tests for bot/handlers/payment.py — Telegram Stars premium flow."""

from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiogram.types import LabeledPrice

from bot.handlers import payment as payment_handler


# ---------------------------------------------------------------------------
# buy_premium callback
# ---------------------------------------------------------------------------


class TestBuyPremium:
    async def test_free_user_gets_invoice(self, make_callback):
        cb = make_callback(data="buy_premium", user_id=111)

        with patch.object(payment_handler, "get_user", return_value={"is_premium": False}):
            await payment_handler.buy_premium_handler(cb)

        cb.answer.assert_awaited_once()
        cb.message.answer_invoice.assert_awaited_once()
        kwargs = cb.message.answer_invoice.await_args.kwargs
        assert kwargs["currency"] == "XTR"
        assert kwargs["payload"] == "premium:111"
        # Single line-item priced at STARS_PRICE.
        prices = kwargs["prices"]
        assert len(prices) == 1
        assert isinstance(prices[0], LabeledPrice)
        assert prices[0].amount == payment_handler.STARS_PRICE

    async def test_missing_user_treated_as_free_and_gets_invoice(self, make_callback):
        cb = make_callback(data="buy_premium")

        with patch.object(payment_handler, "get_user", return_value=None):
            await payment_handler.buy_premium_handler(cb)

        cb.message.answer_invoice.assert_awaited_once()

    async def test_premium_user_does_not_get_invoice(self, make_callback):
        cb = make_callback(data="buy_premium")

        with patch.object(payment_handler, "get_user", return_value={"is_premium": True}):
            await payment_handler.buy_premium_handler(cb)

        cb.message.answer_invoice.assert_not_awaited()
        # Should send a "you already have premium" message instead.
        cb.message.answer.assert_awaited_once()
        text = cb.message.answer.await_args.args[0]
        assert "Premium" in text

    async def test_payload_encodes_tg_id(self, make_callback):
        cb = make_callback(data="buy_premium", user_id=42)

        with patch.object(payment_handler, "get_user", return_value=None):
            await payment_handler.buy_premium_handler(cb)

        payload = cb.message.answer_invoice.await_args.kwargs["payload"]
        assert payload == "premium:42"


# ---------------------------------------------------------------------------
# pre_checkout
# ---------------------------------------------------------------------------


class TestPreCheckout:
    async def test_always_answers_ok(self):
        # Critical: pre_checkout must always answer ok=True or the payment fails on Telegram's side.
        query = MagicMock()
        query.answer = AsyncMock()

        await payment_handler.pre_checkout_handler(query)

        query.answer.assert_awaited_once_with(ok=True)


# ---------------------------------------------------------------------------
# successful_payment
# ---------------------------------------------------------------------------


class TestSuccessfulPayment:
    async def test_sets_premium_and_logs_event_with_star_count(self, make_message):
        sp = SimpleNamespace(total_amount=1)
        msg = make_message(successful_payment=sp, user_id=42)

        with patch.object(payment_handler, "set_premium") as set_prem, \
             patch.object(payment_handler, "log_event") as log_evt:
            await payment_handler.successful_payment_handler(msg)

        set_prem.assert_called_once_with(42)
        log_evt.assert_called_once_with(42, "premium_activated", {"stars": 1})

    async def test_confirms_activation_to_user(self, make_message):
        sp = SimpleNamespace(total_amount=1)
        msg = make_message(successful_payment=sp)

        with patch.object(payment_handler, "set_premium"), \
             patch.object(payment_handler, "log_event"):
            await payment_handler.successful_payment_handler(msg)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "Premium" in text and "активирован" in text.lower()


# ---------------------------------------------------------------------------
# /premium status command
# ---------------------------------------------------------------------------


class TestPremiumStatus:
    async def test_premium_user_sees_status_no_unlock_button(self, make_message):
        msg = make_message(text="/premium", user_id=111)

        with patch.object(payment_handler, "get_user", return_value={"is_premium": True}):
            await payment_handler.premium_status_handler(msg)

        msg.answer.assert_awaited_once()
        # The premium-status message should NOT include the unlock_keyboard inline button.
        kwargs = msg.answer.await_args.kwargs
        assert kwargs.get("reply_markup") is None
        text = msg.answer.await_args.args[0]
        assert "Premium" in text

    async def test_free_user_sees_unlock_keyboard(self, make_message):
        msg = make_message(text="/premium", user_id=111)

        with patch.object(payment_handler, "get_user", return_value={"is_premium": False}):
            await payment_handler.premium_status_handler(msg)

        msg.answer.assert_awaited_once()
        kb = msg.answer.await_args.kwargs["reply_markup"]
        assert kb.inline_keyboard[0][0].callback_data == "buy_premium"

    async def test_missing_user_treated_as_free(self, make_message):
        msg = make_message(text="/premium")

        with patch.object(payment_handler, "get_user", return_value=None):
            await payment_handler.premium_status_handler(msg)

        kb = msg.answer.await_args.kwargs["reply_markup"]
        assert kb.inline_keyboard[0][0].callback_data == "buy_premium"


# ---------------------------------------------------------------------------
# /balance — admin-only star balance check
# ---------------------------------------------------------------------------


class _FakeAiohttpResponse:
    def __init__(self, json_payload):
        self._json = json_payload

    async def json(self):
        return self._json

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False


class _FakeAiohttpSession:
    """Mimic `aiohttp.ClientSession` as a context manager whose `.get(...)` also yields a context manager."""

    def __init__(self, json_payload=None, *, raise_on_get: Exception | None = None):
        self._json = json_payload
        self._raise = raise_on_get

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    def get(self, url, timeout=None):
        if self._raise:
            raise self._raise
        return _FakeAiohttpResponse(self._json)


class TestBalanceHandler:
    def _msg(self, make_message, user_id):
        msg = make_message(text="/balance", user_id=user_id)
        # The handler reads `message.bot.token` — supply it.
        msg.bot = SimpleNamespace(token="0:test-bot-token")
        return msg

    async def test_non_admin_is_silently_ignored(self, make_message):
        msg = self._msg(make_message, user_id=payment_handler.ADMIN_ID + 1)

        # If the guard is broken we'd hit aiohttp — make that a hard failure.
        with patch.object(payment_handler, "aiohttp", side_effect=AssertionError("aiohttp should not be touched")):
            await payment_handler.balance_handler(msg)

        msg.answer.assert_not_awaited()

    async def test_admin_sees_star_balance(self, make_message):
        msg = self._msg(make_message, user_id=payment_handler.ADMIN_ID)

        fake_aiohttp = MagicMock()
        fake_aiohttp.ClientSession = lambda: _FakeAiohttpSession(
            json_payload={"ok": True, "result": {"amount": 42}}
        )
        fake_aiohttp.ClientTimeout = lambda total: None

        with patch.object(payment_handler, "aiohttp", fake_aiohttp):
            await payment_handler.balance_handler(msg)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "42" in text

    async def test_admin_telegram_api_error_reported(self, make_message):
        msg = self._msg(make_message, user_id=payment_handler.ADMIN_ID)

        fake_aiohttp = MagicMock()
        fake_aiohttp.ClientSession = lambda: _FakeAiohttpSession(
            json_payload={"ok": False, "description": "nope"}
        )
        fake_aiohttp.ClientTimeout = lambda total: None

        with patch.object(payment_handler, "aiohttp", fake_aiohttp):
            await payment_handler.balance_handler(msg)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "nope" in text

    async def test_admin_exception_is_caught_and_reported(self, make_message):
        msg = self._msg(make_message, user_id=payment_handler.ADMIN_ID)

        fake_aiohttp = MagicMock()
        # Session() context manager itself raises → caught by the handler's try/except.
        fake_aiohttp.ClientSession = lambda: _FakeAiohttpSession(raise_on_get=RuntimeError("dns broke"))
        fake_aiohttp.ClientTimeout = lambda total: None

        with patch.object(payment_handler, "aiohttp", fake_aiohttp):
            await payment_handler.balance_handler(msg)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "dns broke" in text or "Ошибка" in text

"""Tests for bot/handlers/start.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bot.handlers import start as start_handler
from bot.keyboards import main_keyboard


class TestCmdStart:
    async def test_calls_ensure_user_and_log_event(self, make_message):
        msg = make_message(text="/start", user_id=42, username="bob")

        with patch.object(start_handler, "ensure_user") as ensure, \
             patch.object(start_handler, "log_event") as log_evt:
            await start_handler.cmd_start(msg)

        ensure.assert_called_once_with(42, "bob")
        log_evt.assert_called_once_with(42, "start")

    async def test_sends_greeting_with_main_keyboard(self, make_message):
        msg = make_message(text="/start")

        with patch.object(start_handler, "ensure_user"), \
             patch.object(start_handler, "log_event"):
            await start_handler.cmd_start(msg)

        assert msg.answer.await_count == 1
        sent_text, sent_kwargs = msg.answer.await_args.args, msg.answer.await_args.kwargs
        text = sent_text[0]
        assert "Привет" in text
        # Reply markup should be the main keyboard with 2 rows.
        kb = sent_kwargs["reply_markup"]
        assert len(kb.keyboard) == len(main_keyboard().keyboard)

    async def test_passes_username_none_when_missing(self, make_message):
        msg = make_message(text="/start", user_id=7, username=None)

        with patch.object(start_handler, "ensure_user") as ensure, \
             patch.object(start_handler, "log_event"):
            await start_handler.cmd_start(msg)

        ensure.assert_called_once_with(7, None)

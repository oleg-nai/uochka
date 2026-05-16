"""Tests for bot/handlers/report.py."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bot.handlers import report as report_handler


class TestOnReport:
    async def test_shows_reason_keyboard_for_toilet_id(self, make_callback):
        cb = make_callback(data="report:42")

        await report_handler.on_report(cb)

        # One answer to the message (reason picker).
        assert cb.message.answer.await_count == 1
        kb = cb.message.answer.await_args.kwargs["reply_markup"]
        # 3 reasons → 3 rows.
        assert len(kb.inline_keyboard) == 3
        # All callbacks carry the toilet id.
        for row in kb.inline_keyboard:
            assert row[0].callback_data.startswith("reason:42:")

    async def test_acknowledges_callback(self, make_callback):
        cb = make_callback(data="report:42")
        await report_handler.on_report(cb)
        cb.answer.assert_awaited_once()


class TestOnReason:
    async def test_persists_report_and_logs_event(self, make_callback):
        cb = make_callback(data="reason:42:closed", user_id=111, username="alice")

        with patch.object(report_handler, "ensure_user") as ensure, \
             patch.object(report_handler, "add_report") as add_rep, \
             patch.object(report_handler, "log_event") as log_evt:
            await report_handler.on_reason(cb)

        ensure.assert_called_once_with(111, "alice")
        add_rep.assert_called_once_with(42, 111, "closed")
        log_evt.assert_called_once_with(111, "report", {"toilet_id": 42, "reason": "closed"})

    @pytest.mark.parametrize(
        "reason,label",
        [
            ("closed", "закрыт"),
            ("not_exist", "не существует"),
            ("dirty", "очень грязно"),
        ],
    )
    async def test_response_uses_human_readable_label(self, make_callback, reason, label):
        cb = make_callback(data=f"reason:42:{reason}")

        with patch.object(report_handler, "ensure_user"), \
             patch.object(report_handler, "add_report"), \
             patch.object(report_handler, "log_event"):
            await report_handler.on_reason(cb)

        text = cb.message.answer.await_args.args[0]
        assert label in text

    async def test_unknown_reason_falls_back_to_raw_key(self, make_callback):
        cb = make_callback(data="reason:42:mystery")

        with patch.object(report_handler, "ensure_user"), \
             patch.object(report_handler, "add_report"), \
             patch.object(report_handler, "log_event"):
            await report_handler.on_reason(cb)

        text = cb.message.answer.await_args.args[0]
        assert "mystery" in text

    async def test_acknowledges_callback(self, make_callback):
        cb = make_callback(data="reason:42:closed")

        with patch.object(report_handler, "ensure_user"), \
             patch.object(report_handler, "add_report"), \
             patch.object(report_handler, "log_event"):
            await report_handler.on_reason(cb)

        cb.answer.assert_awaited_once()

    async def test_parses_toilet_id_as_int(self, make_callback):
        cb = make_callback(data="reason:9999:dirty")

        with patch.object(report_handler, "ensure_user"), \
             patch.object(report_handler, "add_report") as add_rep, \
             patch.object(report_handler, "log_event"):
            await report_handler.on_reason(cb)

        # First positional arg to add_report must be an int, not a string.
        args = add_rep.call_args.args
        assert args[0] == 9999
        assert isinstance(args[0], int)

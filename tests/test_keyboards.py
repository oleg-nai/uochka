"""Tests for bot/keyboards.py — every keyboard factory returns the right structure."""

from __future__ import annotations

import pytest
from aiogram.types import (
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)

from bot.keyboards import (
    main_keyboard,
    report_reason_keyboard,
    route_keyboard,
    share_location_keyboard,
    unlock_keyboard,
)


# ---------------------------------------------------------------------------
# route_keyboard
# ---------------------------------------------------------------------------


class TestRouteKeyboard:
    def test_returns_inline_keyboard(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_two_rows(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        assert len(kb.inline_keyboard) == 2

    def test_first_row_has_google_and_yandex(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        row = kb.inline_keyboard[0]
        assert len(row) == 2
        assert row[0].text == "Google Maps"
        assert row[1].text == "Яндекс Карты"

    def test_google_maps_url_embeds_coordinates(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        google_btn = kb.inline_keyboard[0][0]
        assert google_btn.url == "https://www.google.com/maps/dir/?api=1&destination=55.75,37.62"

    def test_yandex_maps_url_embeds_coordinates(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        yandex_btn = kb.inline_keyboard[0][1]
        assert yandex_btn.url == "https://yandex.ru/maps/?rtext=~55.75,37.62&rtt=auto"

    def test_report_button_has_toilet_id_in_callback(self):
        kb = route_keyboard(toilet_id=42, lat=55.75, lon=37.62)
        report_btn = kb.inline_keyboard[1][0]
        assert report_btn.text == "Сообщить о проблеме"
        assert report_btn.callback_data == "report:42"

    def test_negative_coordinates_passed_through(self):
        kb = route_keyboard(toilet_id=1, lat=-33.86, lon=-151.21)
        google_btn = kb.inline_keyboard[0][0]
        assert "-33.86" in google_btn.url
        assert "-151.21" in google_btn.url


# ---------------------------------------------------------------------------
# report_reason_keyboard
# ---------------------------------------------------------------------------


class TestReportReasonKeyboard:
    def test_returns_inline_keyboard(self):
        kb = report_reason_keyboard(toilet_id=7)
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_three_reason_rows(self):
        kb = report_reason_keyboard(toilet_id=7)
        assert len(kb.inline_keyboard) == 3

    @pytest.mark.parametrize(
        "row_idx,expected_label,expected_key",
        [
            (0, "Закрыт", "closed"),
            (1, "Не существует", "not_exist"),
            (2, "Очень грязно", "dirty"),
        ],
    )
    def test_each_reason_button_has_correct_text_and_callback(self, row_idx, expected_label, expected_key):
        kb = report_reason_keyboard(toilet_id=7)
        btn = kb.inline_keyboard[row_idx][0]
        assert btn.text == expected_label
        assert btn.callback_data == f"reason:7:{expected_key}"

    def test_toilet_id_propagated_to_all_buttons(self):
        kb = report_reason_keyboard(toilet_id=999)
        for row in kb.inline_keyboard:
            assert row[0].callback_data.startswith("reason:999:")


# ---------------------------------------------------------------------------
# share_location_keyboard
# ---------------------------------------------------------------------------


class TestShareLocationKeyboard:
    def test_returns_reply_keyboard(self):
        kb = share_location_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)

    def test_has_single_request_location_button(self):
        kb = share_location_keyboard()
        assert len(kb.keyboard) == 1
        assert len(kb.keyboard[0]) == 1
        btn = kb.keyboard[0][0]
        assert isinstance(btn, KeyboardButton)
        assert btn.text == "Отправить геолокацию"
        assert btn.request_location is True

    def test_is_resize_and_one_time(self):
        kb = share_location_keyboard()
        assert kb.resize_keyboard is True
        assert kb.one_time_keyboard is True


# ---------------------------------------------------------------------------
# main_keyboard
# ---------------------------------------------------------------------------


class TestMainKeyboard:
    def test_returns_reply_keyboard(self):
        kb = main_keyboard()
        assert isinstance(kb, ReplyKeyboardMarkup)

    def test_has_two_rows(self):
        kb = main_keyboard()
        assert len(kb.keyboard) == 2

    def test_find_toilet_button_requests_location(self):
        kb = main_keyboard()
        btn = kb.keyboard[0][0]
        assert btn.text == "📍 Найти туалет"
        assert btn.request_location is True

    def test_add_toilet_button_present(self):
        kb = main_keyboard()
        btn = kb.keyboard[1][0]
        assert btn.text == "➕ Добавить туалет"
        # Should NOT request location — it's a plain text trigger for the FSM.
        assert not btn.request_location

    def test_is_resize_but_not_one_time(self):
        kb = main_keyboard()
        assert kb.resize_keyboard is True
        # Main keyboard should persist; one_time would hide it after a tap.
        assert kb.one_time_keyboard is None or kb.one_time_keyboard is False


# ---------------------------------------------------------------------------
# unlock_keyboard
# ---------------------------------------------------------------------------


class TestUnlockKeyboard:
    def test_returns_inline_keyboard(self):
        kb = unlock_keyboard()
        assert isinstance(kb, InlineKeyboardMarkup)

    def test_has_single_buy_premium_button(self):
        kb = unlock_keyboard()
        assert len(kb.inline_keyboard) == 1
        assert len(kb.inline_keyboard[0]) == 1

    def test_buy_premium_button_has_correct_callback(self):
        kb = unlock_keyboard()
        btn = kb.inline_keyboard[0][0]
        assert btn.callback_data == "buy_premium"
        assert "звезда" in btn.text.lower() or "⭐" in btn.text

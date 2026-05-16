"""Tests for bot/handlers/location.py.

Behaviour under test:
  - Free users: limit = 1, unlock prompt shown after results.
  - Premium users: limit = 10, NO unlock prompt.
  - Empty results: friendly message, no unlock prompt, no toilet cards.
  - Each toilet card formats name/address/distance/paid label correctly.
  - log_event is called with results count and premium flag.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bot.handlers import location as location_handler


def _patches(toilets, user_record):
    """Helper to patch all 4 db boundary functions with single-call return values."""
    return (
        patch.object(location_handler, "ensure_user"),
        patch.object(location_handler, "get_user", return_value=user_record),
        patch.object(location_handler, "find_nearest_toilets", return_value=toilets),
        patch.object(location_handler, "log_event"),
    )


class TestLocationLimits:
    async def test_free_user_gets_limit_1(self, make_message, make_location):
        msg = make_message(location=make_location(55.75, 37.62), user_id=111)

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": False}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[]) as fnt, \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        # Third positional arg is the limit.
        fnt.assert_called_once_with(55.75, 37.62, 1)

    async def test_premium_user_gets_limit_10(self, make_message, make_location):
        msg = make_message(location=make_location(55.75, 37.62), user_id=111)

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[]) as fnt, \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        fnt.assert_called_once_with(55.75, 37.62, 10)

    async def test_missing_user_treated_as_free(self, make_message, make_location):
        # get_user returning None should be safe: limit defaults to 1.
        msg = make_message(location=make_location(0.0, 0.0))

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value=None), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[]) as fnt, \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        fnt.assert_called_once_with(0.0, 0.0, 1)


class TestLocationEmptyResults:
    async def test_no_toilets_message_for_free(self, make_message, make_location):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": False}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        # Single "nothing found" message, and no unlock prompt because we early-return.
        assert msg.answer.await_count == 1
        sent_text = msg.answer.await_args.args[0]
        assert "не найдено" in sent_text.lower() or "найдено" in sent_text.lower()

    async def test_no_toilets_no_unlock_prompt_for_free(self, make_message, make_location):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": False}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        # Verify no answer contained the unlock callback.
        for call in msg.answer.await_args_list:
            kb = call.kwargs.get("reply_markup")
            if kb is not None and hasattr(kb, "inline_keyboard"):
                for row in kb.inline_keyboard:
                    for btn in row:
                        assert btn.callback_data != "buy_premium"


class TestLocationWithResults:
    @pytest.fixture
    def sample_toilet(self):
        return {
            "id": 5,
            "lat": 55.75,
            "lon": 37.62,
            "distance_m": 120,
            "name": "Туалет у метро",
            "address": "ул. Тверская, 1",
            "is_paid": False,
        }

    async def test_free_user_with_results_gets_card_plus_unlock_plus_main(
        self, make_message, make_location, sample_toilet
    ):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": False}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[sample_toilet]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        # Expected message sequence: 1 toilet card + 1 unlock prompt + 1 "что дальше?" with main keyboard.
        assert msg.answer.await_count == 3
        # The 2nd message must carry the unlock_keyboard (inline buy_premium callback).
        unlock_call = msg.answer.await_args_list[1]
        kb = unlock_call.kwargs["reply_markup"]
        assert kb.inline_keyboard[0][0].callback_data == "buy_premium"

    async def test_premium_user_with_results_gets_card_plus_main_no_unlock(
        self, make_message, make_location, sample_toilet
    ):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[sample_toilet, sample_toilet]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        # Premium: 2 toilet cards + 1 "что дальше?" — NO unlock prompt.
        assert msg.answer.await_count == 3
        for call in msg.answer.await_args_list:
            kb = call.kwargs.get("reply_markup")
            if kb is not None and hasattr(kb, "inline_keyboard"):
                for row in kb.inline_keyboard:
                    for btn in row:
                        assert btn.callback_data != "buy_premium"

    async def test_card_text_contains_name_address_and_distance_meters(
        self, make_message, make_location, sample_toilet
    ):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[sample_toilet]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        card_call = msg.answer.await_args_list[0]
        text = card_call.args[0]
        assert "Туалет у метро" in text
        assert "ул. Тверская, 1" in text
        assert "120 м" in text
        assert "бесплатный" in text

    async def test_distance_over_1km_formatted_as_kilometers(
        self, make_message, make_location, sample_toilet
    ):
        far = {**sample_toilet, "distance_m": 2500}
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[far]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        card_text = msg.answer.await_args_list[0].args[0]
        assert "2.5 км" in card_text

    async def test_paid_toilet_label(self, make_message, make_location, sample_toilet):
        paid = {**sample_toilet, "is_paid": True}
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[paid]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        card_text = msg.answer.await_args_list[0].args[0]
        assert "платный" in card_text

    async def test_default_name_used_when_name_missing(self, make_message, make_location, sample_toilet):
        anon = {**sample_toilet, "name": None}
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[anon]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        card_text = msg.answer.await_args_list[0].args[0]
        assert "Очко" in card_text

    async def test_route_keyboard_attached_to_each_card(
        self, make_message, make_location, sample_toilet
    ):
        msg = make_message(location=make_location())

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=[sample_toilet]), \
             patch.object(location_handler, "log_event"):
            await location_handler.handle_location(msg)

        kb = msg.answer.await_args_list[0].kwargs["reply_markup"]
        # route_keyboard has 2 rows: maps row + report row.
        assert len(kb.inline_keyboard) == 2
        assert kb.inline_keyboard[1][0].callback_data == "report:5"


class TestLocationLogging:
    async def test_log_event_records_search_with_results_count(self, make_message, make_location):
        msg = make_message(location=make_location(), user_id=42)
        toilets = [{"id": 1, "lat": 0, "lon": 0, "distance_m": 10, "is_paid": False}]

        with patch.object(location_handler, "ensure_user"), \
             patch.object(location_handler, "get_user", return_value={"is_premium": True}), \
             patch.object(location_handler, "find_nearest_toilets", return_value=toilets), \
             patch.object(location_handler, "log_event") as log_evt:
            await location_handler.handle_location(msg)

        log_evt.assert_called_once()
        args = log_evt.call_args.args
        assert args[0] == 42
        assert args[1] == "search"
        assert args[2] == {"results": 1, "premium": True}

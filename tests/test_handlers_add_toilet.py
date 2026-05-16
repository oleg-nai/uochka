"""Tests for bot/handlers/add_toilet.py — FSM flow for adding a toilet."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from bot.handlers import add_toilet as add_toilet_handler
from bot.handlers.add_toilet import AddToiletForm


class TestCmdAdd:
    async def test_sets_state_to_waiting_location(self, make_message, fsm_state):
        msg = make_message(text="➕ Добавить туалет")

        await add_toilet_handler.cmd_add(msg, fsm_state)

        assert await fsm_state.get_state() == AddToiletForm.waiting_location

    async def test_prompts_user_with_share_location_keyboard(self, make_message, fsm_state):
        msg = make_message(text="/add")

        await add_toilet_handler.cmd_add(msg, fsm_state)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "геолокац" in text.lower()
        kb = msg.answer.await_args.kwargs["reply_markup"]
        # share_location_keyboard has exactly one request_location button.
        assert kb.keyboard[0][0].request_location is True


class TestGotLocation:
    async def test_saves_coordinates_to_fsm_data(self, make_message, make_location, fsm_state):
        msg = make_message(location=make_location(55.75, 37.62))
        await fsm_state.set_state(AddToiletForm.waiting_location)

        await add_toilet_handler.got_location(msg, fsm_state)

        data = await fsm_state.get_data()
        assert data["lat"] == 55.75
        assert data["lon"] == 37.62

    async def test_transitions_to_waiting_address(self, make_message, make_location, fsm_state):
        msg = make_message(location=make_location())
        await fsm_state.set_state(AddToiletForm.waiting_location)

        await add_toilet_handler.got_location(msg, fsm_state)

        assert await fsm_state.get_state() == AddToiletForm.waiting_address

    async def test_asks_for_address_and_removes_keyboard(self, make_message, make_location, fsm_state):
        msg = make_message(location=make_location())

        await add_toilet_handler.got_location(msg, fsm_state)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "адрес" in text.lower()
        kb = msg.answer.await_args.kwargs["reply_markup"]
        # ReplyKeyboardRemove instance carries remove_keyboard=True.
        assert getattr(kb, "remove_keyboard", False) is True


class TestGotAddress:
    async def test_saves_address_stripped(self, make_message, fsm_state):
        msg = make_message(text="  ул. Ленина, 5  ")
        await fsm_state.update_data(lat=55.75, lon=37.62)

        await add_toilet_handler.got_address(msg, fsm_state)

        data = await fsm_state.get_data()
        assert data["address"] == "ул. Ленина, 5"

    async def test_transitions_to_waiting_paid(self, make_message, fsm_state):
        msg = make_message(text="ул. Ленина, 5")

        await add_toilet_handler.got_address(msg, fsm_state)

        assert await fsm_state.get_state() == AddToiletForm.waiting_paid

    async def test_offers_paid_free_choice_keyboard(self, make_message, fsm_state):
        msg = make_message(text="ул. Ленина, 5")

        await add_toilet_handler.got_address(msg, fsm_state)

        kb = msg.answer.await_args.kwargs["reply_markup"]
        labels = [btn.text for btn in kb.keyboard[0]]
        assert "Бесплатный" in labels
        assert "Платный" in labels


class TestGotPaid:
    @pytest.mark.parametrize(
        "answer,expected_is_paid",
        [("Платный", True), ("Бесплатный", False)],
    )
    async def test_persists_toilet_with_correct_paid_flag(
        self, make_message, fsm_state, answer, expected_is_paid
    ):
        msg = make_message(text=answer, user_id=111, username="alice")
        await fsm_state.update_data(lat=55.75, lon=37.62, address="ул. Ленина, 5")

        with patch.object(add_toilet_handler, "ensure_user") as ensure, \
             patch.object(add_toilet_handler, "add_toilet") as add_t, \
             patch.object(add_toilet_handler, "log_event") as log_evt:
            await add_toilet_handler.got_paid(msg, fsm_state)

        ensure.assert_called_once_with(111, "alice")
        add_t.assert_called_once_with(
            lat=55.75, lon=37.62, name="Туалет", address="ул. Ленина, 5", is_paid=expected_is_paid,
        )
        log_evt.assert_called_once_with(
            111, "add_toilet", {"is_paid": expected_is_paid, "address": "ул. Ленина, 5"}
        )

    async def test_clears_state_after_save(self, make_message, fsm_state):
        msg = make_message(text="Бесплатный")
        await fsm_state.update_data(lat=0, lon=0, address="x")
        await fsm_state.set_state(AddToiletForm.waiting_paid)

        with patch.object(add_toilet_handler, "ensure_user"), \
             patch.object(add_toilet_handler, "add_toilet"), \
             patch.object(add_toilet_handler, "log_event"):
            await add_toilet_handler.got_paid(msg, fsm_state)

        assert await fsm_state.get_state() is None
        assert await fsm_state.get_data() == {}

    async def test_confirmation_message_uses_main_keyboard(self, make_message, fsm_state):
        msg = make_message(text="Бесплатный")
        await fsm_state.update_data(lat=0, lon=0, address="x")

        with patch.object(add_toilet_handler, "ensure_user"), \
             patch.object(add_toilet_handler, "add_toilet"), \
             patch.object(add_toilet_handler, "log_event"):
            await add_toilet_handler.got_paid(msg, fsm_state)

        msg.answer.assert_awaited_once()
        text = msg.answer.await_args.args[0]
        assert "добавлен" in text.lower() or "спасибо" in text.lower()
        kb = msg.answer.await_args.kwargs["reply_markup"]
        # main_keyboard has 2 rows: find + add buttons.
        assert len(kb.keyboard) == 2

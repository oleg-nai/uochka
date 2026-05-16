"""Tests for db/queries.py.

We mock the supabase client at the `get_client` boundary and verify:
  - which table / RPC was called,
  - what payload was passed,
  - that the returned shape matches what the caller expects.

We deliberately do NOT mock individual chained methods — we use a ChainableMock so the
fluent API just works, and we only assert on the calls and arguments that matter.
"""

from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from db import queries


# ---------------------------------------------------------------------------
# get_client
# ---------------------------------------------------------------------------


class TestGetClient:
    def test_creates_client_once_and_caches(self, monkeypatch):
        monkeypatch.setattr(queries, "_client", None)
        fake = object()
        create_mock = MagicMock(return_value=fake)
        monkeypatch.setattr(queries, "create_client", create_mock)

        c1 = queries.get_client()
        c2 = queries.get_client()

        assert c1 is fake
        assert c2 is fake
        # Cached: create_client must be called exactly once even across multiple get_client() calls.
        create_mock.assert_called_once_with("https://test.supabase.co", "test-key")


# ---------------------------------------------------------------------------
# find_nearest_toilets
# ---------------------------------------------------------------------------


class TestFindNearestToilets:
    def test_calls_rpc_with_correct_arguments(self, mock_supabase):
        mock_supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=[])

        queries.find_nearest_toilets(lat=55.75, lon=37.62, limit=5)

        mock_supabase.rpc.assert_called_once_with(
            "find_nearest_toilets",
            {"user_lat": 55.75, "user_lon": 37.62, "result_limit": 5},
        )

    def test_returns_data_list_when_present(self, mock_supabase):
        rows = [
            {"id": 1, "lat": 55.75, "lon": 37.62, "distance_m": 120, "name": "A"},
            {"id": 2, "lat": 55.76, "lon": 37.63, "distance_m": 800, "name": "B"},
        ]
        mock_supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=rows)

        result = queries.find_nearest_toilets(55.75, 37.62)

        assert result == rows

    def test_returns_empty_list_when_data_is_none(self, mock_supabase):
        # Supabase RPC may return data=None — function should normalize to [].
        mock_supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=None)

        result = queries.find_nearest_toilets(0, 0)

        assert result == []

    def test_default_limit_is_3(self, mock_supabase):
        mock_supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=[])

        queries.find_nearest_toilets(1.0, 2.0)

        args, kwargs = mock_supabase.rpc.call_args
        assert args[1]["result_limit"] == 3


# ---------------------------------------------------------------------------
# add_toilet
# ---------------------------------------------------------------------------


class TestAddToilet:
    def test_inserts_into_toilets_table_with_postgis_point(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[{"id": 7}]
        )

        result = queries.add_toilet(lat=55.75, lon=37.62, name="X", address="ул. 1", is_paid=True)

        mock_supabase.table.assert_called_with("toilets")
        insert_call = mock_supabase.table.return_value.insert
        # The single positional dict passed to .insert()
        payload = insert_call.call_args[0][0]
        # PostGIS expects lon-lat order in POINT().
        assert payload["location"] == "POINT(37.62 55.75)"
        assert payload["name"] == "X"
        assert payload["address"] == "ул. 1"
        assert payload["is_paid"] is True
        # New toilets must default to unverified.
        assert payload["verified"] is False
        assert result == {"id": 7}

    def test_returns_empty_dict_when_no_data_returned(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        result = queries.add_toilet(0, 0, "n", "a", False)

        assert result == {}

    def test_returns_empty_dict_when_data_is_none(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=None
        )

        result = queries.add_toilet(0, 0, "n", "a", False)

        assert result == {}


# ---------------------------------------------------------------------------
# add_report
# ---------------------------------------------------------------------------


class TestAddReport:
    def _setup_user_lookup(self, mock_supabase, user_data):
        """Configure the users-by-telegram-id lookup to return user_data."""
        users_table = MagicMock()
        users_table.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = (
            SimpleNamespace(data=user_data)
        )
        # We use side_effect on table() so we can serve different mocks for "users" vs "reports".
        reports_table = MagicMock()
        reports_table.insert.return_value.execute.return_value = SimpleNamespace(data=[])

        def table_side_effect(name):
            if name == "users":
                return users_table
            if name == "reports":
                return reports_table
            raise AssertionError(f"unexpected table {name}")

        mock_supabase.table.side_effect = table_side_effect
        # RPC for maybe_hide_toilet
        mock_supabase.rpc.return_value.execute.return_value = SimpleNamespace(data=None)
        return users_table, reports_table

    def test_inserts_report_and_calls_maybe_hide_toilet(self, mock_supabase):
        _users, reports_table = self._setup_user_lookup(mock_supabase, {"id": 42})

        queries.add_report(toilet_id=10, telegram_id=111, reason="closed")

        # The insert payload must reference internal user_id (42), not the telegram_id (111).
        insert_payload = reports_table.insert.call_args[0][0]
        assert insert_payload == {"toilet_id": 10, "user_id": 42, "reason": "closed"}

        # maybe_hide_toilet RPC must be triggered with the toilet id.
        mock_supabase.rpc.assert_called_once_with("maybe_hide_toilet", {"p_toilet_id": 10})

    def test_does_nothing_when_user_not_found(self, mock_supabase):
        _users, reports_table = self._setup_user_lookup(mock_supabase, None)

        queries.add_report(toilet_id=10, telegram_id=999, reason="dirty")

        # Critical: no report insert and no maybe_hide_toilet call if user is missing.
        reports_table.insert.assert_not_called()
        mock_supabase.rpc.assert_not_called()


# ---------------------------------------------------------------------------
# log_event
# ---------------------------------------------------------------------------


class TestLogEvent:
    def test_inserts_event_with_payload(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.log_event(111, "start", {"foo": "bar"})

        mock_supabase.table.assert_called_with("bot_events")
        payload = mock_supabase.table.return_value.insert.call_args[0][0]
        assert payload == {
            "telegram_id": 111,
            "event_type": "start",
            "payload": {"foo": "bar"},
        }

    def test_defaults_payload_to_empty_dict_when_none(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.log_event(111, "search")

        payload = mock_supabase.table.return_value.insert.call_args[0][0]
        assert payload["payload"] == {}

    def test_swallows_exceptions(self, mock_supabase):
        # Analytics failures must never crash callers (see commit c393418).
        mock_supabase.table.side_effect = RuntimeError("network down")

        # No exception should propagate.
        queries.log_event(111, "boom")

    def test_swallows_execute_exceptions(self, mock_supabase):
        mock_supabase.table.return_value.insert.return_value.execute.side_effect = RuntimeError("db error")

        queries.log_event(111, "boom")  # must not raise


# ---------------------------------------------------------------------------
# ensure_user
# ---------------------------------------------------------------------------


class TestEnsureUser:
    def test_upserts_user_with_on_conflict(self, mock_supabase):
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.ensure_user(telegram_id=111, username="alice")

        mock_supabase.table.assert_called_with("users")
        upsert_call = mock_supabase.table.return_value.upsert
        payload = upsert_call.call_args[0][0]
        kwargs = upsert_call.call_args[1]
        assert payload == {"telegram_id": 111, "username": "alice"}
        # on_conflict must be telegram_id so re-running /start doesn't create duplicates.
        assert kwargs.get("on_conflict") == "telegram_id"

    def test_accepts_none_username(self, mock_supabase):
        mock_supabase.table.return_value.upsert.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.ensure_user(telegram_id=111, username=None)

        payload = mock_supabase.table.return_value.upsert.call_args[0][0]
        assert payload["username"] is None


# ---------------------------------------------------------------------------
# get_user
# ---------------------------------------------------------------------------


class TestGetUser:
    def test_returns_user_data_when_found(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
            data={"id": 1, "telegram_id": 111, "is_premium": True, "premium_since": "2026-01-01"}
        )

        result = queries.get_user(111)

        mock_supabase.table.assert_called_with("users")
        assert result == {
            "id": 1,
            "telegram_id": 111,
            "is_premium": True,
            "premium_since": "2026-01-01",
        }

    def test_queries_by_telegram_id(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
            data=None
        )

        queries.get_user(555)

        eq_call = mock_supabase.table.return_value.select.return_value.eq
        eq_call.assert_called_with("telegram_id", 555)

    def test_returns_none_when_user_missing(self, mock_supabase):
        mock_supabase.table.return_value.select.return_value.eq.return_value.maybe_single.return_value.execute.return_value = SimpleNamespace(
            data=None
        )

        assert queries.get_user(999) is None


# ---------------------------------------------------------------------------
# set_premium
# ---------------------------------------------------------------------------


class TestSetPremium:
    def test_updates_is_premium_true_and_timestamp(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.set_premium(telegram_id=111)

        mock_supabase.table.assert_called_with("users")
        update_call = mock_supabase.table.return_value.update
        payload = update_call.call_args[0][0]
        assert payload["is_premium"] is True
        assert "premium_since" in payload
        # The timestamp should be ISO 8601 parseable.
        datetime.fromisoformat(payload["premium_since"])

    def test_filters_by_telegram_id(self, mock_supabase):
        mock_supabase.table.return_value.update.return_value.eq.return_value.execute.return_value = SimpleNamespace(
            data=[]
        )

        queries.set_premium(telegram_id=42)

        eq_call = mock_supabase.table.return_value.update.return_value.eq
        eq_call.assert_called_with("telegram_id", 42)

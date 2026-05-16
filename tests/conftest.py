"""Shared test fixtures.

Strategy:
- Never hit the real Supabase or Telegram API.
- Set required env vars (SUPABASE_URL/KEY, BOT_TOKEN) at import time so modules that
  read them on import don't blow up. These values are placeholders — every real call
  to the Supabase client is mocked at the `db.queries.get_client` boundary.
- Provide a `mock_supabase` fixture that returns a chainable Mock whose terminal
  `.execute()` returns whatever `.data` we configure.
- Reset the module-level `_client` cache between tests so each test gets a fresh
  mocked client.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

# Ensure project root is on sys.path before importing project modules.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Set env vars BEFORE importing db.queries / bot modules so import-time access doesn't crash.
os.environ.setdefault("SUPABASE_URL", "https://test.supabase.co")
os.environ.setdefault("SUPABASE_KEY", "test-key")
os.environ.setdefault("BOT_TOKEN", "0:test-bot-token")

import pytest

from db import queries as db_queries


# ---------------------------------------------------------------------------
# Supabase client mocks
# ---------------------------------------------------------------------------


def _make_execute_result(data):
    """Mimic supabase-py response object: an object with a `.data` attribute."""
    return SimpleNamespace(data=data)


class ChainableMock(MagicMock):
    """A MagicMock whose every attribute/call returns another ChainableMock by default.

    This lets us mimic the supabase-py fluent API (`client.table(x).select(y).eq(z).execute()`)
    without configuring every step. The terminal `.execute()` is overridden per test to return
    a SimpleNamespace(data=...).
    """

    def _get_child_mock(self, /, **kw):
        # Return a ChainableMock for any auto-generated child so chained attribute access keeps working.
        kw.pop("_new_name", None)
        kw.pop("_new_parent", None)
        return ChainableMock()


@pytest.fixture
def mock_supabase(monkeypatch):
    """Replace `db.queries.get_client` with a chainable mock and reset the cached client.

    Returns the mock client. Tests configure `.execute.return_value` on whatever
    chain they expect (e.g., `mock_supabase.table.return_value.insert.return_value.execute.return_value = ...`).
    """
    # Reset the cached client so a previous test's mock doesn't leak.
    monkeypatch.setattr(db_queries, "_client", None)

    client = ChainableMock()
    monkeypatch.setattr(db_queries, "get_client", lambda: client)
    return client


# ---------------------------------------------------------------------------
# Telegram object factories
# ---------------------------------------------------------------------------


@pytest.fixture
def make_user():
    """Factory that builds a lightweight User-like object for tests."""
    def _make(user_id: int = 111, username: str | None = "tester"):
        return SimpleNamespace(id=user_id, username=username, is_bot=False, first_name="T")
    return _make


@pytest.fixture
def make_message(make_user):
    """Factory that builds a Message-like object with AsyncMock for `.answer` / `.answer_invoice`."""
    def _make(
        text: str | None = None,
        location=None,
        successful_payment=None,
        user_id: int = 111,
        username: str | None = "tester",
    ):
        msg = MagicMock()
        msg.from_user = make_user(user_id, username)
        msg.text = text
        msg.location = location
        msg.successful_payment = successful_payment
        msg.answer = AsyncMock()
        msg.answer_invoice = AsyncMock()
        return msg
    return _make


@pytest.fixture
def make_callback(make_user, make_message):
    """Factory for CallbackQuery-like object with AsyncMock for `.answer` and a fake `.message`."""
    def _make(data: str, user_id: int = 111, username: str | None = "tester"):
        cb = MagicMock()
        cb.from_user = make_user(user_id, username)
        cb.data = data
        cb.message = make_message(user_id=user_id, username=username)
        cb.answer = AsyncMock()
        return cb
    return _make


@pytest.fixture
def make_location():
    def _make(lat: float = 55.75, lon: float = 37.62):
        return SimpleNamespace(latitude=lat, longitude=lon)
    return _make


@pytest.fixture
def fsm_state():
    """Minimal in-memory stand-in for aiogram FSMContext.

    Implements `get_data`, `update_data`, `set_state`, `get_state`, `clear` as async methods.
    """
    class _State:
        def __init__(self):
            self._data: dict = {}
            self._state = None

        async def get_data(self):
            return dict(self._data)

        async def update_data(self, **kwargs):
            self._data.update(kwargs)
            return dict(self._data)

        async def set_state(self, state):
            self._state = state

        async def get_state(self):
            return self._state

        async def clear(self):
            self._data.clear()
            self._state = None

    return _State()

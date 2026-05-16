import os
from datetime import datetime, timezone

from supabase import create_client, Client

_client: Client | None = None


def get_client() -> Client:
    global _client
    if _client is None:
        _client = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client


def find_nearest_toilets(lat: float, lon: float, limit: int = 3) -> list[dict]:
    client = get_client()
    result = client.rpc(
        "find_nearest_toilets",
        {"user_lat": lat, "user_lon": lon, "result_limit": limit},
    ).execute()
    return result.data or []


def add_toilet(lat: float, lon: float, name: str, address: str, is_paid: bool) -> dict:
    client = get_client()
    result = (
        client.table("toilets")
        .insert({
            "location": f"POINT({lon} {lat})",
            "name": name,
            "address": address,
            "is_paid": is_paid,
            "verified": False,
        })
        .execute()
    )
    return result.data[0] if result.data else {}


def add_report(toilet_id: int, telegram_id: int, reason: str) -> None:
    client = get_client()

    user = (
        client.table("users")
        .select("id")
        .eq("telegram_id", telegram_id)
        .maybe_single()
        .execute()
    )
    if not user.data:
        return

    user_id = user.data["id"]

    client.table("reports").insert({
        "toilet_id": toilet_id,
        "user_id": user_id,
        "reason": reason,
    }).execute()

    client.rpc("maybe_hide_toilet", {"p_toilet_id": toilet_id}).execute()


def log_event(telegram_id: int, event_type: str, payload: dict | None = None) -> None:
    try:
        get_client().table("bot_events").insert({
            "telegram_id": telegram_id,
            "event_type": event_type,
            "payload": payload or {},
        }).execute()
    except Exception:
        pass


def ensure_user(telegram_id: int, username: str | None) -> None:
    client = get_client()
    client.table("users").upsert(
        {"telegram_id": telegram_id, "username": username},
        on_conflict="telegram_id",
    ).execute()


def get_user(telegram_id: int) -> dict | None:
    client = get_client()
    result = (
        client.table("users")
        .select("id, telegram_id, is_premium, premium_since")
        .eq("telegram_id", telegram_id)
        .maybe_single()
        .execute()
    )
    return result.data


def set_premium(telegram_id: int) -> None:
    client = get_client()
    client.table("users").update({
        "is_premium": True,
        "premium_since": datetime.now(timezone.utc).isoformat(),
    }).eq("telegram_id", telegram_id).execute()

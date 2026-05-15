import os
import time
import requests
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

OVERPASS_URL = "https://overpass-api.de/api/interpreter"

# Чуть шире bbox чтобы захватить пригороды
QUERY = """
[out:json][timeout:90];
(
  node["amenity"="toilets"](53.78,27.35,54.00,27.75);
  way["amenity"="toilets"](53.78,27.35,54.00,27.75);
  relation["amenity"="toilets"](53.78,27.35,54.00,27.75);
);
out center tags;
"""
HEADERS = {"User-Agent": "ToiletBot/1.0 (seed script, contact: github)"}


def fetch_toilets():
    r = requests.get(OVERPASS_URL, params={"data": QUERY}, headers=HEADERS, timeout=120)
    r.raise_for_status()
    return r.json()["elements"]


def build_name(tags: dict) -> str:
    if tags.get("name"):
        return tags["name"]
    parts = []
    operator = tags.get("operator")
    description = tags.get("description")
    if description:
        return description
    unisex = tags.get("unisex", "")
    male = tags.get("male", "")
    female = tags.get("female", "")

    if unisex == "yes" or (male == "yes" and female == "yes"):
        parts.append("Общий туалет")
    elif male == "yes":
        parts.append("Мужской туалет")
    elif female == "yes":
        parts.append("Женский туалет")
    else:
        parts.append("Общественный туалет")

    if operator:
        parts.append(f"({operator})")
    return " ".join(parts)


def build_address(tags: dict) -> str | None:
    street = tags.get("addr:street", "")
    house = tags.get("addr:housenumber", "")
    suburb = tags.get("addr:suburb", "") or tags.get("addr:district", "")
    city = tags.get("addr:city", "")

    line1 = (street + (" " + house if house else "")).strip()
    parts = [p for p in [line1, suburb, city] if p]
    return ", ".join(parts) or None


def build_hours(tags: dict) -> str | None:
    raw = tags.get("opening_hours")
    if not raw:
        return None
    # Нормализуем распространённые OSM-сокращения для читабельности
    return (
        raw.replace("Mo-Su", "Пн-Вс")
           .replace("Mo-Fr", "Пн-Пт")
           .replace("Sa-Su", "Сб-Вс")
           .replace("24/7", "Круглосуточно")
    )


def to_row(el: dict) -> dict | None:
    lat = el.get("lat") or el.get("center", {}).get("lat")
    lon = el.get("lon") or el.get("center", {}).get("lon")
    if not lat or not lon:
        return None

    tags = el.get("tags", {})

    fee = tags.get("fee", "").lower()
    is_paid = fee in ("yes", "платно", "платный")

    return {
        "location": f"POINT({lon} {lat})",
        "name": build_name(tags),
        "address": build_address(tags),
        "is_paid": is_paid,
        "is_accessible": tags.get("wheelchair", "") == "yes",
        "working_hours": build_hours(tags),
        "verified": True,
    }


def main():
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    print("Fetching from Overpass API...")
    elements = fetch_toilets()
    print(f"Found {len(elements)} elements in OSM")

    rows = [r for el in elements if (r := to_row(el))]
    print(f"Valid rows: {len(rows)}")

    # upsert по геопозиции — не будет дублей при повторном запуске
    for i in range(0, len(rows), 50):
        batch = rows[i : i + 50]
        client.table("toilets").upsert(batch, on_conflict="location").execute()
        print(f"  Upserted {i + len(batch)}/{len(rows)}")
        time.sleep(0.3)

    print("Done!")


if __name__ == "__main__":
    main()

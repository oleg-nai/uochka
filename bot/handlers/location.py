import asyncio
import logging

from aiogram import Router, F
from aiogram.types import Message

from bot.keyboards import main_keyboard, route_keyboard
from db.queries import ensure_user, find_nearest_toilets, log_event

router = Router()
logger = logging.getLogger(__name__)

PAID_LABEL = {"True": "платный", "False": "бесплатный", True: "платный", False: "бесплатный"}


@router.message(F.location)
async def handle_location(message: Message) -> None:
    tg_id = message.from_user.id
    await asyncio.to_thread(ensure_user, tg_id, message.from_user.username)

    lat = message.location.latitude
    lon = message.location.longitude

    toilets = await asyncio.to_thread(find_nearest_toilets, lat, lon)

    await asyncio.to_thread(log_event, tg_id, "search", {"results": len(toilets)})
    logger.info(
        "user %s searched, found %d toilets",
        tg_id, len(toilets),
        extra={"tags": {"event_type": "search"}},
    )

    if not toilets:
        await message.answer("Рядом туалетов не найдено. Можешь добавить!", reply_markup=main_keyboard())
        return

    for t in toilets:
        distance_m = int(t.get("distance_m", 0))
        distance_str = f"{distance_m} м" if distance_m < 1000 else f"{distance_m / 1000:.1f} км"
        paid_str = PAID_LABEL.get(t.get("is_paid"), "неизвестно")
        name = t.get("name") or "Очко"
        address = t.get("address") or "адрес неизвестен"

        text = (
            f"🚻 <b>{name}</b>\n"
            f"📍 {address}\n"
            f"📏 {distance_str} · {paid_str}"
        )
        await message.answer(
            text,
            parse_mode="HTML",
            reply_markup=route_keyboard(t["id"], t["lat"], t["lon"]),
        )

    await message.answer("Что дальше?", reply_markup=main_keyboard())

from aiogram import Router, F
from aiogram.types import Message
from bot.keyboards import route_keyboard
from db.queries import find_nearest_toilets, ensure_user

router = Router()

PAID_LABEL = {"True": "платный", "False": "бесплатный", True: "платный", False: "бесплатный"}


@router.message(F.location)
async def handle_location(message: Message) -> None:
    ensure_user(message.from_user.id, message.from_user.username)

    lat = message.location.latitude
    lon = message.location.longitude

    toilets = find_nearest_toilets(lat, lon)

    if not toilets:
        await message.answer("Рядом туалетов не найдено. Можешь добавить — /add")
        return

    for t in toilets:
        distance_m = int(t.get("distance_m", 0))
        distance_str = f"{distance_m} м" if distance_m < 1000 else f"{distance_m / 1000:.1f} км"
        paid_str = PAID_LABEL.get(t.get("is_paid"), "неизвестно")
        name = t.get("name") or "Туалет"
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

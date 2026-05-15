from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.keyboards import share_location_keyboard
from db.queries import ensure_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    ensure_user(message.from_user.id, message.from_user.username)
    await message.answer(
        "Привет! Я помогу найти ближайший туалет.\n\n"
        "Отправь свою геолокацию — покажу 5 ближайших точек.",
        reply_markup=share_location_keyboard(),
    )

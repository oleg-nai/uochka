import asyncio
from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from bot.keyboards import main_keyboard
from db.queries import ensure_user

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    await asyncio.to_thread(ensure_user, message.from_user.id, message.from_user.username)
    await message.answer(
        "Привет! Я помогу найти ближайший туалет.\n\n"
        "Нажми кнопку ниже, чтобы найти туалеты рядом или добавить новый.",
        reply_markup=main_keyboard(),
    )

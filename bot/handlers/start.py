import asyncio
import logging

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from bot.keyboards import main_keyboard
from db.queries import ensure_user, log_event

router = Router()
logger = logging.getLogger(__name__)


@router.message(CommandStart())
async def cmd_start(message: Message) -> None:
    tg_id = message.from_user.id
    await asyncio.to_thread(ensure_user, tg_id, message.from_user.username)
    await asyncio.to_thread(log_event, tg_id, "start")
    logger.info("user %s started", tg_id, extra={"tags": {"event_type": "start"}})
    await message.answer(
        "Привет! Я помогу найти ближайший туалет.\n\n"
        "Нажми кнопку ниже, чтобы найти туалеты рядом или добавить новый.",
        reply_markup=main_keyboard(),
    )

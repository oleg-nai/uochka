import asyncio
import logging

from aiogram import Router, F
from aiogram.types import CallbackQuery

from bot.keyboards import report_reason_keyboard
from db.queries import add_report, ensure_user, log_event

router = Router()
logger = logging.getLogger(__name__)

REASON_LABELS = {
    "closed": "закрыт",
    "not_exist": "не существует",
    "dirty": "очень грязно",
}


@router.callback_query(F.data.startswith("report:"))
async def on_report(callback: CallbackQuery) -> None:
    toilet_id = int(callback.data.split(":")[1])
    await callback.message.answer(
        "Выбери причину жалобы:",
        reply_markup=report_reason_keyboard(toilet_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("reason:"))
async def on_reason(callback: CallbackQuery) -> None:
    _, toilet_id_str, reason = callback.data.split(":")
    toilet_id = int(toilet_id_str)
    tg_id = callback.from_user.id

    await asyncio.to_thread(ensure_user, tg_id, callback.from_user.username)
    await asyncio.to_thread(add_report, toilet_id, tg_id, reason)

    await asyncio.to_thread(log_event, tg_id, "report", {"toilet_id": toilet_id, "reason": reason})
    logger.info(
        "user %s reported toilet %d: %s",
        tg_id, toilet_id, reason,
        extra={"tags": {"event_type": "report"}},
    )

    label = REASON_LABELS.get(reason, reason)
    await callback.message.answer(f"Жалоба принята: «{label}». Спасибо!")
    await callback.answer()

import asyncio
from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.keyboards import report_reason_keyboard
from db.queries import add_report, ensure_user

router = Router()

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

    await asyncio.to_thread(ensure_user, callback.from_user.id, callback.from_user.username)
    await asyncio.to_thread(add_report, toilet_id, callback.from_user.id, reason)

    label = REASON_LABELS.get(reason, reason)
    await callback.message.answer(f"Жалоба принята: «{label}». Спасибо!")
    await callback.answer()

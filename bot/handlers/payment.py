import asyncio
import logging

from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery

from bot.keyboards import unlock_keyboard
from db.queries import get_user, log_event, set_premium

router = Router()
logger = logging.getLogger(__name__)

STARS_PRICE = 1


@router.callback_query(F.data == "buy_premium")
async def buy_premium_handler(query: CallbackQuery) -> None:
    tg_id = query.from_user.id
    await query.answer()

    user = await asyncio.to_thread(get_user, tg_id)
    if user and user.get("is_premium"):
        await query.message.answer("У тебя уже есть Premium!")
        return

    await query.message.answer_invoice(
        title="Уочка Premium",
        description="Все туалеты в радиусе 5 км навсегда",
        payload=f"premium:{tg_id}",
        currency="XTR",
        prices=[LabeledPrice(label="Уочка Premium", amount=STARS_PRICE)],
    )


@router.pre_checkout_query()
async def pre_checkout_handler(query: PreCheckoutQuery) -> None:
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment_handler(message: Message) -> None:
    tg_id = message.from_user.id
    stars = message.successful_payment.total_amount
    await asyncio.to_thread(set_premium, tg_id)
    await asyncio.to_thread(log_event, tg_id, "premium_activated", {"stars": stars})
    logger.info("user %s activated premium via %d stars", tg_id, stars)
    await message.answer(
        "🎉 <b>Premium активирован!</b>\n\n"
        "Теперь ты видишь все туалеты рядом.\n"
        "Отправь геолокацию чтобы проверить!",
        parse_mode="HTML",
    )


@router.message(Command("premium"))
async def premium_status_handler(message: Message) -> None:
    tg_id = message.from_user.id
    user = await asyncio.to_thread(get_user, tg_id)
    if user and user.get("is_premium"):
        await message.answer("💎 У тебя уже есть Premium! Все туалеты в радиусе 5 км доступны.")
    else:
        await message.answer(
            "💎 <b>Уочка Premium</b>\n\n"
            "Видь все туалеты в радиусе 5 км навсегда за <b>1 ⭐️</b>.",
            parse_mode="HTML",
            reply_markup=unlock_keyboard(),
        )

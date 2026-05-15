import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from bot.keyboards import share_location_keyboard, main_keyboard
from db.queries import add_toilet, ensure_user

router = Router()


class AddToiletForm(StatesGroup):
    waiting_location = State()
    waiting_address = State()
    waiting_paid = State()


@router.message(Command("add"))
@router.message(F.text == "➕ Добавить туалет")
async def cmd_add(message: Message, state: FSMContext) -> None:
    await state.set_state(AddToiletForm.waiting_location)
    await message.answer(
        "Добавляем новый туалет. Отправь геолокацию места.",
        reply_markup=share_location_keyboard(),
    )


@router.message(AddToiletForm.waiting_location, F.location)
async def got_location(message: Message, state: FSMContext) -> None:
    await state.update_data(lat=message.location.latitude, lon=message.location.longitude)
    await state.set_state(AddToiletForm.waiting_address)
    await message.answer("Напиши адрес (улица и номер дома):", reply_markup=ReplyKeyboardRemove())


@router.message(AddToiletForm.waiting_address, F.text)
async def got_address(message: Message, state: FSMContext) -> None:
    await state.update_data(address=message.text.strip())
    await state.set_state(AddToiletForm.waiting_paid)
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Бесплатный"), KeyboardButton(text="Платный")]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )
    await message.answer("Платный или бесплатный?", reply_markup=kb)


@router.message(AddToiletForm.waiting_paid, F.text.in_({"Бесплатный", "Платный"}))
async def got_paid(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    is_paid = message.text == "Платный"

    await asyncio.to_thread(ensure_user, message.from_user.id, message.from_user.username)
    await asyncio.to_thread(
        add_toilet,
        lat=data["lat"],
        lon=data["lon"],
        name="Туалет",
        address=data["address"],
        is_paid=is_paid,
    )

    await state.clear()
    await message.answer("Туалет добавлен! Спасибо.", reply_markup=main_keyboard())

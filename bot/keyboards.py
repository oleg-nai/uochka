from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
)


def route_keyboard(toilet_id: int, lat: float, lon: float) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="Google Maps",
                url=f"https://www.google.com/maps/dir/?api=1&destination={lat},{lon}",
            ),
            InlineKeyboardButton(
                text="Яндекс Карты",
                url=f"https://yandex.ru/maps/?rtext=~{lat},{lon}&rtt=auto",
            ),
        ],
        [
            InlineKeyboardButton(
                text="Сообщить о проблеме",
                callback_data=f"report:{toilet_id}",
            ),
        ],
    ])


def report_reason_keyboard(toilet_id: int) -> InlineKeyboardMarkup:
    reasons = [
        ("Закрыт", "closed"),
        ("Не существует", "not_exist"),
        ("Очень грязно", "dirty"),
    ]
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=label, callback_data=f"reason:{toilet_id}:{key}")]
        for label, key in reasons
    ])


def share_location_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Отправить геолокацию", request_location=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )

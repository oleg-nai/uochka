from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from bot.handlers import start, location, add_toilet, report


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)
    dp.include_router(add_toilet.router)
    dp.include_router(report.router)
    dp.include_router(location.router)
    return dp

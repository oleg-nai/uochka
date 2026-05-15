import asyncio
import os

from aiogram import Bot
from dotenv import load_dotenv

from bot.app import create_dispatcher

load_dotenv()


async def main() -> None:
    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

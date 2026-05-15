import asyncio
import logging
import os

from aiogram import Bot
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)

if os.getenv("LOKI_URL"):
    import logging_loki
    from multiprocessing import Queue
    loki_handler = logging_loki.LokiQueueHandler(
        Queue(-1),
        url=f"{os.environ['LOKI_URL']}/loki/api/v1/push",
        tags={"app": "toilet-bot"},
        auth=(os.environ["LOKI_USERNAME"], os.environ["LOKI_PASSWORD"]),
        version="1",
    )
    logging.getLogger().addHandler(loki_handler)

from bot.app import create_dispatcher

logger = logging.getLogger(__name__)


async def main() -> None:
    bot = Bot(token=os.environ["BOT_TOKEN"])
    dp = create_dispatcher()
    logger.info("bot starting")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

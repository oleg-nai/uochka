import asyncio
import json
import os
from http.server import BaseHTTPRequestHandler

from aiogram import Bot
from aiogram.types import Update
from dotenv import load_dotenv

load_dotenv()

from bot.app import create_dispatcher

BOT_TOKEN = os.environ["BOT_TOKEN"]
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")

_dp = create_dispatcher()


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        secret = self.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
        if WEBHOOK_SECRET and secret != WEBHOOK_SECRET:
            self.send_response(403)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        try:
            update_data = json.loads(body)
        except json.JSONDecodeError:
            self.send_response(400)
            self.end_headers()
            return

        asyncio.run(self._process(update_data))

        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(b"{}")

    async def _process(self, update_data: dict) -> None:
        bot = Bot(token=BOT_TOKEN)
        try:
            update = Update(**update_data)
            await _dp.feed_update(bot, update)
        finally:
            await bot.session.close()

    def log_message(self, *args):
        pass

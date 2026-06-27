import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
import os

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

FUEL_PRICES = {
    "АИ-92": 51.30,
    "АИ-95": 55.80,
    "АИ-98": 63.40,
    "ДТ": 60.10,
}

def format_message():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    lines = ["⛽ *Цены на топливо в России*", f"📅 {now}\n"]
    for fuel, price in FUEL_PRICES.items():
        lines.append(f"🔹 {fuel}: *{price:.2f} ₽/л*")
    return "\n".join(lines)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⛽ Бот цен на топливо\n\n/prices — текущие цены")

@dp.message(Command("prices"))
async def prices(message: types.Message):
    await message.answer(format_message(), parse_mode="Markdown")

async def post_to_channel():
    await bot.send_message(CHANNEL_ID, format_message(), parse_mode="Markdown")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(post_to_channel, "cron", hour=9, minute=0)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

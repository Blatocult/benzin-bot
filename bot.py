import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")
DGIS_KEY = os.environ.get("DGIS_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

CITIES = {
    "Москва": "37.6173,55.7558",
    "Санкт-Петербург": "30.3351,59.9343",
    "Новосибирск": "82.9346,55.0084",
    "Екатеринбург": "60.6122,56.8519",
    "Казань": "49.1221,55.7887",
}

async def get_stations(lon_lat):
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": "АЗС",
        "point": lon_lat,
        "radius": 5000,
        "type": "branch",
        "key": DGIS_KEY,
        "page_size": 3,
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                data = await resp.json()
                return data.get("result", {}).get("items", [])
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        return []

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *АЗС по России* | {now}\n\n"
    
    for city, coords in CITIES.items():
        stations = await get_stations(coords)
        if stations:
            message += f"📍 *{city}*\n"
            for s in stations:
                name = s.get("name_ex", {}).get("primary", s.get("name", "АЗС"))
                addr = s.get("address_name", "")
                message += f"  • {name} — {addr}\n"
        else:
            message += f"📍 *{city}* — нет данных\n"
        message += "\n"
    
    await bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⛽ Бот поиска АЗС\n\n/stations — найти АЗС по городам")

@dp.message(Command("stations"))
async def stations_cmd(message: types.Message):
    await message.answer("🔍 Ищу АЗС...")
    await post_to_channel()
    await message.answer("✅ Готово! Проверьте канал.")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(post_to_channel, "interval", minutes=30)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


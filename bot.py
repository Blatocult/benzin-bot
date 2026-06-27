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

REGIONS = [
    "Москва", "Санкт-Петербург", "Новосибирск", "Екатеринбург",
    "Казань", "Краснодар", "Ростов-на-Дону", "Уфа", "Самара", "Омск"
]

async def get_gas_stations(city):
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": "АЗС бензин",
        "location": city,
        "type": "branch",
        "key": DGIS_KEY,
        "fields": "items.point,items.address,items.name_ex",
        "page_size": 5,
    }
    async with aiohttp.ClientSession() as session:
        async with session.get(url, params=params) as resp:
            data = await resp.json()
            items = data.get("result", {}).get("items", [])
            return items

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *АЗС по России* | {now}\n\n"
    
    for city in REGIONS:
        stations = await get_gas_stations(city)
        if stations:
            message += f"📍 *{city}*\n"
            for s in stations[:3]:
                name = s.get("name_ex", {}).get("primary", "АЗС")
                addr = s.get("address", {}).get("building_name", "")
                message += f"  • {name} — {addr}\n"
            message += "\n"
    
    await bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⛽ Бот поиска АЗС\n\n/stations — найти АЗС")

@dp.message(Command("stations"))
async def stations(message: types.Message):
    await message.answer("🔍 Ищу АЗС по городам...")
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

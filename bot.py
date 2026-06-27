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
    "🌴 Краснодарский край": {
        "Краснодар": "38.9760,45.0360",
        "Сочи": "39.7257,43.5992",
        "Новороссийск": "37.7686,44.7237",
        "Армавир": "41.1236,44.9896",
        "Анапа": "37.3167,44.8953",
    },
    "🌾 Ставропольский край": {
        "Ставрополь": "41.9734,45.0428",
        "Пятигорск": "43.0597,44.0496",
        "Кисловодск": "42.7167,43.9000",
        "Невинномысск": "41.9380,44.6349",
    },
    "🌻 Ростовская область": {
        "Ростов-на-Дону": "39.7015,47.2357",
        "Таганрог": "38.8969,47.2090",
        "Шахты": "40.2158,47.7081",
        "Новочеркасск": "40.1126,47.4135",
    },
}

async def get_stations(lon_lat, city_name):
    url = "https://catalog.api.2gis.com/3.0/items"
    params = {
        "q": "автозаправочная станция",
        "point": lon_lat,
        "radius": 10000,
        "key": DGIS_KEY,
        "page_size": 5,
        "locale": "ru_RU",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("result", {}).get("items", [])
    except Exception as e:
        logging.error(f"Ошибка {city_name}: {e}")
    return []

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *АЗС — Юг России*\n📅 {now}\n\n"

    for region, cities in CITIES.items():
        message += f"*{region}*\n"
        for city, coords in cities.items():
            stations = await get_stations(coords, city)
            if stations:
                message += f"  📍 *{city}*\n"
                for s in stations[:3]:
                    name = s.get("name_ex", {}).get("primary", s.get("name", "АЗС"))
                    addr = s.get("address_name", "")
                    message += f"    • {name} — {addr}\n"
            else:
                message += f"  📍 *{city}* — нет данных\n"
        message += "\n"

    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        await bot.send_message(CHANNEL_ID, chunk, parse_mode="Markdown")
        await asyncio.sleep(1)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⛽ Бот АЗС — Юг России\n\n/stations — найти АЗС")

@dp.message(Command("stations"))
async def stations_cmd(message: types.Message):
    await message.answer("🔍 Ищу АЗС по регионам...")
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


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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

CITIES = {
    "🌴 Краснодарский край": {
        "Краснодар": (45.0360, 38.9760),
        "Сочи": (43.5992, 39.7257),
        "Новороссийск": (44.7237, 37.7686),
        "Армавир": (44.9896, 41.1236),
        "Анапа": (44.8953, 37.3167),
    },
    "🌾 Ставропольский край": {
        "Ставрополь": (45.0428, 41.9734),
        "Пятигорск": (44.0496, 43.0597),
        "Кисловодск": (43.9000, 42.7167),
        "Невинномысск": (44.6349, 41.9380),
    },
    "🌻 Ростовская область": {
        "Ростов-на-Дону": (47.2357, 39.7015),
        "Таганрог": (47.2090, 38.8969),
        "Шахты": (47.7081, 40.2158),
        "Новочеркасск": (47.4135, 40.1126),
    },
}

async def get_stations_osm(lat, lon, city):
    query = f"""
    [out:json][timeout:10];
    node["amenity"="fuel"](around:5000,{lat},{lon});
    out 5;
    """
    url = "https://overpass-api.de/api/interpreter"
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=query, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("elements", [])
    except Exception as e:
        logging.error(f"Ошибка {city}: {e}")
    return []

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *АЗС — Юг России*\n📅 {now}\n\n"

    for region, cities in CITIES.items():
        message += f"*{region}*\n"
        for city, (lat, lon) in cities.items():
            stations = await get_stations_osm(lat, lon, city)
            if stations:
                message += f"  📍 *{city}* — найдено {len(stations)} АЗС\n"
                for s in stations[:3]:
                    tags = s.get("tags", {})
                    name = tags.get("name", tags.get("brand", "АЗС"))
                    brand = tags.get("brand", "")
addr = tags.get("addr:street", "")
has_95 = tags.get("fuel:octane_95", "")
extra = f" — {addr}" if addr else ""
fuel_tag = " ⛽95" if has_95 == "yes" else ""
message += f"    • {name}{fuel_tag}{extra}\n"

            else:
                message += f"  📍 *{city}* — нет данных\n"
            await asyncio.sleep(1)
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
    await message.answer("🔍 Ищу АЗС... (займёт ~1 мин)")
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

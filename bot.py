import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime
from bs4 import BeautifulSoup

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def get_rosneft_prices():
    url = "https://www.rosneft.ru/retail/fuel_prices/"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    rows = soup.select("table tr")
                    prices = {}
                    for row in rows:
                        cols = row.select("td")
                        if len(cols) >= 3:
                            region = cols[0].text.strip()
                            if any(r in region for r in ["Краснодар", "Ставропол", "Ростов"]):
                                prices[region] = {
                                    "АИ-92": cols[1].text.strip(),
                                    "АИ-95": cols[2].text.strip(),
                                }
                    return prices
    except Exception as e:
        logging.error(f"Роснефть ошибка: {e}")
    return {}

async def get_lukoil_prices():
    url = "https://lukoil.ru/retail/prices"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status == 200:
                    html = await resp.text()
                    soup = BeautifulSoup(html, "html.parser")
                    rows = soup.select("table tr")
                    prices = {}
                    for row in rows:
                        cols = row.select("td")
                        if len(cols) >= 3:
                            region = cols[0].text.strip()
                            if any(r in region for r in ["Краснодар", "Ставропол", "Ростов"]):
                                prices[region] = {
                                    "АИ-92": cols[1].text.strip(),
                                    "АИ-95": cols[2].text.strip(),
                                }
                    return prices
    except Exception as e:
        logging.error(f"Лукойл ошибка: {e}")
    return {}

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *Цены на топливо — Юг России*\n📅 {now}\n\n"

    rosneft = await get_rosneft_prices()
    lukoil = await get_lukoil_prices()

    if rosneft:
        message += "*🔴 Роснефть*\n"
        for region, prices in rosneft.items():
            message += f"  📍 {region}\n"
            for fuel, price in prices.items():
                message += f"    • {fuel}: {price} ₽/л\n"
        message += "\n"

    if lukoil:
        message += "*🔵 Лукойл*\n"
        for region, prices in lukoil.items():
            message += f"  📍 {region}\n"
            for fuel, price in prices.items():
                message += f"    • {fuel}: {price} ₽/л\n"
        message += "\n"

    if not rosneft and not lukoil:
        message += "⚠️ Не удалось получить данные. Попробуйте позже.\n"

    chunks = [message[i:i+4000] for i in range(0, len(message), 4000)]
    for chunk in chunks:
        await bot.send_message(CHANNEL_ID, chunk, parse_mode="Markdown")
        await asyncio.sleep(1)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("⛽ Бот цен на топливо\n\n/prices — цены по регионам")

@dp.message(Command("prices"))
async def prices_cmd(message: types.Message):
    await message.answer("🔍 Получаю цены...")
    await post_to_channel()
    await message.answer("✅ Готово! Проверьте канал.")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(post_to_channel, "interval", hours=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())


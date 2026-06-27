import asyncio
import logging
import os
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHANNEL_ID = os.environ.get("CHANNEL_ID")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

REGIONS = {
    "krd": {
        "name": "🌴 Краснодарский край",
        "prices": {"АИ-92": "51.20", "АИ-95": "55.60", "ДТ": "59.80"},
        "cities": {
            "krd_krasnodar": ("Краснодар", 45.0360, 38.9760),
            "krd_sochi": ("Сочи", 43.5992, 39.7257),
            "krd_novoross": ("Новороссийск", 44.7237, 37.7686),
            "krd_armavir": ("Армавир", 44.9896, 41.1236),
            "krd_anapa": ("Анапа", 44.8953, 37.3167),
        }
    },
    "stv": {
        "name": "🌾 Ставропольский край",
        "prices": {"АИ-92": "50.90", "АИ-95": "55.30", "ДТ": "59.50"},
        "cities": {
            "stv_stavropol": ("Ставрополь", 45.0428, 41.9734),
            "stv_pyatigorsk": ("Пятигорск", 44.0496, 43.0597),
            "stv_kislovodsk": ("Кисловодск", 43.9000, 42.7167),
            "stv_nevinn": ("Невинномысск", 44.6349, 41.9380),
        }
    },
    "rst": {
        "name": "🌻 Ростовская область",
        "prices": {"АИ-92": "51.10", "АИ-95": "55.50", "ДТ": "59.70"},
        "cities": {
            "rst_rostov": ("Ростов-на-Дону", 47.2357, 39.7015),
            "rst_taganrog": ("Таганрог", 47.2090, 38.8969),
            "rst_shahty": ("Шахты", 47.7081, 40.2158),
            "rst_novocherk": ("Новочеркасск", 47.4135, 40.1126),
        }
    },
    "msk": {
        "name": "🏙️ Москва",
        "prices": {"АИ-92": "52.50", "АИ-95": "57.10", "ДТ": "61.20"},
        "cities": {
            "msk_cao": ("ЦАО — Центр", 55.7558, 37.6173),
            "msk_sao": ("САО — Север", 55.8500, 37.5833),
            "msk_svao": ("СВАО — Северо-Восток", 55.8667, 37.7000),
            "msk_vao": ("ВАО — Восток", 55.7833, 37.8167),
            "msk_yuvao": ("ЮВАО — Юго-Восток", 55.7000, 37.8000),
            "msk_yuao": ("ЮАО — Юг", 55.6333, 37.6333),
            "msk_yuzao": ("ЮЗАО — Юго-Запад", 55.6500, 37.5000),
            "msk_zao": ("ЗАО — Запад", 55.7500, 37.4167),
            "msk_szao": ("СЗАО — Северо-Запад", 55.8167, 37.4333),
            "msk_zel": ("ЗелАО — Зеленоград", 55.9833, 37.1833),
            "msk_nao": ("НАО — Новомосковский", 55.5167, 37.3333),
            "msk_tao": ("ТАО — Троицкий", 55.4833, 37.2833),
        }
    },
}

CITY_TO_REGION = {}
for reg_id, reg_data in REGIONS.items():
    for city_id in reg_data["cities"]:
        CITY_TO_REGION[city_id] = reg_id

def regions_keyboard():
    buttons = []
    for reg_id, reg_data in REGIONS.items():
        buttons.append([InlineKeyboardButton(
            text=reg_data["name"],
            callback_data=f"region_{reg_id}"
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cities_keyboard(reg_id):
    reg = REGIONS[reg_id]
    buttons = []
    row = []
    for i, (city_id, city_data) in enumerate(reg["cities"].items()):
        row.append(InlineKeyboardButton(
            text=city_data[0],
            callback_data=f"city_{city_id}"
        ))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="◀️ Назад", callback_data="back_regions")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

async def get_stations_osm(lat, lon):
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
        logging.error(f"OSM ошибка: {e}")
    return []

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "⛽ *Бот поиска АЗС*\n\nВыберите регион:",
        parse_mode="Markdown",
        reply_markup=regions_keyboard()
    )

@dp.callback_query(lambda c: c.data == "back_regions")
async def back_to_regions(callback: CallbackQuery):
    await callback.message.edit_text(
        "⛽ *Бот поиска АЗС*\n\nВыберите регион:",
        parse_mode="Markdown",
        reply_markup=regions_keyboard()
    )

@dp.callback_query(lambda c: c.data.startswith("region_"))
async def region_selected(callback: CallbackQuery):
    reg_id = callback.data.replace("region_", "")
    reg = REGIONS[reg_id]
    prices = reg["prices"]
    price_str = " | ".join([f"{k}: {v}₽" for k, v in prices.items()])
    await callback.message.edit_text(
        f"*{reg['name']}*\n💰 _{price_str}_\n\nВыберите город:",
        parse_mode="Markdown",
        reply_markup=cities_keyboard(reg_id)
    )

@dp.callback_query(lambda c: c.data.startswith("city_"))
async def city_selected(callback: CallbackQuery):
    city_id = callback.data.replace("city_", "")
    reg_id = CITY_TO_REGION[city_id]
    reg = REGIONS[reg_id]
    city_data = reg["cities"][city_id]
    city_name, lat, lon = city_data

    await callback.message.edit_text(
        f"🔍 Ищу АЗС в *{city_name}*...",
        parse_mode="Markdown"
    )

    stations = await get_stations_osm(lat, lon)
    prices = reg["prices"]
    price_str = " | ".join([f"{k}: {v}₽" for k, v in prices.items()])

    text = f"⛽ *АЗС — {city_name}*\n"
    text += f"💰 _{price_str}_\n\n"

    if stations:
        text += f"Найдено {len(stations)} АЗС:\n\n"
        for s in stations:
            tags = s.get("tags", {})
            name = tags.get("name", tags.get("brand", "АЗС"))
            addr = tags.get("addr:street", "")
            has_92 = "✅" if tags.get("fuel:octane_92") == "yes" else "❌"
            has_95 = "✅" if tags.get("fuel:octane_95") == "yes" else "❌"
            has_dt = "✅" if tags.get("fuel:diesel") == "yes" else "❌"
            text += f"🏪 *{name}*\n"
            if addr:
                text += f"📍 {addr}\n"
            text += f"92: {has_92} | 95: {has_95} | ДТ: {has_dt}\n\n"
    else:
        text += "⚠️ АЗС не найдены\n"

    back_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ К городам", callback_data=f"region_{reg_id}")],
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="back_regions")]
    ])

    await callback.message.edit_text(
        text,
        parse_mode="Markdown",
        reply_markup=back_kb
    )

async def post_to_channel():
    now = datetime.now().strftime("%d.%m.%Y %H:%M")
    message = f"⛽ *АЗС — Юг России + Москва*\n📅 {now}\n\n"
    for reg_id, reg in REGIONS.items():
        prices = reg["prices"]
        price_str = " | ".join([f"{k}: {v}₽" for k, v in prices.items()])
        message += f"*{reg['name']}*\n💰 _{price_str}_\n\n"
    await bot.send_message(CHANNEL_ID, message, parse_mode="Markdown")

async def main():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(post_to_channel, "interval", hours=1)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging





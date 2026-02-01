import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("8161107014:AAGBWEYVxie7-pB4-2FoGCPjCv_sl0yHogc", "").strip()
BASE_URL = os.getenv("https://replit.com/@habibulloabidjo", "").strip()  # Replitda: https://xxxxx.repl.co

if not BOT_TOKEN or not BASE_URL:
    raise RuntimeError("BOT_TOKEN yoki BASE_URL topilmadi. .env yoki Replit Secrets ni tekshir.")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def start(msg: types.Message):
    user_id = msg.from_user.id
    username = msg.from_user.username or ""

    # user DBga tushsin
    async with aiohttp.ClientSession() as s:
        await s.post(f"{BASE_URL}/api/user/upsert", params={"user_id": user_id, "username": username})

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌐 Brauzerda ochish", web_app=WebAppInfo(url=BASE_URL))]
    ])

    await msg.answer("🎰 Mini ilova tayyor. Pastdagi tugma orqali oching:", reply_markup=kb)

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

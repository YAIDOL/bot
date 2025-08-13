import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiosupabase import Supabase, create_client

# --- ENV ---
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("BOT_TOKEN, SUPABASE_URL або SUPABASE_KEY не задані!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase: Supabase = create_client(url=SUPABASE_URL, key=SUPABASE_KEY)

waiting_for_nick = set()
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🗺️ Приключения"), KeyboardButton("🪨 Крафт")],
        [KeyboardButton("👤 Профиль"), KeyboardButton("💪 Мой клан"),
         KeyboardButton("🏆 Топ"), KeyboardButton("🛍️ Торговля")],
    ],
    resize_keyboard=True
)

async def add_user(user_id, nickname):
    await supabase.table("users").upsert({
        "user_id": user_id,
        "username": nickname,
        "status": "Игрок",
        "level": 1,
        "exp": 0,
        "exp_max": 100,
        "health": 100,
        "defense": 10,
        "attack": 50,
        "money": 0,
        "diamonds": 0,
        "head": "нет",
        "body": "нет",
        "legs": "нет",
        "feet": "нет",
        "weapon": "нет",
        "bag": "нет",
        "premium_until": None
    }).execute()

async def get_user(user_id):
    res = await supabase.table("users").select("*").eq("user_id", user_id).execute()
    return res.data[0] if res.data else None

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await get_user(message.from_user.id)
    if user and user.get("username"):
        await message.answer(f"Привет, <b>{user['username']}</b>! Выбери кнопку ⬇️", reply_markup=main_menu_kb)
    else:
        waiting_for_nick.add(message.from_user.id)
        await message.answer("Привет! Напиши свой никнейм.")

@dp.message()
async def handle_msg(msg: types.Message):
    uid = msg.from_user.id
    if uid in waiting_for_nick:
        if len(msg.text.strip()) < 3:
            return await msg.answer("Никнейм должен быть минимум 3 символа.")
        await add_user(uid, msg.text.strip())
        waiting_for_nick.remove(uid)
        return await msg.answer(f"Ник сохранён: <b>{msg.text.strip()}</b>", reply_markup=main_menu_kb)

    if msg.text == "👤 Профиль":
        user = await get_user(uid)
        if not user:
            waiting_for_nick.add(uid)
            return await msg.answer("Никнейм не найден. Введи его.")
        text = (
            f"<b>{user['username']}</b> | <code>{uid}</code>\n"
            f"Уровень {user['level']} | Опыт {user['exp']} / {user['exp_max']}\n"
            f"❤️{user['health']} 🛡{user['defense']} 🗡{user['attack']}\n"
            f"Деньги: {user['money']} | Алмазы: {user['diamonds']}\n"
            f"Premium до: {user['premium_until'] or 'Нет'}"
        )
        return await msg.answer(text, reply_markup=main_menu_kb)

    if msg.text == "🏆 Топ":
        res = await supabase.table("users").select("username").execute()
        players = res.data or []
        if not players:
            return await msg.answer("Список пуст.", reply_markup=main_menu_kb)
        lst = "\n".join(f"{i+1}. {p['username']}" for i, p in enumerate(players))
        return await msg.answer(f"🏆 Игроки:\n\n{lst}", reply_markup=main_menu_kb)

    await msg.answer("Неизвестная команда. Используй меню или /start.", reply_markup=main_menu_kb)

async def notify_all():
    res = await supabase.table("users").select("user_id").execute()
    for u in (res.data or []):
        try:
            await bot.send_message(u["user_id"], "Бот запущен!")
        except:
            pass

async def main():
    await notify_all()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

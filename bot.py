import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from supabase import create_client, Client

# === ENV ===
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("BOT_TOKEN, SUPABASE_URL або SUPABASE_KEY не задані!")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

waiting_for_nick = set()

# === Клавіатура ===
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton("🗺️ Приключения"), KeyboardButton("🪨 Крафт")],
        [KeyboardButton("👤 Профиль"), KeyboardButton("💪 Мой клан"),
         KeyboardButton("🏆 Топ"), KeyboardButton("🛍️ Торговля")],
    ],
    resize_keyboard=True
)

# === Supabase функції ===
def add_user(user_id, username):
    supabase.table("users").upsert({
        "user_id": user_id,
        "username": username,
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

def get_user(user_id):
    result = supabase.table("users").select("*").eq("user_id", user_id).execute()
    return result.data[0] if result.data else None

def get_all_users():
    return supabase.table("users").select("*").execute().data

# === /start ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user = await asyncio.to_thread(get_user, message.from_user.id)
    if user and user.get("username"):
        await message.answer(f"Привет, <b>{user['username']}</b>! Выбери кнопку ⬇️", reply_markup=main_menu_kb)
    else:
        waiting_for_nick.add(message.from_user.id)
        await message.answer("Привет! Напиши свой никнейм.")

# === Обробка повідомлень ===
@dp.message()
async def handle_message(message: types.Message):
    uid = message.from_user.id
    text = message.text.strip()

    if uid in waiting_for_nick:
        if len(text) < 3:
            return await message.answer("❗ Никнейм должен быть минимум 3 символа.")
        await asyncio.to_thread(add_user, uid, text)
        waiting_for_nick.remove(uid)
        return await message.answer(f"✅ Отлично, <b>{text}</b>! Ник сохранён.", reply_markup=main_menu_kb)

    if text == "👤 Профиль":
        user = await asyncio.to_thread(get_user, uid)
        if user:
            await message.answer(
                f"<b>{user['username']}</b> | <code>{uid}</code>\n"
                f"Статус: {user['status']}\n"
                f"Уровень: {user['level']} | Опыт: {user['exp']} / {user['exp_max']}\n"
                f"❤️ {user['health']} 🛡 {user['defense']} 🗡 {user['attack']}\n"
                f"🪙 {user['money']} 💎 {user['diamonds']}\n"
                f"🥋 Одежда: Голова: {user['head']}, Тело: {user['body']}, Ноги: {user['legs']}, Ступни: {user['feet']}\n"
                f"🪛 Оружие: {user['weapon']} | 🧰 Сумка: {user['bag']}\n"
                f"⭐ Premium до: {user['premium_until'] or 'Нет'}",
                reply_markup=main_menu_kb
            )
        else:
            waiting_for_nick.add(uid)
            await message.answer("Профиль не найден. Напиши никнейм.")

    elif text == "🏆 Топ":
        users = await asyncio.to_thread(get_all_users)
        if users:
            lst = "\n".join(f"{i+1}. {u['username']}" for i, u in enumerate(users))
            await message.answer(f"🏆 Топ игроков:\n\n{lst}", reply_markup=main_menu_kb)
        else:
            await message.answer("Список игроков пуст.", reply_markup=main_menu_kb)

    elif text in ["🗺️ Приключения", "🪨 Крафт", "💪 Мой клан", "🛍️ Торговля"]:
        await message.answer(f"Вы выбрали: <b>{text}</b>", reply_markup=main_menu_kb)

    else:
        await message.answer("❓ Неизвестная команда. Используй кнопки меню или напиши /start.", reply_markup=main_menu_kb)

# === Повідомлення при запуску ===
async def notify_users_on_start():
    users = await asyncio.to_thread(get_all_users)
    for u in users:
        try:
            await bot.send_message(u["user_id"], "🤖 Бот перезапущен!")
        except:
            pass

# === Запуск ===
async def main():
    await notify_users_on_start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

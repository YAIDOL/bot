import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiosupabase import create_client, SupabaseClient

# ---------- ЗАВАНТАЖЕННЯ ЗМІННИХ ----------
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("BOT_TOKEN, SUPABASE_URL або SUPABASE_KEY не задані!")

# ---------- ІНІЦІАЛІЗАЦІЯ ----------
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase: SupabaseClient = create_client(SUPABASE_URL, SUPABASE_KEY)

waiting_for_nick = set()

# ---------- КЛАВІАТУРА ----------
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Приключения"), KeyboardButton(text="🪨 Крафт")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💪 Мой клан"),
         KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🛍️ Торговля")],
    ],
    resize_keyboard=True
)

# ---------- SUPABASE FUNCTIONS ----------
async def add_user(user_id, username):
    await supabase.table("users").upsert({
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

async def get_user(user_id):
    res = await supabase.table("users").select("*").eq("user_id", user_id).execute()
    if res.data:
        return res.data[0]
    return None

async def update_user(user_id, data: dict):
    await supabase.table("users").update(data).eq("user_id", user_id).execute()

# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = await get_user(user_id)
    if user and user.get("username"):
        await message.answer(f"Привет, <b>{user['username']}</b>! Выбери кнопку ниже ⬇️", reply_markup=main_menu_kb)
    else:
        waiting_for_nick.add(user_id)
        await message.answer("Привет! Напиши, пожалуйста, свой никнейм.")

# ---------- ОБРОБКА ПОВІДОМЛЕНЬ ----------
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in waiting_for_nick:
        nickname = text
        if len(nickname) < 3:
            await message.answer("❗ Никнейм должен быть минимум 3 символа, попробуй ещё раз.")
            return
        await add_user(user_id, nickname)
        waiting_for_nick.remove(user_id)
        await message.answer(f"✅ Отлично, <b>{nickname}</b>! Никнейм сохранён.", reply_markup=main_menu_kb)
        return

    if text == "👤 Профиль":
        user = await get_user(user_id)
        if user:
            profile_text = (
                f"<b>{user['username']}</b> | <code>{user_id}</code>\n"
                f"Статус аккаунта: {user['status']}\n\n"
                f"Уровень: {user['level']}\nОпыт: {user['exp']} / {user['exp_max']}\n"
                f"❤️{user['health']} | 🛡{user['defense']} | 🗡{user['attack']}\n\n"
                f"🪙 Деньги: {user['money']} 💰, Алмазы: {user['diamonds']} 💎\n"
                f"🥋 Одежда: Голова: {user['head']}, Тело: {user['body']}, Ноги: {user['legs']}, Ступни: {user['feet']}\n"
                f"🪛 Снаряжение: Оружие: {user['weapon']}\n🧰 Сумка: {user['bag']}\n\n"
                f"⭐ Premium до: {user['premium_until'] or 'Нет'}"
            )
            await message.answer(profile_text, reply_markup=main_menu_kb)
        else:
            waiting_for_nick.add(user_id)
            await message.answer("Никнейм не найден. Введите свой никнейм.")

    elif text == "🏆 Топ":
        res = await supabase.table("users").select("username").execute()
        players = res.data if res.data else []
        if players:
            players_list = "\n".join(f"{i+1}. {p['username']}" for i, p in enumerate(players))
            await message.answer(f"🏆 <b>Список игроков:</b>\n\n{players_list}", reply_markup=main_menu_kb)
        else:
            await message.answer("Список игроков пуст.", reply_markup=main_menu_kb)

    elif text in ["🗺️ Приключения", "🪨 Крафт", "💪 Мой клан", "🛍️ Торговля"]:
        await message.answer(f"Вы выбрали: <b>{text}</b>", reply_markup=main_menu_kb)

    else:
        await message.answer("❓ Неизвестная команда. Используй кнопки меню или напиши /start.", reply_markup=main_menu_kb)

# ---------- ПОВІДОМЛЕННЯ ВСІМ КОРИСТУВАЧАМ ПРИ СТАРТІ ----------
async def notify_users_on_start():
    res = await supabase.table("users").select("user_id").execute()
    users = res.data if res.data else []
    for user in users:
        try:
            await bot.send_message(user["user_id"], "🤖 Бот працює ✅")
        except Exception:
            pass

# ---------- ОСНОВНИЙ ЗАПУСК ----------
async def main():
    await notify_users_on_start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

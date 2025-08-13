import os
import sqlite3
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

# ---------- ЗАВАНТАЖЕННЯ TOKEN ----------
TOKEN = os.getenv("BOT_TOKEN")
if TOKEN is None:
    raise ValueError("BOT_TOKEN не знайдено! Додай його у Render → Environment Variables")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ---------- БАЗА ДАНИХ ----------
conn = sqlite3.connect("users.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    status TEXT DEFAULT 'Игрок',
    level INTEGER DEFAULT 1,
    exp INTEGER DEFAULT 0,
    exp_max INTEGER DEFAULT 100,
    health INTEGER DEFAULT 100,
    defense INTEGER DEFAULT 10,
    attack INTEGER DEFAULT 50,
    money INTEGER DEFAULT 0,
    diamonds INTEGER DEFAULT 0,
    head TEXT DEFAULT 'нет',
    body TEXT DEFAULT 'нет',
    legs TEXT DEFAULT 'нет',
    feet TEXT DEFAULT 'нет',
    weapon TEXT DEFAULT 'нет',
    bag TEXT DEFAULT 'нет'
)
""")
conn.commit()

waiting_for_nick = set()

# ---------- КЛАВІАТУРИ ----------
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Приключения"), KeyboardButton(text="🪨 Крафт")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💪 Мой клан"),
         KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🛍️ Торговля")],
    ],
    resize_keyboard=True
)

# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    cursor.execute("SELECT username FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if row and row[0]:
        await message.answer(f"Привет, <b>{row[0]}</b>! Выбери кнопку ниже ⬇️", reply_markup=main_menu_kb)
    else:
        waiting_for_nick.add(user_id)
        await message.answer("Привет! Напиши, пожалуйста, свой никнейм.")

# ---------- ОБРОБКА ПОВІДОМЛЕНЬ ----------
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # ----- Введення ника -----
    if user_id in waiting_for_nick:
        nickname = text
        if len(nickname) < 3:
            await message.answer("❗ Никнейм должен быть минимум 3 символа, попробуй ещё раз.")
            return
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, username)
            VALUES (?, ?)
        """, (user_id, nickname))
        conn.commit()
        waiting_for_nick.remove(user_id)
        await message.answer(f"✅ Отлично, <b>{nickname}</b>! Никнейм сохранён.", reply_markup=main_menu_kb)
        return

    # ----- ПРОФІЛЬ -----
    if text == "👤 Профиль":
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        if row:
            (
                _id, username, status, level, exp, exp_max,
                health, defense, attack, money, diamonds,
                head, body, legs, feet, weapon, bag
            ) = row

            profile_text = (
                f"<b>{username}</b> | <code>{user_id}</code>\n"
                f"Статус аккаунта: {status}\n\n"
                f"Уровень: {level}\n"
                f"Опыт: {exp} / {exp_max}\n"
                f"Характеристики: ❤️{health} | 🛡{defense} | 🗡{attack}\n\n"
                f"🪙 Баланс:\n"
                f"Деньги: {money} 💰\n"
                f"Алмазы: {diamonds} 💎\n\n"
                f"🥋 Одежда:\n"
                f"Голова: {head}\n"
                f"Тело: {body}\n"
                f"Ноги: {legs}\n"
                f"Ступни: {feet}\n\n"
                f"🪛 Снаряжение:\n"
                f"Оружие: {weapon}\n\n"
                f"🧰 Сумка:\n"
                f"{bag}"
            )
            await message.answer(profile_text, reply_markup=main_menu_kb)
        else:
            waiting_for_nick.add(user_id)
            await message.answer("Никнейм не найден. Введите свой никнейм.")

    # ----- ТОП -----
    elif text == "🏆 Топ":
        cursor.execute("SELECT username FROM users")
        players = cursor.fetchall()
        if players:
            players_list = "\n".join(f"{i+1}. {name[0]}" for i, name in enumerate(players))
            await message.answer(f"🏆 <b>Список игроков:</b>\n\n{players_list}", reply_markup=main_menu_kb)
        else:
            await message.answer("Список игроков пуст.", reply_markup=main_menu_kb)

    # ----- ПРОСТІ КНОПКИ -----
    elif text in ["🗺️ Приключения", "🪨 Крафт", "💪 Мой клан", "🛍️ Торговля"]:
        await message.answer(f"Вы выбрали: <b>{text}</b>", reply_markup=main_menu_kb)

    else:
        await message.answer("❓ Неизвестная команда. Используй кнопки меню или напиши /start.", reply_markup=main_menu_kb)

# ---------- ПОВІДОМЛЕННЯ ВСІМ ПРИ СТАРТІ ----------
async def notify_users_on_start():
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    for (user_id,) in users:
        try:
            await bot.send_message(user_id, "🤖 Бот працює ✅")
        except Exception:
            pass  # якщо користувач заблокував бота

# ---------- ОСНОВНИЙ ЗАПУСК ----------
async def main():
    await notify_users_on_start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

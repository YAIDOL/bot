import os
import asyncio
import random
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from supabase import create_client, Client
from dotenv import load_dotenv

# ---------- Load environment ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
waiting_for_nick = set()

# ---------- Кнопки ----------
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Приключения"), KeyboardButton(text="⚒️ Кузница")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💪 Мой клан"), KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🛍️ Торговля")],
    ],
    resize_keyboard=True
)

top_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Топ по уровню"), KeyboardButton(text="💰 Топ по деньгам")],
        [KeyboardButton(text="⬅️ Главная")],
    ],
    resize_keyboard=True
)

forge_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="⚔️ Заточка"), KeyboardButton(text="🔨 Крафт")],
        [KeyboardButton(text="⬅️ Главная")]
    ],
    resize_keyboard=True
)

# ---------- Кланы ----------
CLANS = {
    "Звездные стражи 🌌": "🛡 <b>Звездные стражи</b> — ...",
    "Сияющие маяки 🔥": "🔥 <b>Сияющие маяки</b> — ...",
    "Тенистые клинки 🌑": "🌑 <b>Тенистые клинки</b> — ...",
    "Безмолвные песни 🎵": "🎵 <b>Безмолвные песни</b> — ..."
}

# ---------- Локации ----------
ADVENTURES = {
    "Большой Лес": {
        "description": "🌲 Густой, таинственный лес, окутанный туманом...",
        "mobs": ["Туманный Волк", "Древесный Страж", "Лесной Жутень", "Призрачный Олень", "Корнеплет"]
    },
    "Мёртвая Деревня": {
        "description": "🏚️ Проклятая деревня, наполненная жуткими тенями...",
        "mobs": ["Безглазый Житель", "Пепельный Пёс", "Колоколий", "Сломанный Кукловод", "Жнец Молчания"]
    },
    "Заброшенный Замок": {
        "description": "🏰 Огромная крепость, забытая временем...",
        "mobs": ["Блуждающий Рыцарь", "Призрачная Дева", "Гаргулья-Караульщица", "Книжный Ужас", "Старый Ключник"]
    }
}

# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    response = supabase.table("users").select("username", "clan").eq("user_id", user_id).execute()
    row = response.data[0] if response.data else None

    if row and row.get("username") and row.get("clan"):
        await message.answer(f"Привет, <b>{row['username']}</b>! Выбери кнопку ниже ⬇️", reply_markup=main_menu_kb)
    elif row and row.get("username"):
        await message.answer(f"Привет, <b>{row['username']}</b>! Пожалуйста, выбери клан.")
        await ask_clan_choice(message)
    else:
        waiting_for_nick.add(user_id)
        await message.answer("Привет! Напиши, пожалуйста, свой никнейм.")

# ---------- Приключения ----------
@dp.message(lambda msg: msg.text == "🗺️ Приключения")
async def adventures(message: types.Message):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=loc, callback_data=f"adventure_{loc}")]
        for loc in ADVENTURES
    ])
    await message.answer("🌍 <b>Выбери локацию для приключений:</b>", reply_markup=keyboard)

@dp.callback_query()
async def handle_adventure(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data.startswith("adventure_"):
        loc_name = data[len("adventure_"):]
        adventure = ADVENTURES.get(loc_name)

        if not adventure:
            await callback.message.answer("❌ Локация не найдена.")
            return

        mobs_text = "\n".join(f"• {mob}" for mob in adventure["mobs"])
        text = f"{adventure['description']}\n\n👾 <b>Враги:</b>\n{mobs_text}"

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Исследовать", callback_data=f"explore_{loc_name}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_adventures")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()

    elif data.startswith("explore_"):
        loc_name = data[len("explore_"):]

        LOCATIONS = {
            "Большой Лес": {"exp": (10, 30), "money": (20, 40), "duration": 60},
            "Мёртвая Деревня": {"exp": (20, 50), "money": (30, 60), "duration": 180},
            "Заброшенный Замок": {"exp": (40, 60), "money": (50, 80), "duration": 300},
        }

        MOBS = ADVENTURES.get(loc_name, {}).get("mobs", [])
        if not MOBS or loc_name not in LOCATIONS:
            await callback.message.answer("❌ Ошибка локации.")
            return

        config = LOCATIONS[loc_name]
        exp = random.randint(*config["exp"])
        money = random.randint(*config["money"])
        mob = random.choice(MOBS)

        # Получить данные пользователя
        res = supabase.table("users").select("exp", "exp_max", "level", "money").eq("user_id", user_id).execute()
        if not res.data:
            await callback.message.answer("⚠️ Профиль не найден.")
            return

        user = res.data[0]
        new_exp = user["exp"] + exp
        level = user["level"]
        exp_max = user["exp_max"]

        if new_exp >= exp_max:
            level += 1
            new_exp = 0
            exp_max = level * 100

        new_money = user["money"] + money

        supabase.table("users").update({
            "exp": new_exp,
            "level": level,
            "exp_max": exp_max,
            "money": new_money
        }).eq("user_id", user_id).execute()

        await callback.message.edit_text(
            f"🧭 <b>Ты исследовал локацию:</b> {loc_name}\n"
            f"👾 Встретил: <b>{mob}</b>\n\n"
            f"🌟 Опыт: +{exp}\n"
            f"💰 Деньги: +{money}\n"
            f"📈 Уровень: {level}\n"
            f"🕐 Длительность: {config['duration'] // 60} мин",
            reply_markup=main_menu_kb
        )
        await callback.answer("Приключение завершено!")

    elif data == "back_to_adventures":
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=loc, callback_data=f"adventure_{loc}")]
            for loc in ADVENTURES
        ])
        await callback.message.edit_text("🌍 <b>Выбери локацию для приключений:</b>", reply_markup=keyboard)
        await callback.answer()

# ---------- Запуск ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

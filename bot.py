import os
import asyncio
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

if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Перевірте BOT_TOKEN, SUPABASE_URL та SUPABASE_ANON_KEY в .env")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

waiting_for_nick = set()

# ---------- Keyboards ----------
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

# ---------- Clans ----------
CLANS = {
    "Звездные стражи 🌌": "🛡 <b>Звездные стражи</b> — это древнее и неуловимое братство, чья связь с космосом и тайнами вселенной глубока и неразрывна. Они — вечные наблюдатели, хранители небесного порядка и защитники миров от угроз, исходящих из бездны космоса. Их взгляд устремлен к звездам, а сердца бьются в ритме галактических циклов.",
    "Сияющие маяки 🔥": "🔥 <b>Сияющие маяки</b> — это древний и благородный орден, чья миссия заключается в том, чтобы нести свет, надежду и истину через самые темные времена. Они — путеводная звезда для заблудших, символ непоколебимой веры и оплот против тьмы и хаоса. Их сила исходит из чистоты намерений, непоколебимой решимости и внутренней гармонии, которая отражается во всем, что они делают.",
    "Тенистые клинки 🌑": "🌑 <b>Тенистые клинки</b> — это древнее братство, чье существование окутано тайной и легендами. Они не стремятся к славе или открытому признанию, предпочитая действовать из теней, словно невидимые вихри, которые оставляют за собой лишь след судьбы.",
    "Безмолвные песни 🎵": "🎵 <b>Безмолвные песни</b> — это загадочное и меланхоличное сообщество, чье существование окутано завесой печали и древних тайн. Они не владеют острыми клинками или громогласными криками, их оружие — это эмоции, воспоминания и эхо забытых мелодий. Члены этого клана — хранители скорби, носители утерянных историй и проводники через лабиринты человеческих чувств."
}

# ---------- Clan selection ----------
async def ask_clan_choice(message: types.Message):
    buttons = [[InlineKeyboardButton(text=clan, callback_data=f"clan_{clan.split()[0]}")] for clan in CLANS.keys()]
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    description = (
        "🧭 <b>Выбери один из кланов:</b>\n\n"
        "🌌 <b>Звездные стражи</b> — воины света и защитники порядка\n"
        "🔥 <b>Сияющие маяки</b> — символ надежды и силы духа\n"
        "🌑 <b>Тенистые клинки</b> — скрытные и смертоносные бойцы\n"
        "🎵 <b>Безмолвные песни</b> — мудрецы, владеющие тайными знаниями"
    )
    await message.answer(description, reply_markup=keyboard)

# ---------- /start ----------
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    response = supabase.table("users").select("username, clan").eq("user_id", user_id).execute()
    row = response.data[0] if response.data else None

    if row and row.get("username") and row.get("clan"):
        await message.answer(f"Привет, <b>{row['username']}</b>! Выбери кнопку ниже ⬇️", reply_markup=main_menu_kb)
    elif row and row.get("username"):
        await message.answer(f"Привет, <b>{row['username']}</b>! Пожалуйста, выбери клан.")
        await ask_clan_choice(message)
    else:
        waiting_for_nick.add(user_id)
        await message.answer("Привет! Напиши, пожалуйста, свой никнейм.")

# ---------- Обработка сообщений ----------
@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in waiting_for_nick:
        nickname = text

        if re.search(r"[;:/.\"<>'\\\\]", nickname) or "script" in nickname.lower():
            await message.answer("❗ Недопустимые символы или слово.")
            return
        if not (3 <= len(nickname) <= 9):
            await message.answer("❗ Ник должен быть от 3 до 9 символов.")
            return
        if not re.match(r"^[A-Za-z0-9_]+$", nickname):
            await message.answer("❗ Только латиница, цифры и подчёркивания.")
            return

        supabase.table("users").upsert({"user_id": user_id, "username": nickname}).execute()
        waiting_for_nick.remove(user_id)
        await message.answer(f"✅ Отлично, <b>{nickname}</b>! Никнейм сохранён.\nТеперь выбери клан.")
        await ask_clan_choice(message)
        return

    if text == "👤 Профиль":
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        row = response.data[0] if response.data else None
        if row:
            clan_desc = CLANS.get(row.get("clan", ""), "")
            profile_text = (
                f"<b>{row['username']}</b> | <code>{user_id}</code>\n"
                f"Статус аккаунта: {row['status']}\n\n"
                f"🌟 Уровень: {row['level']}\n"
                f"Опыт: {row['exp']} / {row['exp_max']}\n"
                f"❤️{row['health']} | 🛡{row['defense']} | 🗡{row['attack']}\n\n"
                f"💰 Деньги: {row['money']} | 💎 Алмазы: {row['diamonds']}\n\n"
                f"🥋 Экипировка:\n"
                f"Голова: {row['head']}\nТело: {row['body']}\nНоги: {row['legs']}\nСтупни: {row['feet']}\n"
                f"Оружие: {row['weapon']}\n"
                f"Сумка: {row['bag']}\n\n"
                f"💪 Клан: {row.get('clan', 'нет')}\n{clan_desc}"
            )
            await message.answer(profile_text, reply_markup=main_menu_kb)
        else:
            waiting_for_nick.add(user_id)
            await message.answer("Никнейм не найден. Введите свой никнейм.")

    elif text == "🗺️ Приключения":
        await message.answer("⚙️ В разработке...", reply_markup=main_menu_kb)

    elif text == "💪 Мой клан":
        response = supabase.table("users").select("clan").eq("user_id", user_id).execute()
        row = response.data[0] if response.data else None
        if row and row.get("clan"):
            clan = row["clan"]
            clan_desc = CLANS.get(clan, "")
            members_resp = supabase.table("clan_members").select("user_id").eq("clan_name", clan).execute()
            members = members_resp.data or []
            user_ids = [m["user_id"] for m in members]
            users_resp = supabase.table("users").select("user_id, username").in_("user_id", user_ids).execute()
            id_to_username = {u["user_id"]: u["username"] for u in users_resp.data or []}
            members_list = "\n".join(f"- {id_to_username.get(uid, uid)}" for uid in user_ids) or "Пока нет участников"
            await message.answer(f"💪 Клан: <b>{clan}</b>\n\n{clan_desc}\n\n👥 Участники:\n{members_list}", reply_markup=main_menu_kb)
        else:
            await message.answer("Вы еще не выбрали клан. Пожалуйста, выберите клан.", reply_markup=main_menu_kb)
            await ask_clan_choice(message)

    elif text == "🏆 Топ":
        await message.answer("Выберите тип топа:", reply_markup=top_menu_kb)

    elif text == "🌟 Топ по уровню":
        response = supabase.table("users").select("user_id, username, level").order("level", desc=True).execute()
        players = response.data or []
        top_10 = players[:10]
        players_list = "\n".join(f"{i + 1}. {p['username']} 🌟 {p['level']}" for i, p in enumerate(top_10))
        place = next((i + 1 for i, p in enumerate(players) if p["user_id"] == user_id), None)
        await message.answer(f"🌟 <b>Топ по уровню:</b>\n\n{players_list}\n\n📍Твое место: {place}", reply_markup=top_menu_kb)

    elif text == "💰 Топ по деньгам":
        response = supabase.table("users").select("user_id, username, money").order("money", desc=True).execute()
        players = response.data or []
        top_10 = players[:10]
        players_list = "\n".join(f"{i + 1}. {p['username']} 💰 {p['money']}" for i, p in enumerate(top_10))
        place = next((i + 1 for i, p in enumerate(players) if p["user_id"] == user_id), None)
        await message.answer(f"💰 <b>Топ по деньгам:</b>\n\n{players_list}\n\n📍Твое место: {place}", reply_markup=top_menu_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    elif text == "⚒️ Кузница":
        await message.answer("Выберите действие:", reply_markup=forge_menu_kb)

    elif text in ("⚔️ Заточка", "🔨 Крафт"):
        await message.answer("⚙️ В разработке...", reply_markup=forge_menu_kb)

    elif text == "🛍️ Торговля":
        await message.answer("⚙️ В разработке...", reply_markup=main_menu_kb)

    else:
        await message.answer("❓ Неизвестная команда. Используй кнопки меню или напиши /start.", reply_markup=main_menu_kb)

# ---------- Callback: Clan selection ----------
@dp.callback_query()
async def handle_clan_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data.startswith("clan_"):
        clan_key = data[5:]
        clan_name = next((name for name in CLANS if name.startswith(clan_key)), None)
        if not clan_name:
            await callback.answer("Ошибка: клан не найден.")
            return
        desc = CLANS[clan_name]
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Выбрать", callback_data=f"select_{clan_key}"),
             InlineKeyboardButton(text="Назад", callback_data="back_to_clans")]
        ])
        await callback.message.edit_text(desc, reply_markup=keyboard)
        await callback.answer()

    elif data.startswith("select_"):
        clan_key = data[7:]
        clan_name = next((name for name in CLANS if name.startswith(clan_key)), None)
        if not clan_name:
            await callback.answer("Ошибка: клан не найден.")
            return
        supabase.table("users").update({"clan": clan_name}).eq("user_id", user_id).execute()
        supabase.table("clan_members").upsert({"clan_name": clan_name, "user_id": user_id}).execute()
        await callback.message.edit_text(f"Вы успешно выбрали клан:\n\n{CLANS[clan_name]}")
        await bot.send_message(user_id, "Теперь тебе доступно главное меню ⬇️", reply_markup=main_menu_kb)
        await callback.answer("Клан выбран!")

    elif data == "back_to_clans":
        await ask_clan_choice(callback.message)
        await callback.answer()

# ---------- Notify on start ----------
async def notify_users_on_start():
    response = supabase.table("users").select("user_id").execute()
    for user in response.data:
        try:
            await bot.send_message(user["user_id"], "🤖 Бот работает ✅")
        except:
            continue

# ---------- Run bot ----------
async def main():
    await notify_users_on_start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

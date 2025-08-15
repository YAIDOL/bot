import os
import asyncio
import re
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from supabase import create_client, Client
from dotenv import load_dotenv

# ---------- ЗАВАНТАЖЕННЯ .env ----------
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Перевірте BOT_TOKEN, SUPABASE_URL та SUPABASE_ANON_KEY в .env")

# ---------- Бот ----------
bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ---------- Підключення до Supabase ----------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

waiting_for_nick = set()

# ---------- Клавіатури ----------
main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Приключения"), KeyboardButton(text="⚒️ Кузница")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💪 Мой клан"),
         KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🛍️ Торговля")],
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

# ---------- Клани та їх описи ----------
CLANS = {
    "Звездные стражи 🌌": (
        "🛡 <b>Звездные стражи</b> — воины света, связанные с космосом и вечностью. "
        "Они охраняют равновесие и защищают мир от хаоса."
    ),
    "Сияющие маяки 🔥": (
        "🔥 <b>Сияющие маяки</b> — лидеры и проводники. Символизируют надежду, чистоту и силу духа. "
        "Их цель — быть светом во тьме для других."
    ),
    "Тенистые клинки 🌑": (
        "🌑 <b>Тенистые клинки</b> — мастера скрытности и внезапных ударов. "
        "Они действуют из тени, используя ловкость и точность как главное оружие."
    ),
    "Безмолвные песни 🎵": (
        "🎵 <b>Безмолвные песни</b> — мудрецы и мистики, владеющие древними знаниями и магией. "
        "Их сила кроется в тайне, тишине и внутреннем равновесии."
    )
}

# пробудження бота
async def ping_fly_machine():
    url = "https://bot-amackg.fly.dev"  # заміни на свою адресу, якщо інша
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=3) as response:
                if response.status == 200:
                    print("🟢 Fly.io машина розбуджена")
    except Exception as e:
        print(f"⚠️ Не вдалося пінгонути машину: {e}")

# ---------- Функція для показу вибору клану ----------
async def ask_clan_choice(message: types.Message):
    buttons = [
        [InlineKeyboardButton(text=clan, callback_data=f"clan_{clan.split()[0]}")]
        for clan in CLANS.keys()
    ]
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
    elif row and row.get("username") and not row.get("clan"):
        # Пользователь есть, но клан не выбран
        await message.answer(f"Привет, <b>{row['username']}</b>! Пожалуйста, выбери клан.")
        await ask_clan_choice(message)
    else:
        waiting_for_nick.add(user_id)
        await message.answer("Привет! Напиши, пожалуйста, свой никнейм.")

# ---------- Обробка повідомлень ----------
@dp.message()
async def handle_messages(message: types.Message):
    await ping_fly_machine()
    
    user_id = message.from_user.id
    text = message.text.strip()

    # ----- Введення ника -----
    # --- У handle_messages: після введення ніку (ні кнопки меню) ---
    if user_id in waiting_for_nick:
        nickname = text

        # 1. Заборонені символи
        if re.search(r"[;:/.\"<>'\\\\]", nickname):
            await message.answer(
                "❗ Никнейм содержит недопустимые символы. Используй только буквы, цифры и подчёркивания.")
            return

        # 2. Заборонене слово "script"
        if "script" in nickname.lower():
            await message.answer("❗ Никнейм не может содержать запрещённые слова.")
            return

        # 3. Перевірка довжини
        if not (3 <= len(nickname) <= 9):
            await message.answer("❗ Никнейм должен быть от 3 до 9 символов.")
            return

        # 4. Дозволені лише латиниця/цифри/_
        if not re.match(r"^[A-Za-z0-9_]+$", nickname):
            await message.answer("❗ Никнейм должен содержать только латинские буквы, цифры и подчёркивания.")
            return

        # Все ок — зберігаємо
        supabase.table("users").upsert({"user_id": user_id, "username": nickname}).execute()
        waiting_for_nick.remove(user_id)
        await message.answer(f"✅ Отлично, <b>{nickname}</b>! Никнейм сохранён.\nТеперь выбери клан.")
        await ask_clan_choice(message)
        return

    # ----- ПРОФІЛЬ -----
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
                f"Характеристики: ❤️{row['health']} | 🛡{row['defense']} | 🗡{row['attack']}\n\n"
                f"🪙 Баланс:\n"
                f"Деньги: {row['money']} 💰\n"
                f"Алмазы: {row['diamonds']} 💎\n\n"
                f"🥋 Одежда:\n"
                f"Голова: {row['head']}\n"
                f"Тело: {row['body']}\n"
                f"Ноги: {row['legs']}\n"
                f"Ступни: {row['feet']}\n\n"
                f"🪛 Снаряжение:\n"
                f"Оружие: {row['weapon']}\n\n"
                f"🧰 Сумка:\n"
                f"{row['bag']}\n\n"
                f"💪 Клан: {row.get('clan', 'нет')}\n"
                f"{clan_desc}"
            )
            await message.answer(profile_text, reply_markup=main_menu_kb)
        else:
            waiting_for_nick.add(user_id)
            await message.answer("Никнейм не найден. Введите свой никнейм.")

    # ----- Приключения -----
    elif text == "🗺️ Приключения":
        await message.answer("⚙️ В разработке...", reply_markup=main_menu_kb)

    # ----- Мой клан -----
    # --- У handle_messages: при натисканні "💪 Мой клан", збираємо ніки ---
    elif text == "💪 Мой клан":
        response = supabase.table("users").select("clan").eq("user_id", user_id).execute()
        row = response.data[0] if response.data else None
        if row and row.get("clan"):
            clan = row["clan"]
            clan_desc = CLANS.get(clan, "")

            members_resp = supabase.table("clan_members").select("user_id").eq("clan_name", clan).execute()
            members = members_resp.data or []
            user_ids = [m["user_id"] for m in members]
            if user_ids:
                users_resp = supabase.table("users").select("user_id, username").in_("user_id", user_ids).execute()
                users_data = users_resp.data or []
                id_to_username = {u["user_id"]: u["username"] for u in users_data}
                members_list = "\n".join(f"- {id_to_username.get(uid, uid)}" for uid in user_ids)
            else:
                members_list = "Пока нет участников"

            await message.answer(
                f"💪 Клан: <b>{clan}</b>\n\n{clan_desc}\n\n"
                f"👥 Участники:\n{members_list}", reply_markup=main_menu_kb
            )
        else:
            await message.answer("Вы еще не выбрали клан. Пожалуйста, выберите клан.", reply_markup=main_menu_kb)
            await ask_clan_choice(message)


    # ----- ТОП -----
    elif text == "🏆 Топ":
        await message.answer("Выберите тип топа:", reply_markup=top_menu_kb)

    elif text == "🌟 Топ по уровню":
        full_response = supabase.table("users").select("user_id, username, level").order("level", desc=True).execute()
        players = full_response.data

        if players:
            top_10 = players[:10]
            players_list = "\n".join(f"{i + 1}. {p['username']} 🌟 {p['level']}" for i, p in enumerate(top_10))

            current_user_place = next((i + 1 for i, p in enumerate(players) if p["user_id"] == user_id), None)
            suffix = f"\n\n📍Твое место: {current_user_place}" if current_user_place else ""
            await message.answer(f"🌟 <b>Топ по уровню:</b>\n\n{players_list}{suffix}", reply_markup=top_menu_kb)
        else:
            await message.answer("Список игроков пуст.", reply_markup=top_menu_kb)

    elif text == "💰 Топ по деньгам":
        full_response = supabase.table("users").select("user_id, username, money").order("money", desc=True).execute()
        players = full_response.data

        if players:
            top_10 = players[:10]
            players_list = "\n".join(f"{i + 1}. {p['username']} 💰 {p['money']}" for i, p in enumerate(top_10))

            current_user_place = next((i + 1 for i, p in enumerate(players) if p["user_id"] == user_id), None)
            suffix = f"\n\n📍 Твое место: {current_user_place}" if current_user_place else ""
            await message.answer(f"💰 <b>Топ по деньгам:</b>\n\n{players_list}{suffix}", reply_markup=top_menu_kb)
        else:
            await message.answer("Список игроков пуст.", reply_markup=top_menu_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    # ----- КУЗНЯ -----
    elif text == "⚒️ Кузница":
        await message.answer("Выберите действие:", reply_markup=forge_menu_kb)

    elif text == "⚔️ Заточка" or text == "🔨 Крафт":
        await message.answer("⚙️ В разработке...", reply_markup=forge_menu_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    # ----- Торговля -----
    elif text == "🛍️ Торговля":
        await message.answer("⚙️ В разработке...", reply_markup=main_menu_kb)

    else:
        await message.answer("❓ Неизвестная команда. Используй кнопки меню или напиши /start.", reply_markup=main_menu_kb)

# ---------- Обробка callback для вибору клану ----------
@dp.callback_query()
async def handle_clan_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data  # формат: clan_<Клан>

    if data.startswith("clan_"):
        clan_key = data[5:]  # отримуємо назву клану без префіксу
        # Шукаємо клан повністю за ключем (по першому слову)
        clan_name = None
        for name in CLANS.keys():
            if name.startswith(clan_key):
                clan_name = name
                break

        if clan_name is None:
            await callback.message.answer("Ошибка: клан не найден.")
            await callback.answer()
            return

        desc = CLANS[clan_name]

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="Выбрать", callback_data=f"select_{clan_key}"),
                InlineKeyboardButton(text="Назад", callback_data="back_to_clans")
            ]
        ])

        await callback.message.edit_text(desc, reply_markup=keyboard)
        await callback.answer()

    elif data.startswith("select_"):
        clan_key = data[7:]
        clan_name = None
        for name in CLANS.keys():
            if name.startswith(clan_key):
                clan_name = name
                break
        if clan_name is None:
            supabase.table("users").update({"clan": clan_name}).eq("user_id", user_id).execute()
            supabase.table("clan_members").upsert({"clan_name": clan_name, "user_id": user_id}).execute()

            await callback.message.edit_text(f"Вы успешно выбрали клан:\n\n{CLANS[clan_name]}", reply_markup=None)
            await bot.send_message(user_id, "Теперь тебе доступно главное меню ⬇️", reply_markup=main_menu_kb)
            await callback.answer()

        # Записуємо клан в таблиці users і clan_members
        supabase.table("users").update({"clan": clan_name}).eq("user_id", user_id).execute()

        supabase.table("clan_members").upsert({
            "clan_name": clan_name,
            "user_id": user_id
        }).execute()

        await callback.message.edit_text(f"Вы успешно выбрали клан:\n\n{CLANS[clan_name]}")
        await callback.answer("Клан выбран!")

    elif data == "back_to_clans":
        # Повертаємось до вибору клану
        buttons = [
            [InlineKeyboardButton(text=clan, callback_data=f"clan_{clan.split()[0]}")]
            for clan in CLANS.keys()
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

        description = (
            "🧭 <b>Выбери один из кланов:</b>\n\n"
            "🌌 <b>Звездные стражи</b> — воины света и защитники порядка\n"
            "🔥 <b>Сияющие маяки</b> — символ надежды и силы духа\n"
            "🌑 <b>Тенистые клинки</b> — скрытные и смертоносные бойцы\n"
            "🎵 <b>Безмолвные песни</b> — мудрецы, владеющие тайными знаниями"
        )
        await callback.message.edit_text(description, reply_markup=keyboard)
        await callback.answer()

# ---------- ПОВІДОМЛЕННЯ ВСІМ ПРИ СТАРТІ ----------
async def notify_users_on_start():
    response = supabase.table("users").select("user_id").execute()
    users = response.data
    for user in users:
        try:
            await bot.send_message(user["user_id"], "🤖 Бот работает ✅")
        except Exception:
            pass

# ---------- ОСНОВНИЙ ЗАПУСК ----------
app = FastAPI()

@app.get("/")
async def root():
    return {"status": "ok"}

def run_fastapi():
    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")

# Основна async-функція бота
async def main():
    await notify_users_on_start()
    await dp.start_polling(bot)

# Головний запуск
if __name__ == "__main__":
    # Запуск FastAPI-сервера у фоновому потоці
    threading.Thread(target=run_fastapi, daemon=True).start()

    # Запуск Telegram-бота
    import asyncio
    asyncio.run(main())

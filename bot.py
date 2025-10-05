import os
import asyncio
import re
import random
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from aiogram import Bot, Dispatcher, types, F
from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.client.default import DefaultBotProperties
from supabase import create_client, Client
from dotenv import load_dotenv


# ---------- Load environment ----------


now = datetime.now(timezone.utc)
load_dotenv()
TOKEN = os.getenv("BOT_TOKEN")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")

if not TOKEN or not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Перевірте BOT_TOKEN, SUPABASE_URL та SUPABASE_ANON_KEY в .env")

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
waiting_for_price = set()
lot_creation_data = {}

waiting_for_nick = set()

# ---------- Keyboards ----------
cancel_search_kb = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="❌ Уйти с арены", callback_data="pvp_cancel")]
    ]
)
arena_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔍 Начать поиск противника")],
        [KeyboardButton(text="⬅️ Главная")],
    ],
    resize_keyboard=True
)

market_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Создать лот"), KeyboardButton(text="❌ Убрать лот")],
        [KeyboardButton(text="⬅️ Назад (торговля)")]
    ],
    resize_keyboard=True
)

donate_shop_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="👑 Премиум"), KeyboardButton(text="💎 Алмазы")],
        [KeyboardButton(text="⬅️ Назад (торговля)")]
    ],
    resize_keyboard=True
)
trade_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🛒 Магазин"), KeyboardButton(text="💎 Донат Магазин"), KeyboardButton(text="🏪 Рынок")],
        [KeyboardButton(text="⬅️ Главная")]
    ],
    resize_keyboard=True
)


main_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🗺️ Приключения"), KeyboardButton(text="⚒️ Кузница")],
        [KeyboardButton(text="👤 Профиль"), KeyboardButton(text="💪 Мой клан"), KeyboardButton(text="🏆 Топ"), KeyboardButton(text="🛍️ Торговля")],
        [KeyboardButton(text="⚔️ Арена"), KeyboardButton(text="🛡️ Клановая битва")],
    ],
    resize_keyboard=True
)

top_menu_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🌟 Топ по уровню"), KeyboardButton(text="💰 Топ по деньгам")],
        [KeyboardButton(text="⚔️ Топ по PvP победам")],
        [KeyboardButton(text="⬅️ Главная")],
    ],
    resize_keyboard=True
)

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

clan_battle_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📌 Сделать пин"), KeyboardButton(text="📊 Результаты битвы")],
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

# Основная клавиатура профиля
profile_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🎒 Рюкзак"), KeyboardButton(text="⚙️ Прокачка")],
        [KeyboardButton(text="⚔️ Надеть"), KeyboardButton(text="❌ Снять")],
        [KeyboardButton(text="⬅️ Главная")]
    ],
    resize_keyboard=True
)

backpack_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🪖 Голова", callback_data="slot_head"), InlineKeyboardButton(text="👕 Тело", callback_data="slot_body")],
    [InlineKeyboardButton(text="🧤 Руки", callback_data="slot_gloves"), InlineKeyboardButton(text="👖 Ноги", callback_data="slot_legs")],
    [InlineKeyboardButton(text="🥾 Ступни", callback_data="slot_feet"), InlineKeyboardButton(text="🗡 Оружие", callback_data="slot_weapon")],
    [InlineKeyboardButton(text="📦 Ресурсы", callback_data="view_resources")]
])

# Создание клавиатуры для выбора экипировки
equip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🪖 Голова"), KeyboardButton(text="👕 Тело"), KeyboardButton(text="🧤 Руки")],
        [KeyboardButton(text="👖 Ноги"), KeyboardButton(text="👟 Ступни"), KeyboardButton(text="🗡️ Оружие")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True
)
# Клавиатура для снятия экипировки
unequip_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="❌ Голова"), KeyboardButton(text="❌ Тело"), KeyboardButton(text="❌ Руки")],
        [KeyboardButton(text="❌ Ноги"), KeyboardButton(text="❌ Ступни"), KeyboardButton(text="❌ Оружие")],
        [KeyboardButton(text="⬅️ Назад")],
    ],
    resize_keyboard=True
)

async def notify_users_on_start():
    print("Бот запущен и уведомляет пользователей...")
    # Тут можна зробити розсилку або інші дії


async def broadcast_battle_results():
    try:
        response = supabase.table("users").select("user_id", "username").execute()
        users = response.data or []

        if not users:
            print("⚠️ Нет пользователей для рассылки.")
            return

        # Составляем текст
        allowed_locations = {
            "🏰 Проклятая Цитадель",
            "🌋 Утроба Вулкана",
            "🕸️ Паутина Забвения",
            "👁️ Обитель Иллюзий"
        }

        clancv_table = supabase.table("clancv").select("*").execute()
        clancv_rows = clancv_table.data or []

        result_lines = []
        for location in allowed_locations:
            controlling_clan = None
            for row in clancv_rows:
                if row.get(location):
                    controlling_clan = row["clan_name"]
                    break
            if controlling_clan:
                result_lines.append(f"{location} — под контролем клана *{controlling_clan}*")
            else:
                result_lines.append(f"{location} — под контролем монстров")

        result_text = "\n".join(result_lines)
        full_message = f"📊 *Результаты клановой битвы:*\n\n{result_text}"

        # Рассылка по user_id
        for user in users:
            user_id = user["user_id"]
            username = user.get("username", "неизвестен")
            try:
                await bot.send_message(chat_id=user_id, text=full_message, parse_mode="Markdown")
                print(f"📨 Отправлено @{username} ({user_id})")
            except Exception as e:
                print(f"❌ Не удалось отправить @{username} ({user_id}): {e}")

        print("✅ Рассылка завершена.")
    except Exception as e:
        print(f"❌ Ошибка при рассылке: {e}")


async def show_clan_control_status():
    try:
        print("📢 Показ текущего контроля над локациями...")

        allowed_locations = {
            "🏰 Проклятая Цитадель",
            "🌋 Утроба Вулкана",
            "🕸️ Паутина Забвения",
            "👁️ Обитель Иллюзий"
        }

        # Получаем текущие данные из clancv
        clancv_table = supabase.table("clancv").select("*").execute()
        clancv_rows = clancv_table.data or []

        for location in allowed_locations:
            controlling_clan = None

            for row in clancv_rows:
                if row.get(location) == True:
                    controlling_clan = row["clan_name"]
                    break  # нашли первого — выходим

            if controlling_clan:
                print(f"📍 {location}: находится под контролем клана {controlling_clan}")
            else:
                print(f"📍 {location}: локация свободна")

    except Exception as e:
        print(f"❌ Ошибка при выводе статуса локаций: {e}")



async def run_clear_results():
    print("🧹 [19:00:01] Обнуляем результаты...")
    # Очистка result_clan_battle
    result_table = supabase.table("result_clan_battle").select("*").execute()
    existing_rows = result_table.data or []
    if existing_rows:
        columns_to_reset = [key for key in existing_rows[0].keys() if key != "clan_name"]
        for row in existing_rows:
            clan_name = row["clan_name"]
            reset_data = {col: 0 for col in columns_to_reset}
            supabase.table("result_clan_battle").update(reset_data).eq("clan_name", clan_name).execute()
        print("✅ Таблица result_clan_battle обнулена.")
    else:
        print("⚠️ Таблица result_clan_battle пуста.")

async def run_calculate_results():
    print("📊 [19:01:01] Считаем результаты...")
    response = supabase.table("clan_battle").select("clan_name, pin, health, attack").execute()
    data = response.data or []
    results = {}
    for row in data:
        clan = row.get("clan_name")
        pin = row.get("pin")
        health = row.get("health", 0)
        attack = row.get("attack", 0)
        if clan and pin:
            value = health * attack
            results[(clan, pin)] = results.get((clan, pin), 0) + value
    for (clan, pin), value_to_add in results.items():
        supabase.table("result_clan_battle").update({pin: value_to_add}).eq("clan_name", clan).execute()
    print("✅ Результаты записаны.")

async def run_clear_clan_battle():
    print("🗑️ [19:02:01] Очищаем clan_battle...")
    supabase.table("clan_battle").delete().neq("clan_name", "").execute()
    print("✅ Таблица clan_battle очищена.")

async def run_update_clancv():
    print("📌 [19:03:01] Обновляем clancv...")
    allowed_locations = {
        "🏰 Проклятая Цитадель",
        "🌋 Утроба Вулкана",
        "🕸️ Паутина Забвения",
        "👁️ Обитель Иллюзий"
    }

    # Сброс значений
    clancv_table = supabase.table("clancv").select("clan_name").execute()
    clancv_rows = clancv_table.data or []
    for row in clancv_rows:
        clan_name = row["clan_name"]
        reset_locations = {location: False for location in allowed_locations}
        supabase.table("clancv").update(reset_locations).eq("clan_name", clan_name).execute()
    print("🔄 Все значения сброшены.")

    # Определение победителей
    result_table = supabase.table("result_clan_battle").select("*").execute()
    updated_rows = result_table.data or []
    for location in allowed_locations:
        max_damage = 0
        top_clan = None
        for row in updated_rows:
            clan_name = row["clan_name"]
            damage = row.get(location, 0)
            if damage > max_damage:
                max_damage = damage
                top_clan = clan_name
        if top_clan:
            supabase.table("clancv").update({location: True}).eq("clan_name", top_clan).execute()
            print(f"🏆 {location}: победитель — {top_clan} ({max_damage})")
        else:
            print(f"⚠️ {location}: нет победителя.")

    await show_clan_control_status()

# Планировщик
async def scheduler():
    while True:
        now = datetime.now(timezone.utc)  # timezone-aware время
        run_times = {
            "clear_results": now.replace(hour=16, minute=55, second=1, microsecond=0),
            "calculate_results": now.replace(hour=16, minute=56, second=1, microsecond=0),
            "clear_clan_battle": now.replace(hour=16, minute=57, second=1, microsecond=0),
            "update_clancv": now.replace(hour=16, minute=58, second=1, microsecond=0),
        }

        for key in run_times:
            if now >= run_times[key]:
                run_times[key] += timedelta(days=1)

        for name, run_time in run_times.items():
            wait = (run_time - datetime.now(timezone.utc)).total_seconds()
            print(f"⏳ Ждём до {name} ({run_time.time()} UTC) — {wait} секунд")
            await asyncio.sleep(wait)

            if name == "clear_results":
                await run_clear_results()
            elif name == "calculate_results":
                await run_calculate_results()
            elif name == "clear_clan_battle":
                await run_clear_clan_battle()
            elif name == "update_clancv":
                await run_update_clancv()
                await broadcast_battle_results()

ITEMS_PER_PAGE = 10

async def create_paginated_inline_keyboard(user_id, items, supabase, page=0, category="все"):
    backpack_data = supabase.table("backpack").select("item_name, count").eq("user_id", user_id).execute()

    if not backpack_data.data:
        return None

    filtered_items = []
    for item in backpack_data.data:
        item_name = item['item_name']
        item_count = item['count']

        for category_name, category_data in items.items():
            for set_item in category_data:
                if set_item['name'] == item_name:
                    if category == "все" or category_name == category:
                        filtered_items.append((set_item, item_count))
                    break

    if not filtered_items:
        return None

    # Пагінація
    start = page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE
    paginated_items = filtered_items[start:end]

    buttons = [
        InlineKeyboardButton(
            text=f"{item['name']} ({count})",
            callback_data=f"create_lot:{item['name']}"
        )
        for item, count in paginated_items
    ]

    # Розкладка в 2 колонки
    keyboard_rows = [buttons[i:i+2] for i in range(0, len(buttons), 2)]

    # Кнопки пагінації
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(
            InlineKeyboardButton(text="⬅️ Назад", callback_data=f"page:{page - 1}")
        )
    if end < len(filtered_items):
        pagination_buttons.append(
            InlineKeyboardButton(text="➡️ Далее", callback_data=f"page:{page + 1}")
        )

    if pagination_buttons:
        keyboard_rows.append(pagination_buttons)

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)



ITEMS_PER_PAGE = 10


async def show_market(message: types.Message, page: int = 1):
    offset = (page - 1) * ITEMS_PER_PAGE

    # Получаем лоты с БД
    result = supabase.table("rynok") \
        .select("*") \
        .order("id", desc=False) \
        .range(offset, offset + ITEMS_PER_PAGE - 1) \
        .execute()

    data = result.data
    if not data:
        await message.answer("❗ Рынок пуст.")
        return

    # Формируем текст
    market_text = f"🏪 <b>Лоты на рынке (стр. {page})</b>:\n\n"
    for i, lot in enumerate(data, start=1 + offset):
        market_text += f"{i}. <b>{lot['item_name']}</b> — {lot['cost']} монет\n"

    # === Кнопки с предметами ===
    item_buttons = []
    row = []
    for i, lot in enumerate(data):
        button = InlineKeyboardButton(
            text=lot['item_name'],
            callback_data=f"buy_{lot['id']}"  # Привязываем к id лота для покупки
        )
        row.append(button)
        if len(row) == 2:
            item_buttons.append(row)
            row = []
    if row:
        item_buttons.append(row)

    # === Кнопки пагинации ===
    total_lots = supabase.table("rynok").select("id", count="exact").execute().count or 0
    max_page = (total_lots + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    pagination_buttons = []
    if page > 1:
        pagination_buttons.append(InlineKeyboardButton(text="⏪ Назад", callback_data=f"market_page_{page - 1}"))
    if page < max_page:
        pagination_buttons.append(InlineKeyboardButton(text="⏩ Далее", callback_data=f"market_page_{page + 1}"))

    if pagination_buttons:
        item_buttons.append(pagination_buttons)

    keyboard = InlineKeyboardMarkup(inline_keyboard=item_buttons)

    await message.answer(market_text, parse_mode="HTML", reply_markup=keyboard)


@dp.message(lambda message: message.from_user.id in waiting_for_price)
async def handle_price_input(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Перевірка: тільки цифри
    if not text.isdigit():
        await message.answer("❗ Введите только число. Без букв, символов или пробелов.")
        return

    price = int(text)
    item_name = lot_creation_data.get(user_id)

    # ⬇️ Зменшити кількість предмета в backpack на 1
    result = supabase.table("backpack") \
        .select("count") \
        .eq("user_id", user_id) \
        .eq("item_name", item_name) \
        .limit(1) \
        .execute()

    if not result.data:
        await message.answer("❗ У вас нет такого предмета в рюкзаке.")
        waiting_for_price.remove(user_id)
        lot_creation_data.pop(user_id, None)
        return

    current_count = result.data[0]['count']
    if current_count <= 0:
        await message.answer("❗ Недостаточно количества предмета.")
        return

    # Якщо залишиться 0 — можна видалити рядок або залишити з 0
    if current_count == 1:
        supabase.table("backpack") \
            .delete() \
            .eq("user_id", user_id) \
            .eq("item_name", item_name) \
            .execute()
    else:
        supabase.table("backpack") \
            .update({"count": current_count - 1}) \
            .eq("user_id", user_id) \
            .eq("item_name", item_name) \
            .execute()

    # 🛒 Додати лот у таблицю rynok
    supabase.table("rynok").insert({
        "user_id": user_id,
        "item_name": item_name,
        "cost": price
    }).execute()

    # ✅ Повідомлення
    await message.answer(
        f"✅ Лот на <b>{item_name}</b> создан с ценой <b>{price}</b> монет!\n"
        f"📉 Из рюкзака списано 1 предмет.",
        parse_mode="HTML"
    )

    # Очистити стан
    waiting_for_price.remove(user_id)
    lot_creation_data.pop(user_id, None)

@dp.message(lambda message: message.text == "🏪 Рынок")
async def handle_market_button(message: types.Message):
    await message.answer("🏪 Добро пожаловать на рынок! Выберите действие:", reply_markup=market_menu_kb)
    await show_market(message, page=1)


@dp.message(lambda message: message.text == "🛒 Создать лот")
async def handle_create_lot_start(message: types.Message):
    user_id = message.from_user.id
    keyboard = await create_paginated_inline_keyboard(user_id, items, supabase, page=0)

    if keyboard:
        await message.answer("🎒 Выберите предмет для создания лота:", reply_markup=keyboard)
    else:
        await message.answer("У вас нет предметов в рюкзаке.")


@dp.message(lambda message: message.text == "❌ Убрать лот")
async def handle_remove_lot_menu(message: types.Message):
    await show_user_lots(message, page=1)

ITEMS_PER_PAGE = 10  # можно изменить

async def show_user_lots(message_or_callback, page: int = 1):
    user_id = message_or_callback.from_user.id if hasattr(message_or_callback, "from_user") else message_or_callback.from_user.id
    offset = (page - 1) * ITEMS_PER_PAGE

    result = supabase.table("rynok") \
        .select("*") \
        .eq("user_id", user_id) \
        .order("id", desc=False) \
        .range(offset, offset + ITEMS_PER_PAGE - 1) \
        .execute()

    data = result.data
    if not data:
        await message_or_callback.answer("❗ У вас нет выставленных лотов.")
        return

    text = f"❌ <b>Выберите лот для удаления (стр. {page})</b>:\n\n"
    for i, lot in enumerate(data, start=1 + offset):
        text += f"{i}. <b>{lot['item_name']}</b> — {lot['cost']} монет\n"

    # Инлайн кнопки
    keyboard = []
    row = []
    for lot in data:
        row.append(InlineKeyboardButton(
            text=lot["item_name"],
            callback_data=f"remove_lot_{lot['id']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Кнопки пагинации
    total = supabase.table("rynok").select("id", count="exact").eq("user_id", user_id).execute().count or 0
    max_page = (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE

    pagination_row = []
    if page > 1:
        pagination_row.append(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"user_lots_page_{page - 1}"))
    if page < max_page:
        pagination_row.append(InlineKeyboardButton(text="➡️ Далее", callback_data=f"user_lots_page_{page + 1}"))
    if pagination_row:
        keyboard.append(pagination_row)

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

    if isinstance(message_or_callback, types.CallbackQuery):
        await message_or_callback.message.edit_text(text, parse_mode="HTML", reply_markup=markup)
    else:
        await message_or_callback.answer(text, parse_mode="HTML", reply_markup=markup)


# ----------EXP ---------

async def add_experience(user_id: int, amount: int):
    response = supabase.table("users").select("exp, level, level_points").eq("user_id", user_id).execute()
    if not response.data:
        return

    user = response.data[0]
    current_exp = user.get("exp", 0)
    level = user.get("level", 1)
    level_points = user.get("level_points", 0)

    new_exp = current_exp + amount
    exp_max = level * 100
    level_ups = 0

    while new_exp >= exp_max:
        new_exp -= exp_max
        level += 1
        level_ups += 1
        exp_max = level * 100

    # Если уровень больше 75, очки прокачки не даём
    if level > 75:
        level_points_to_add = 0
    else:
        level_points_to_add = level_ups

    # Обновление уровня, опыта и очков прокачки
    supabase.table("users").update({
        "exp": new_exp,
        "level": level,
        "exp_max": exp_max,
        "level_points": level_points + level_points_to_add
    }).eq("user_id", user_id).execute()

    if level_ups > 0:
        await bot.send_message(
            user_id,
            f"🌟 <b>Поздравляем!</b> Вы достигли <b>{level} уровня</b>!\n"
            f"🎉 Вы получили <b>{level_points_to_add}</b> очков прокачки!"
        )



async def create_inline_keyboard_from_backpack(user_id, category):
    # Получаем все предметы из рюкзака пользователя
    backpack_data = supabase.table("backpack").select("item_name, count").eq("user_id", user_id).execute()

    if not backpack_data.data:
        return None  # Нет предметов в рюкзаке

    filtered_items = []

    # Ищем предметы по категории в full_items
    for item in backpack_data.data:
        item_name = item['item_name']
        item_count = item['count']
        matched = False

        for category_name, item_list in full_items.items():
            if category_name != category:
                continue

            for equip_item in item_list:
                if equip_item['name'] == item_name:
                    filtered_items.append((equip_item, item_count))
                    matched = True
                    break
            if matched:
                break

    if not filtered_items:
        return None  # Ничего не найдено по категории

    # Генерация инлайн-кнопок
    buttons = [
        InlineKeyboardButton(
            text=f"{item['name']} ({count})",
            callback_data=item['callback_data']
        )
        for item, count in filtered_items
    ]

    # Кнопки по два в ряд
    keyboard_rows = [buttons[i:i + 2] for i in range(0, len(buttons), 2)]

    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)


def get_item_stats(item_name):
    for tier in SETS.values():
        for set_data in tier.values():
            for item in set_data["items"]:
                if item["name"] == item_name:
                    return item["hp"], item["damage"]
    return 0, 0


def build_pvp_message(player, opponent):
    return (
        f"👤 Вы: {player['username']}\n"
        f"❤️ Здоровье: {player['health']}\n"
        f"⚔️ Атака: {player['attack']}\n"
        f"🛡️ Уклонение: {player['dodge']}\n"
        f"💥 Крит: {player['crit']}\n"
        f"🔁 Контратака: {player['counter_attack']}\n\n"

        f"🎯 Противник: {opponent['username']}\n"
        f"❤️ Здоровье: {opponent['health']}\n"
        f"⚔️ Атака: {opponent['attack']}\n"
        f"🛡️ Уклонение: {opponent['dodge']}\n"
        f"💥 Крит: {opponent['crit']}\n"
        f"🔁 Контратака: {opponent['counter_attack']}"
    )



# ---------- Clans ----------
CLANS = {
    "Звездные стражи 🌌": "🛡 <b>Звездные стражи</b> — это древнее и неуловимое братство, чья связь с космосом и тайнами вселенной глубока и неразрывна. Они — вечные наблюдатели, хранители небесного порядка и защитники миров от угроз, исходящих из бездны космоса. Их взгляд устремлен к звездам, а сердца бьются в ритме галактических циклов.",
    "Сияющие маяки 🔥": "🔥 <b>Сияющие маяки</b> — это древний и благородный орден, чья миссия заключается в том, чтобы нести свет, надежду и истину через самые темные времена. Они — путеводная звезда для заблудших, символ непоколебимой веры и оплот против тьмы и хаоса. Их сила исходит из чистоты намерений, непоколебимой решимости и внутренней гармонии, которая отражается во всем, что они делают.",
    "Тенистые клинки 🌑": "🌑 <b>Тенистые клинки</b> — это древнее братство, чье существование окутано тайной и легендами. Они не стремятся к славе или открытому признанию, предпочитая действовать из теней, словно невидимые вихри, которые оставляют за собой лишь след судьбы.",
    "Безмолвные песни 🎵": "🎵 <b>Безмолвные песни</b> — это загадочное и меланхоличное сообщество, чье существование окутано завесой печали и древних тайн. Они не владеют острыми клинками или громогласными криками, их оружие — это эмоции, воспоминания и эхо забытых мелодий. Члены этого клана — хранители скорби, носители утерянных историй и проводники через лабиринты человеческих чувств."
}
items = {
    "head": [
        {"name": "Шлем Стража", "callback_data": "equip_helmet_guard"},
        {"name": "Серьги Хищника", "callback_data": "equip_ear_predator"},
        {"name": "Шлем Судьбы", "callback_data": "equip_helmet_fate"},
        {"name": "Шлем Былого", "callback_data": "equip_helmet_of_old"},
        {"name": "Капюшон Света", "callback_data": "equip_hood_of_light"},
        {"name": "Шляпа Охотника", "callback_data": "equip_hunter_hat"}
    ],
    "body": [
        {"name": "Плащ Жизни", "callback_data": "equip_cloak_of_life"},
        {"name": "Амулет Хищника", "callback_data": "equip_amulet_of_predator"},
        {"name": "Амулет Правосудия", "callback_data": "equip_amulet_of_justice"},
        {"name": "Доспех Чести", "callback_data": "equip_armor_of_honor"},
        {"name": "Куртка Света", "callback_data": "equip_jacket_of_light"},
        {"name": "Плащ Теней", "callback_data": "equip_cloak_of_shadows"}
    ],
    "gloves": [
        {"name": "Перчатки Защиты", "callback_data": "equip_gloves_of_protection"},
        {"name": "Перчатки Гнева", "callback_data": "equip_gloves_of_wrath"},
        {"name": "Перчатки Карающего", "callback_data": "equip_gloves_of_avenger"},
        {"name": "Наручи Былого", "callback_data": "equip_bracers_of_old"},
        {"name": "Перчатки Красок", "callback_data": "equip_gloves_of_paint"},
        {"name": "Перчатки Охотника", "callback_data": "equip_hunter_gloves"}
    ],
    "legs": [
        {"name": "Пояс Скалы", "callback_data": "equip_belt_of_rock"},
        {"name": "Пояс Хищника", "callback_data": "equip_belt_of_predator"},
        {"name": "Пояс Ответа", "callback_data": "equip_belt_of_revenge"},
        {"name": "Пояс Нерушимости", "callback_data": "equip_belt_of_indestructibility"},
        {"name": "Юбка Света", "callback_data": "equip_skirt_of_light"},
        {"name": "Штаны Охотника", "callback_data": "equip_hunter_pants"}
    ],
    "feet": [
        {"name": "Наручи Титана", "callback_data": "equip_bracers_of_titan"},
        {"name": "Сапоги Бури", "callback_data": "equip_boots_of_storm"},
        {"name": "Сапоги Ярости", "callback_data": "equip_boots_of_rage"},
        {"name": "Поножи Былого", "callback_data": "equip_greaves_of_old"},
        {"name": "Сапоги Света", "callback_data": "equip_boots_of_light"},
        {"name": "Кожаные Сапоги", "callback_data": "equip_leather_boots"}
    ],
    "weapon": [
        {"name": "Щит Вечной Стали", "callback_data": "equip_shield_of_eternal_steel"},
        {"name": "Меч Бури", "callback_data": "equip_sword_of_storm"},
        {"name": "Клинок Возмездия", "callback_data": "equip_blade_of_vengeance"},
        {"name": "Ржавая Секира", "callback_data": "equip_rusty_axe"},
        {"name": "Клинок Света", "callback_data": "equip_blade_of_light"},
        {"name": "Трость-хлыст", "callback_data": "equip_whip_staff"}
    ]
}

locations = {
    "🏰 Проклятая Цитадель": "Величественные руины древнего замка, утопающего в тумане и загадках прошлого.",
    "🌋 Утроба Вулкана": "Огненная пещера с мерцающими лавовыми потоками и горячими источниками, наполненная силой природы.",
    "🕸️ Паутина Забвения": "Туманный каньон, украшенный гигантскими сверкающими паутинами, переливающимися в солнечном свете.",
    "👁️ Обитель Иллюзий": "Мистическое место, где небо играет всеми оттенками, а мир словно растворяется в волшебстве."
}

allowed_locations = {
    "🏰 Проклятая Цитадель",
    "🌋 Утроба Вулкана",
    "🕸️ Паутина Забвения",
    "👁️ Обитель Иллюзий"
}

full_items = {
    "head": [
        {"name": "Шлем Стража", "callback_data": "equip_helmet_guard"},
        {"name": "Серьги Хищника", "callback_data": "equip_ear_predator"},
        {"name": "Шлем Судьбы", "callback_data": "equip_helmet_fate"},
        {"name": "Шлем Былого", "callback_data": "equip_helmet_of_old"},
        {"name": "Капюшон Света", "callback_data": "equip_hood_of_light"},
        {"name": "Шляпа Охотника", "callback_data": "equip_hunter_hat"},
        {"name": "Капюшон Стратегии", "callback_data": "equip_hood_of_strategy"}
    ],
    "body": [
        {"name": "Плащ Жизни", "callback_data": "equip_cloak_of_life"},
        {"name": "Амулет Хищника", "callback_data": "equip_amulet_of_predator"},
        {"name": "Амулет Правосудия", "callback_data": "equip_amulet_of_justice"},
        {"name": "Доспех Чести", "callback_data": "equip_armor_of_honor"},
        {"name": "Куртка Света", "callback_data": "equip_jacket_of_light"},
        {"name": "Плащ Теней", "callback_data": "equip_cloak_of_shadows"},
        {"name": "Куртка Искателя", "callback_data": "equip_jacket_of_seeker"}
    ],
    "gloves": [
        {"name": "Перчатки Защиты", "callback_data": "equip_gloves_of_protection"},
        {"name": "Перчатки Гнева", "callback_data": "equip_gloves_of_wrath"},
        {"name": "Перчатки Карающего", "callback_data": "equip_gloves_of_avenger"},
        {"name": "Наручи Былого", "callback_data": "equip_bracers_of_old"},
        {"name": "Перчатки Красок", "callback_data": "equip_gloves_of_paint"},
        {"name": "Перчатки Охотника", "callback_data": "equip_hunter_gloves"},
        {"name": "Перчатки Мастера", "callback_data": "equip_gloves_of_master"}
    ],
    "legs": [
        {"name": "Пояс Скалы", "callback_data": "equip_belt_of_rock"},
        {"name": "Пояс Хищника", "callback_data": "equip_belt_of_predator"},
        {"name": "Пояс Ответа", "callback_data": "equip_belt_of_revenge"},
        {"name": "Пояс Нерушимости", "callback_data": "equip_belt_of_indestructibility"},
        {"name": "Юбка Света", "callback_data": "equip_skirt_of_light"},
        {"name": "Штаны Охотника", "callback_data": "equip_hunter_pants"},
        {"name": "Ремень Тактика", "callback_data": "equip_belt_of_tactician"}
    ],
    "feet": [
        {"name": "Наручи Титана", "callback_data": "equip_bracers_of_titan"},
        {"name": "Сапоги Бури", "callback_data": "equip_boots_of_storm"},
        {"name": "Сапоги Ярости", "callback_data": "equip_boots_of_rage"},
        {"name": "Поножи Былого", "callback_data": "equip_greaves_of_old"},
        {"name": "Сапоги Света", "callback_data": "equip_boots_of_light"},
        {"name": "Кожаные Сапоги", "callback_data": "equip_leather_boots"},
        {"name": "Сапоги Скитальца", "callback_data": "equip_boots_of_wanderer"}
    ],
    "weapon": [
        {"name": "Щит Вечной Стали", "callback_data": "equip_shield_of_eternal_steel"},
        {"name": "Меч Бури", "callback_data": "equip_sword_of_storm"},
        {"name": "Клинок Возмездия", "callback_data": "equip_blade_of_vengeance"},
        {"name": "Ржавая Секира", "callback_data": "equip_rusty_axe"},
        {"name": "Клинок Света", "callback_data": "equip_blade_of_light"},
        {"name": "Трость-хлыст", "callback_data": "equip_whip_staff"},
        {"name": "Копьё Уничтожитель Зла", "callback_data": "equip_spear_of_purifier"}
    ]
}
SETS = {
    "strong": {
        "Бастион Титана": {
            "description": "🛡️ Массивный сет, дающий большое количество здоровья и щит для защиты",
            "items": [
                {"id": 1, "name": "Шлем Стража", "hp": 120, "damage": 0, "head": "Голова"},
                {"id": 2, "name": "Плащ Жизни", "hp": 200, "damage": 0, "body": "Тело"},
                {"id": 3, "name": "Перчатки Защиты", "hp": 60, "damage": 0, "gloves": "Перчатки"},
                {"id": 4, "name": "Пояс Скалы", "hp": 120, "damage": 0, "legs": "Ноги"},
                {"id": 5, "name": "Наручи Титана", "hp": 50, "damage": 0, "feet": "Ступни"},
                {"id": 6, "name": "Щит Вечной Стали", "hp": 150, "damage": 80, "weapon": "Оружие"}
            ]
        },
        "Клинок Бури": {
            "description": "⚔️ Легкий и стремительный сет с фокусом на урон",
            "items": [
                {"id": 7, "name": "Серьги Хищника", "hp": 30, "damage": 0, "head": "Голова"},
                {"id": 8, "name": "Амулет Хищника", "hp": 40, "damage": 0, "body": "Тело"},
                {"id": 9, "name": "Перчатки Гнева", "hp": 20, "damage": 0, "gloves": "Перчатки"},
                {"id": 10, "name": "Пояс Хищника", "hp": 30, "damage": 0, "legs": "Ноги"},
                {"id": 11, "name": "Сапоги Бури", "hp": 30, "damage": 0, "feet": "Ступни"},
                {"id": 12, "name": "Меч Бури", "hp": 0, "damage": 180, "weapon": "Оружие"}
            ]
        },
        "Возмездие": {
            "description": "🗡️ Сбалансированный сет с упором на среднее здоровье и урон",
            "items": [
                {"id": 13, "name": "Шлем Судьбы", "hp": 60, "damage": 0, "head": "Голова"},
                {"id": 14, "name": "Амулет Правосудия", "hp": 100, "damage": 0, "body": "Тело"},
                {"id": 15, "name": "Перчатки Карающего", "hp": 40, "damage": 0, "gloves": "Перчатки"},
                {"id": 16, "name": "Пояс Ответа", "hp": 60, "damage": 0, "legs": "Ноги"},
                {"id": 17, "name": "Сапоги Ярости", "hp": 40, "damage": 0, "feet": "Ступни"},
                {"id": 18, "name": "Клинок Возмездия", "hp": 0, "damage": 120, "weapon": "Оружие"}
            ]
        }
    },
    "weak": {
        "Забытый Страж": {
            "description": "🛡️ Надёжный сет с умеренным здоровьем и слабым уроном",
            "items": [
                {"id": 19, "name": "Шлем Былого", "hp": 50, "damage": 0, "head": "Голова"},
                {"id": 20, "name": "Доспех Чести", "hp": 100, "damage": 0, "body": "Тело"},
                {"id": 21, "name": "Наручи Былого", "hp": 40, "damage": 0, "gloves": "Перчатки"},
                {"id": 22, "name": "Пояс Нерушимости", "hp": 60, "damage": 0, "legs": "Ноги"},
                {"id": 23, "name": "Поножи Былого", "hp": 50, "damage": 0, "feet": "Ступни"},
                {"id": 24, "name": "Ржавая Секира", "hp": 0, "damage": 50, "weapon": "Оружие"}
            ]
        },
        "Звёздный Живописец": {
            "description": "✨ Легкий сет с минимальным здоровьем, но сильным оружием",
            "items": [
                {"id": 25, "name": "Капюшон Света", "hp": 15, "damage": 0, "head": "Голова"},
                {"id": 26, "name": "Куртка Света", "hp": 25, "damage": 0, "body": "Тело"},
                {"id": 27, "name": "Перчатки Красок", "hp": 15, "damage": 0, "gloves": "Перчатки"},
                {"id": 28, "name": "Юбка Света", "hp": 20, "damage": 0, "legs": "Ноги"},
                {"id": 29, "name": "Сапоги Света", "hp": 25, "damage": 0, "feet": "Ступни"},
                {"id": 30, "name": "Клинок Света", "hp": 0, "damage": 140, "weapon": "Оружие"}
            ]
        },
        "Охотник": {
            "description": "🏹 Сет для ловкости и средней защиты, с акцентом на оружие",
            "items": [
                {"id": 31, "name": "Шляпа Охотника", "hp": 25, "damage": 0, "head": "Голова"},
                {"id": 32, "name": "Плащ Теней", "hp": 50, "damage": 0, "body": "Тело"},
                {"id": 33, "name": "Перчатки Охотника", "hp": 25, "damage": 0, "gloves": "Перчатки"},
                {"id": 34, "name": "Штаны Охотника", "hp": 30, "damage": 0, "legs": "Ноги"},
                {"id": 35, "name": "Кожаные Сапоги", "hp": 30, "damage": 0, "feet": "Ступни"},
                {"id": 36, "name": "Трость-хлыст", "hp": 0, "damage": 90, "weapon": "Оружие"}
            ]
        }
    },
    "crafter": {
        "Осенний Лист 🍁": {
            "description": "🍁 Балансированный сет легендарного мастера. Осенний Лист сочетает разумную защиту с высоким уроном, используя самодельное, но смертоносное снаряжение.",
            "items": [
                {"id": 37, "name": "Капюшон Стратегии", "hp": 60, "damage": 0, "head": "Голова"},
                {"id": 38, "name": "Куртка Искателя", "hp": 100, "damage": 0, "body": "Тело"},
                {"id": 39, "name": "Перчатки Мастера", "hp": 40, "damage": 0, "gloves": "Перчатки"},
                {"id": 40, "name": "Ремень Тактика", "hp": 60, "damage": 0, "legs": "Ноги"},
                {"id": 41, "name": "Сапоги Скитальца", "hp": 50, "damage": 0, "feet": "Ступни"},
                {"id": 42, "name": "Копьё Уничтожитель Зла", "hp": 80, "damage": 130, "weapon": "Оружие"}
            ]
        }
    }
}

DROP = {
    "epic": {
        "Теневой Обсидиан": {
            "description": "🖤 Тёмный магический минерал, поглощающий свет. Применяется в усилении оружия и элитных доспехов.",
            "chance": 5
        }
    },
    "rare": {
        "Тактическая Кожа": {
            "description": "🧵 Обработанная кожа с элементами усиления. Часто используется мастерами для создания функциональной экипировки.",
            "chance": 5
        }
    },
    "common": {
        "Листовая Сталь": {
            "description": "🍃 Лёгкий, но прочный сплав, сделанный из обработанных листьев и металла. Используется для создания гибкой брони.",
            "chance": 5
        }
    }
}

craft_sets = {
    "Осенний Лист 🍁": {
        "Капюшон Стратегии": {
            "Теневой Обсидиан": 1,
            "Тактическая Кожа": 2,
            "Листовая Сталь": 3
        },
        "Куртка Искателя": {
            "Теневой Обсидиан": 2,
            "Тактическая Кожа": 4,
            "Листовая Сталь": 5
        },
        "Перчатки Мастера": {
            "Тактическая Кожа": 2,
            "Листовая Сталь": 3
        },
        "Ремень Тактика": {
            "Тактическая Кожа": 2,
            "Листовая Сталь": 2
        },
        "Сапоги Скитальца": {
            "Тактическая Кожа": 2,
            "Листовая Сталь": 3
        },
        "Копьё Уничтожитель Зла": {
            "Теневой Обсидиан": 4,
            "Тактическая Кожа": 3,
            "Листовая Сталь": 2
        }
    }
}


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

LOCATIONS = {
    "Большой Лес": {
        "exp": (5, 10),
        "money": (10, 20),
        "duration": 15,
        "min_level": 1,
        "rarity_chances": {
            "epic": 5,
            "rare": 20,
            "common": 75
        }
    },
    "Мёртвая Деревня": {
        "exp": (15, 30),
        "money": (20, 40),
        "duration": 30,
        "min_level": 10,
        "rarity_chances": {
            "epic": 10,
            "rare": 25,
            "common": 65
        }
    },
    "Заброшенный Замок": {
        "exp": (40, 60),
        "money": (50, 100),
        "duration": 60,
        "min_level": 20,
        "rarity_chances": {
            "epic": 15,
            "rare": 30,
            "common": 55
        }
    }
}

MONSTERS = {
    "Туманный Волк": {
        "hp": 100, "damage": 20, "dodge": 10, "counter": 0,
        "description": "Хищник, скрывающийся в тумане. Быстрый и коварный.",
        "rarity": "common"
    },
    "Древесный Страж": {
        "hp": 150, "damage": 10, "dodge": 0, "counter": 20,
        "description": "Существо из корней и листвы. Защищает лес от незваных гостей.",
        "rarity": "common"
    },
    "Лесной Жутень": {
        "hp": 100, "damage": 20, "dodge": 30, "counter": 10,
        "description": "Тварь, порождённая страхами путников. Питается страхом и болью.",
        "rarity": "rare"
    },
    "Призрачный Олень": {
        "hp": 70, "damage": 10, "dodge": 50, "counter": 0,
        "description": "Легендарный дух леса. Встреча с ним — знак судьбы.",
        "rarity": "rare"
    },
    "Корнеплет": {
        "hp": 200, "damage": 15, "dodge": 0, "counter": 30,
        "description": "Существо из земли и ветвей. Захватывает добычу корнями.",
        "rarity": "epic"
    },

    "Безглазый Житель": {
        "hp": 150, "damage": 20, "dodge": 30, "counter": 10,
        "description": "Когда-то человек. Теперь лишь оболочка, бродящая по деревне.",
        "rarity": "common"
    },
    "Пепельный Пёс": {
        "hp": 70, "damage": 50, "dodge": 30, "counter": 5,
        "description": "Пёс из пепла и криков. Ищет своего хозяина в вечной муке.",
        "rarity": "common"
    },
    "Колоколий": {
        "hp": 200, "damage": 30, "dodge": 5, "counter": 40,
        "description": "Ржавый колокол вместо головы. Его звон парализует страхом.",
        "rarity": "rare"
    },
    "Сломанный Кукловод": {
        "hp": 100, "damage": 20, "dodge": 60, "counter": 0,
        "description": "Мастер марионеток, ставший одной из них.",
        "rarity": "rare"
    },
    "Жнец Молчания": {
        "hp": 500, "damage": 20, "dodge": 0, "counter": 20,
        "description": "Собирает души тех, кто кричал в темноте. Никогда не говорит.",
        "rarity": "epic"
    },
    "Блуждающий Рыцарь": {
        "hp": 150, "damage": 70, "dodge": 10, "counter": 50,
        "description": "Когда-то защитник замка. Теперь лишь тень в броне.",
        "rarity": "common"
    },
    "Призрачная Дева": {
        "hp": 400, "damage": 30, "dodge": 20, "counter": 30,
        "description": "Появляется в тишине. Её плач слышен даже сквозь стены.",
        "rarity": "common"
    },
    "Гаргулья-Караульщица": {
        "hp": 1000, "damage": 10, "dodge": 5, "counter": 5,
        "description": "Каменное чудовище, что охраняет руины. Неустанна и беспощадна.",
        "rarity": "rare"
    },
    "Книжный Ужас": {
        "hp": 500, "damage": 200, "dodge": 0, "counter": 0,
        "description": "Созданный из запретных знаний. Поглощает разум.",
        "rarity": "rare"
    },
    "Старый Ключник": {
        "hp": 2000, "damage": 100, "dodge": 20, "counter": 30,
        "description": "Хранитель замка. Без него двери не открываются... и не закрываются.",
        "rarity": "epic"
    }
}

def roll_drop():
    material_pool = []

    for rarity, materials in DROP.items():
        for name, data in materials.items():
            material_pool.append((name, data["chance"], rarity))

    drop_roll = random.uniform(0, 100)
    cumulative = 0

    for name, chance, rarity in material_pool:
        cumulative += chance
        if drop_roll <= cumulative:
            return name, rarity  # ✅ возвращаем два значения

    return None, None  # ничего не выпало



def get_items_by_slot(slot: str):
    valid_slots = ["head", "body", "gloves", "legs", "feet", "weapon"]
    if slot not in valid_slots:
        raise ValueError(f"Invalid slot name: {slot}")

    slot_items = {
        "head": [],
        "body": [],
        "gloves": [],
        "legs": [],
        "feet": [],
        "weapon": []
    }

    for power_type in SETS.values():
        for set_name, set_data in power_type.items():
            for item in set_data["items"]:
                if slot in item:
                    slot_items[slot].append(item)

    return slot_items[slot]


DROP_CHANCES = {
    "common": {"weak": 0.15, "strong": 0.05},
    "rare": {"weak": 0.20, "strong": 0.10},
    "epic": {"weak": 0.30, "strong": 0.15}
}


def random_strong_item():
    set_name = random.choice(list(SETS["strong"].keys()))
    chosen_set = SETS["strong"][set_name]
    item = random.choice(chosen_set["items"])
    return set_name, item

def random_weak_item():
    set_name = random.choice(list(SETS["weak"].keys()))
    chosen_set = SETS["weak"][set_name]
    item = random.choice(chosen_set["items"])
    return set_name, item

def get_random_monster(location_name: str, location_mobs: list):
    rarity_chances = LOCATIONS.get(location_name, {}).get("rarity_chances", {
        "epic": 10,
        "rare": 30,
        "common": 60
    })

    rarity_pool = {
        "epic": [],
        "rare": [],
        "common": []
    }

    for name in location_mobs:
        monster = MONSTERS.get(name)
        if not monster:
            continue
        rarity = monster.get("rarity", "common")
        monster = monster.copy()
        monster["name"] = name
        rarity_pool[rarity].append(monster)

    rarity = random.choices(
        population=list(rarity_chances.keys()),
        weights=list(rarity_chances.values()),
        k=1
    )[0]

    pool = rarity_pool.get(rarity, rarity_pool["common"])
    return random.choice(pool)

allowed_locations = set(locations.keys())

def get_locations_text(user_id):
    text = "Выберите локацию для пина:\n\n"

    try:
        response = supabase.table("clan_battle") \
            .select("pin") \
            .eq("user_id", user_id) \
            .limit(1) \
            .execute()

        data = response.data or []

        if data and data[0].get("pin"):
            pin_location = data[0]["pin"]
            text += f"📍 Ваш пин: {pin_location}\n\n"
        else:
            text += "📍 Ваш пин: отсутствует\n\n"

    except Exception as e:
        print(f"❌ Ошибка при получении пина игрока: {e}")
        text += "📍 Ваш пин: ошибка при получении\n\n"

    # Добавляем описание локаций
    for name, desc in locations.items():
        text += f"{name}\n{desc}\n\n"

    # Добавляем информацию о клановой войне
    text += "⚔️ Клановая война (КВ) проводится каждый день в 19:00. Будьте готовы!\n"

    return text




def get_locations_inline_kb() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(text=name, callback_data=f"loc_{name}")]
        for name in locations.keys()
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def build_pvp_message(my, opponent):
    return (
        f"🛡️ Противник найден!\n\n"
        f"👤 <b>{opponent['username']}</b>\n"
        f"❤️ Здоровье: {opponent['health']}\n"
        f"💥 Урон: {opponent['attack']}\n"
        f"🌀 Уклонение: {opponent.get('dodge', 0)}%\n"
        f"🎯 Крит: {opponent.get('crit', 0)}%\n"
        f"🔁 Контратака: {opponent.get('counter_attack', 0)}%\n\n"
        f"Выберите действие:"
    )


def get_pvp_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🗡️ Ударить", callback_data="pvp_attack"),
            InlineKeyboardButton(text="⏭️ Пропустить", callback_data="pvp_skip")
        ],
        [
            InlineKeyboardButton(text="❌ Уйти с арены", callback_data="pvp_cancel")
        ]
    ])


async def craft_item(user_id: int, item_name: str, needed_materials: dict, supabase):
    # 1. Проверяем, хватает ли материалов
    for material_name, required_count in needed_materials.items():
        materials_resp = supabase.table("materials")\
            .select("count")\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()
        if not materials_resp.data or materials_resp.data[0]["count"] < required_count:
            return f"❌ Недостаточно материала: {material_name}"

    # 2. Списываем материалы
    for material_name, required_count in needed_materials.items():
        materials_resp = supabase.table("materials")\
            .select("count")\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()
        current_count = materials_resp.data[0]["count"]
        supabase.table("materials")\
            .update({"count": current_count - required_count})\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()

    # 3. Добавляем или обновляем предмет в рюкзаке
    existing = supabase.table("backpack")\
        .select("count")\
        .eq("user_id", user_id)\
        .eq("item_name", item_name)\
        .execute()

    if existing.data:
        current_count = existing.data[0]["count"]
        supabase.table("backpack")\
            .update({"count": current_count + 1})\
            .eq("user_id", user_id)\
            .eq("item_name", item_name)\
            .execute()
    else:
        supabase.table("backpack")\
            .insert({"user_id": user_id, "item_name": item_name, "count": 1})\
            .execute()

    return f"✅ Вы успешно скрафтили предмет: {item_name}"

# ---------- Clan selection ----------
def get_user_backpack(user_id: int, supabase: Client):
    response = supabase.table("backpack").select("*").eq("user_id", user_id).execute()
    return response.data if response.data else []


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

@dp.message(lambda message: message.text == "🔍 Начать поиск противника")
async def start_pvp_search(message: Message):
    user_id = str(message.from_user.id)

    # Проверка: не участвует ли уже в PVP
    existing_status = supabase.table("adventure_status").select("*").eq("user_id", user_id).execute()
    if existing_status.data:
        status = existing_status.data[0]
        if status.get("pvp") is True:
            await message.answer("⚔️ Вы уже на арене.")
            return
        else:
            await message.answer("❗ Вы не можете начать PvP сейчас.")
            return

    # Получаем характеристики и имя пользователя
    user_response = supabase.table("users").select("username, health, attack, dodge, crit, counter_attack").eq("user_id", user_id).execute()

    if not user_response.data:
        await message.answer("⚠️ Не удалось получить ваши характеристики.")
        return

    user_data = user_response.data[0]
    username = user_data["username"]

    # Ищем соперника
    opponent_search = supabase.table("adventure_status") \
        .select("user_id") \
        .eq("pvp", True) \
        .is_("opponent_id", None) \
        .neq("user_id", user_id) \
        .limit(1).execute()

    if opponent_search.data:
        opponent_id = opponent_search.data[0]["user_id"]

        # Обновляем обоих игроков — создаем бой
        for uid, opp_id in [(user_id, opponent_id), (opponent_id, user_id)]:
            player_data = supabase.table("users").select("username, health, attack, dodge, crit, counter_attack").eq("user_id", uid).execute().data[0]

            supabase.table("adventure_status").upsert({
                "user_id": uid,
                "username": player_data["username"],
                "pvp": True,
                "opponent_id": opp_id,
                "pvp_turn": 0,
                "last_action": None,
                "health": player_data["health"],
                "attack": player_data["attack"],
                "dodge": player_data["dodge"],
                "crit": player_data["crit"],
                "counter_attack": player_data["counter_attack"]
            }).execute()

        # Получаем полную информацию о игроках
        user_info = supabase.table("users").select("username, health, attack, dodge, crit, counter_attack").eq("user_id", user_id).execute().data[0]
        opp_info = supabase.table("users").select("username, health, attack, dodge, crit, counter_attack").eq("user_id", opponent_id).execute().data[0]

        # Кнопки PvP
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🗡️ Ударить", callback_data="pvp_attack"),
                InlineKeyboardButton(text="⏭️ Пропустить", callback_data="pvp_skip")
            ],
            [
                InlineKeyboardButton(text="❌ Уйти с арены", callback_data="pvp_cancel")
            ]
        ])

        await bot.send_message(user_id, build_pvp_message(user_info, opp_info), reply_markup=keyboard)
        await bot.send_message(opponent_id, build_pvp_message(opp_info, user_info), reply_markup=keyboard)

    else:
        # Никого не найдено — добавляем в очередь
        supabase.table("adventure_status").upsert({
            "user_id": user_id,
            "username": username,
            "pvp": True,
            "opponent_id": None,
            "pvp_turn": 0,
            "last_action": None,
            "health": user_data["health"],
            "attack": user_data["attack"],
            "dodge": user_data["dodge"],
            "crit": user_data["crit"],
            "counter_attack": user_data["counter_attack"]
        }).execute()

        await message.answer(
            "🔍 Вы начали поиск противника. Ожидание соперника...",
            reply_markup=cancel_search_kb
        )

async def handle_adventure(user_id: int, location_name: str, monster: dict, duration: int):
    await asyncio.sleep(duration)

    # Проверка премиума
    premium_resp = supabase.table("users").select("premium_until").eq("user_id", user_id).execute()
    premium_until_str = premium_resp.data[0].get("premium_until") if premium_resp.data else None
    premium_active = False

    if premium_until_str:
        premium_until = datetime.fromisoformat(premium_until_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        if premium_until > now:
            premium_active = True

    # Получаем локацию
    location = LOCATIONS.get(location_name)
    base_exp = random.randint(*location["exp"])
    base_money = random.randint(*location["money"])
    bonus_exp = int(base_exp * 0.3) if premium_active else 0
    bonus_money = int(base_money * 0.5) if premium_active else 0
    total_exp = base_exp + bonus_exp
    total_money = base_money + bonus_money

    # Обновление баланса и опыта
    user_data = supabase.table("users").select("money").eq("user_id", user_id).execute()
    current_money = user_data.data[0]["money"] if user_data.data else 0

    await add_experience(user_id, total_exp)

    supabase.table("users").update({
        "money": current_money + total_money
    }).eq("user_id", user_id).execute()

    # Удаление статуса приключения
    supabase.table("adventure_status").delete().eq("user_id", user_id).execute()

    # Дроп логика
    rarity_key = monster["rarity"].lower()
    drop_chances = DROP_CHANCES.get(rarity_key, {"weak": 0.10, "strong": 0.02})
    drop_roll = random.random()
    item_dropped = None

    if drop_roll < drop_chances["weak"]:
        set_name, item = random_weak_item()
        item_dropped = item
        rarity_type = "слабый"
    elif drop_roll < drop_chances["weak"] + drop_chances["strong"]:
        set_name, item = random_strong_item()
        item_dropped = item
        rarity_type = "сильный"

    if item_dropped:
        item_name = item_dropped["name"]
        await bot.send_message(
            user_id,
            f"🎉 Тебе выпал {rarity_type} предмет из сета <b>{set_name}</b>:\n"
            f"🧩 <b>{item_name}</b>"
        )
        existing = supabase.table("backpack").select("count").eq("user_id", user_id).eq("item_name", item_name).execute()
        if existing.data:
            current_count = existing.data[0]["count"]
            supabase.table("backpack").update({
                "count": current_count + 1
            }).eq("user_id", user_id).eq("item_name", item_name).execute()
        else:
            supabase.table("backpack").insert({
                "user_id": user_id,
                "item_name": item_name,
                "count": 1
            }).execute()
    else:
        material_name, material_rarity = roll_drop()
        if material_name:
            await bot.send_message(
                user_id,
                f"🪵 Ты нашёл ресурс:\n"
                f"🔹 <b>{material_name}</b>"
            )

            existing = supabase.table("materials").select("count").eq("user_id", user_id).eq("material_name", material_name).execute()
            if existing.data:
                current_count = existing.data[0]["count"]
                supabase.table("materials").update({
                    "count": current_count + 1
                }).eq("user_id", user_id).eq("material_name", material_name).execute()
            else:
                supabase.table("materials").insert({
                    "user_id": user_id,
                    "material_name": material_name,
                    "count": 1
                }).execute()

    # Финальное сообщение
    exp_text = f"{base_exp}+{bonus_exp}({total_exp})" if premium_active else str(base_exp)
    money_text = f"{base_money}+{bonus_money}({total_money})" if premium_active else str(base_money)

    await bot.send_message(
        user_id,
        f"✅ <b>Приключение завершено!</b>\n\n"
        f"🏞️ Локация: <b>{location_name}</b>\n"
        f"⚔️ Побежденный враг: <b>{monster['name']}</b>\n\n"
        f"🎖 Получено опыта: <b>{exp_text}</b>\n"
        f"💰 Получено монет: <b>{money_text}</b>",
        reply_markup=main_menu_kb
    )

@dp.message(lambda message: message.text == "🔨 Крафт")
async def handle_craft(message: types.Message):
    crafter_sets = SETS.get("crafter", {})

    if not crafter_sets:
        await message.answer("⚠️ Нет доступных сетов для крафта.")
        return

    # Создание клавиатуры с сетами
    keyboard = [
        [InlineKeyboardButton(text=set_name, callback_data=f"craft_set:{set_name}")]
        for set_name in crafter_sets.keys()
    ]

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await message.answer("🛠 Что вы хотите скрафтить?", reply_markup=markup)

@dp.message(lambda message: message.text == "📊 Результаты битвы")
async def send_battle_results(message: Message):
    try:
        allowed_locations = {
            "🏰 Проклятая Цитадель",
            "🌋 Утроба Вулкана",
            "🕸️ Паутина Забвения",
            "👁️ Обитель Иллюзий"
        }

        # Получаем данные из таблицы clancv
        clancv_table = supabase.table("clancv").select("*").execute()
        clancv_rows = clancv_table.data or []

        result_lines = []

        for location in allowed_locations:
            controlling_clan = None

            for row in clancv_rows:
                if row.get(location) == True:
                    controlling_clan = row["clan_name"]
                    break

            if controlling_clan:
                result_lines.append(f"{location} — под контролем клана *{controlling_clan}*")
            else:
                result_lines.append(f"{location} — под контролем монстров")

        result_text = "\n".join(result_lines)

        await message.answer(
            text=f"📊 *Результаты клановой битвы:*\n\n{result_text}",
            parse_mode="Markdown"
        )

    except Exception as e:
        print(f"❌ Ошибка при выводе результатов: {e}")
        await message.answer("❌ Ошибка при получении результатов битвы.")



@dp.message(lambda message: message.text in ["🪖 Голова", "👕 Тело", "🧤 Руки", "👖 Ноги", "👟 Ступни", "🗡️ Оружие"])
async def show_items(message: types.Message):
    category = None
    if message.text == "🪖 Голова":
        category = "head"
    elif message.text == "👕 Тело":
        category = "body"
    elif message.text == "🧤 Руки":
        category = "gloves"
    elif message.text == "👖 Ноги":
        category = "legs"
    elif message.text == "👟 Ступни":
        category = "feet"
    elif message.text == "🗡️ Оружие":
        category = "weapon"

    # Створюємо інлайн клавіатуру для вибраної категорії
    keyboard = await create_inline_keyboard_from_backpack(message.from_user.id, category)

    if keyboard:
        await message.answer(f"Выберите предмет для {message.text.lower()}: ", reply_markup=keyboard)
    else:
        await message.answer(f"У вас нет предметов в рюкзаке для категории {message.text.lower()}.")


@dp.message(lambda message: message.text in ["❌ Голова", "❌ Тело", "❌ Руки", "❌ Ноги", "❌ Ступни", "❌ Оружие"])
async def unequip_item(message: types.Message):
    user_id = message.from_user.id

    # Определение категории
    category_map = {
        "❌ Голова": "head",
        "❌ Тело": "body",
        "❌ Руки": "gloves",
        "❌ Ноги": "legs",
        "❌ Ступни": "feet",
        "❌ Оружие": "weapon"
    }
    category = category_map[message.text]

    # Получаем данные пользователя
    user_data = supabase.table("users").select("*").eq("user_id", user_id).single().execute()
    if not user_data.data:
        await message.answer("❗ Пользователь не найден.")
        return

    equipped_item = user_data.data.get(category)

    if not equipped_item or equipped_item == "нет":
        await message.answer("⚠️ В этой категории ничего не надето.")
        return

    # Получаем бонусы предмета
    hp_bonus, damage_bonus = get_item_stats(equipped_item)

    # Обновляем экипировку и характеристики
    new_health = max(0, user_data.data.get("health", 0) - hp_bonus)
    new_attack = max(0, user_data.data.get("attack", 0) - damage_bonus)

    supabase.table("users").update({
        category: "нет",
        "health": new_health,
        "attack": new_attack
    }).eq("user_id", user_id).execute()

    # Обновляем/добавляем в рюкзак
    backpack_response = supabase.table("backpack").select("count")\
        .eq("user_id", user_id).eq("item_name", equipped_item).execute()

    backpack_data = backpack_response.data[0] if backpack_response.data else None

    if backpack_data:
        new_count = backpack_data["count"] + 1
        supabase.table("backpack").update({"count": new_count})\
            .eq("user_id", user_id).eq("item_name", equipped_item).execute()
    else:
        supabase.table("backpack").insert({
            "user_id": user_id,
            "item_name": equipped_item,
            "count": 1
        }).execute()

    await message.answer(f"❌ Снято: <b>{equipped_item}</b>")



@dp.message(lambda message: message.text == "📌 Сделать пин")
async def send_pin_menu(message: types.Message):
    user_id = message.from_user.id
    text = get_locations_text(user_id)
    kb = get_locations_inline_kb()
    await message.answer(text, reply_markup=kb)


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


    async def start_adventure(message: types.Message, location_name: str):
        location = LOCATIONS.get(location_name)
        adventure = ADVENTURES.get(location_name)

        if not location or not adventure:
            await message.answer("❗ Приключение не найдено.")
            return

        duration = location["duration"]
        user_id = message.from_user.id

        # Випадковий монстр з урахуванням рідкості
        monster = get_random_monster(adventure['mobs'])

        name = monster["name"]
        hp = monster["hp"]
        dmg = monster["damage"]
        dodge = monster["dodge"]
        counter = monster["counter"]
        desc = monster["description"]
        rarity = monster["rarity"].capitalize()

        # Повідомлення про початок пригоди та зустріч з монстром
        await message.answer(
            f"🏃‍♂️ Ты отправился в <b>{location_name}</b>\n\n"
            f"👾 <b>Вы встретили монстра: {name}</b>\n"
            f"📖 <i>{desc}</i>\n"
            f"🏷 Редкость: <b>{rarity}</b>\n\n"
            f"❤️ Здоровье: <b>{hp}</b>\n"
            f"💥 Урон: <b>{dmg}</b>\n"
            f"🌀 Уклонение: <b>{dodge}%</b>\n"
            f"🔁 Контратака: <b>{counter}%</b>\n\n"
            f"⏳ Приключение продлится <b>{duration}</b> секунд..."
        )

        # Очікуємо завершення
        await asyncio.sleep(duration)

    # Генеруємо нагороду
    exp = random.randint(*location["exp"])
    money = random.randint(*location["money"])

    # Отримуємо гроші користувача
    user_resp = supabase.table("users").select("money").eq("user_id", user_id).execute()
    current_money = user_resp.data[0]["money"] if user_resp.data else 0

    # Оновлюємо досвід та гроші
    await add_experience(user_id, exp)
    supabase.table("users").update({
        "money": current_money + money
    }).eq("user_id", user_id).execute()

    # Підсумок
    await bot.send_message(
        user_id,
        f"✅ <b>Приключение завершено!</b>\n\n"
        f"🏞️ Локация: <b>{location_name}</b>\n"
        f"⚔️ Побежден враг: <b>{name}</b>\n\n"
        f"🎖 Получено опыта: <b>{exp}</b>\n"
        f"💰 Найдено монет: <b>{money}</b>",
        reply_markup=main_menu_kb
    )


# ---------- Обработка сообщений ----------

@dp.message()
async def handle_messages(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    # Проверка на ожидание ввода никнейма
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


    # Основной блок обработки сообщений

    if text == "👤 Профиль":
        response = supabase.table("users").select("*").eq("user_id", user_id).execute()
        row = response.data[0] if response.data else None

        if row:
            clan_desc = CLANS.get(row.get("clan", ""), "")

            # Проверка и форматирование премиума
            premium_status = "Не активен"
            premium_remaining = ""

            premium_until_str = row.get("premium_until")
            if premium_until_str:
                premium_until = datetime.fromisoformat(premium_until_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)
                if premium_until > now:
                    premium_status = "✅ Активен"
                    remaining = premium_until - now
                    days = remaining.days
                    hours = remaining.seconds // 3600
                    premium_remaining = f"\nОсталось: {days} д. {hours} ч."
                else:
                    premium_status = "❌ Не активен"

            profile_text = (
                f"<b>{row['username']}</b> | <code>{user_id}</code>\n"
                f"Статус аккаунта: {row['status']}\n"
                f"Премиум статус: {premium_status}{premium_remaining}\n\n"
                f"🌟 Уровень: {row['level']}\n"
                f"Опыт: {row['exp']} / {row['exp_max']}\n"
                f"Очки прокачки: {row.get('level_points', 0)}\n"
                f"❤️ {row['health']} | 🗡 {row['attack']}\n"
                f"🌀 Уклонение: {row.get('dodge', 0)}%\n"
                f"🎯 Крит: {row.get('crit', 0)}%\n"
                f"🔁 Контратака: {row.get('counter_attack', 0)}%\n\n"
                f"💰 Деньги: {row['money']} | 💎 Алмазы: {row['diamonds']}\n\n"
                f"🥋 Экипировка:\n"
                f"Голова: {row['head']}\n"
                f"Тело: {row['body']}\n"
                f"Перчатки: {row.get('gloves')}\n"
                f"Ноги: {row['legs']}\n"
                f"Ступни: {row['feet']}\n"
                f"Оружие: {row['weapon']}\n"
                f"💪 Клан: {row.get('clan', 'нет')}"
            )

            await message.answer(profile_text, reply_markup=profile_kb)
        else:
            waiting_for_nick.add(user_id)
            await message.answer("Никнейм не найден. Введите свой никнейм.")

    elif text == "🎒 Рюкзак":
        await message.answer("🎒 Выберите слот:", reply_markup=backpack_keyboard)


    elif text == "⚔️ Надеть":
        # Показываем клавиатуру для выбора части тела
        await message.answer("Выберите, что надеть:", reply_markup=equip_kb)
    elif text == "❌ Снять":
        # Показываем клавиатуру для выбора части тела
        await message.answer("Выберите, что надеть:", reply_markup=unequip_kb)


    elif text == "⬅️ Назад":
        # Возвращаем в рюкзак
        await message.answer("Ваши вещи в рюкзаке:", reply_markup=profile_kb)


    elif text == "⚙️ Прокачка":
        upgrade_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❤️ Здоровье"), KeyboardButton(text="🗡️ Урон")],
                [KeyboardButton(text="🌀 Уклонение"), KeyboardButton(text="🎯 Крит"),
                 KeyboardButton(text="🔁 Контратака")],
                [KeyboardButton(text="⬅️ Назад ")]
            ],
            resize_keyboard=True
        )

        await message.answer("Выберите, что прокачать:", reply_markup=upgrade_kb)
    elif text in ("❤️ Здоровье", "🗡️ Урон", "🌀 Уклонение", "🎯 Крит", "🔁 Контратака"):
        resp = supabase.table("users").select("level_points", "health", "attack", "dodge", "crit", "counter_attack").eq(
            "user_id", user_id).execute()
        if not resp.data:
            return
        user = resp.data[0]
        points = user["level_points"]
        if points <= 0:
            await message.answer("❗ У вас нет очков прокачки.", reply_markup=profile_kb)
            return

        new_points = points - 1
        updates = {"level_points": new_points}
        msg = ""

        if text == "❤️ Здоровье":
            updates["health"] = user["health"] + 10
            msg = "❤️ <b>Здоровье +10!</b>\nВы стали крепче и выносливее."
        elif text == "🗡️ Урон":
            updates["attack"] = user["attack"] + 10
            msg = "🗡️ <b>Атака +10!</b>\nТвоя сила увеличилась!"
        elif text == "🌀 Уклонение":
            if user["dodge"] >= 20:
                await message.answer("❗ Уклонение уже на максимуме (20%).")
                return
            updates["dodge"] = min(user["dodge"] + 2, 20)
            msg = f"🌀 <b>Уклонение +2%</b>\nТеперь вы уворачиваетесь чаще!"
        elif text == "🎯 Крит":
            if user["crit"] >= 30:
                await message.answer("❗ Крит уже на максимуме (30%).")
                return
            updates["crit"] = min(user["crit"] + 2, 30)
            msg = f"🎯 <b>Крит +2%</b>\nТы стал наносить больше критических ударов!"
        elif text == "🔁 Контратака":
            if user["counter_attack"] >= 20:
                await message.answer("❗ Контратака уже на максимуме (20%).")
                return
            updates["counter_attack"] = min(user["counter_attack"] + 2, 20)
            msg = f"🔁 <b>Контратака +2%</b>\nТы научился отвечать на удары противника!"

        supabase.table("users").update(updates).eq("user_id", user_id).execute()

        updated = supabase.table("users").select("level_points", "health", "attack", "dodge", "crit",
                                                 "counter_attack").eq("user_id", user_id).execute()
        new_user = updated.data[0]

        await message.answer(f"{msg}\n\n"
                             f"🧬 <b>Текущие характеристики:</b>\n"
                             f"❤️ Здоровье: <b>{new_user['health']}</b>\n"
                             f"🗡️ Урон: <b>{new_user['attack']}</b>\n"
                             f"🌀 Уклонение: <b>{new_user['dodge']}%</b>\n"
                             f"🎯 Крит: <b>{new_user['crit']}%</b>\n"
                             f"🔁 Контратака: <b>{new_user['counter_attack']}%</b>\n"
                             f"🎯 Очки прокачки: <b>{new_user['level_points']}</b>")

    elif text == "⬅️Назад":
        await message.answer("Главное меню:", reply_markup=profile_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    elif text == "⚔️ Арена":
        await message.answer("Добро пожаловать на арену! Выберите действие:", reply_markup=arena_kb)



    elif text == "🗺️ Приключения":
        locations_info = ""
        for name, data in LOCATIONS.items():
            if name not in ADVENTURES:
                continue
            exp_range = f"{data['exp'][0]}–{data['exp'][1]}"
            money_range = f"{data['money'][0]}–{data['money'][1]}"
            duration = data["duration"]
            min_level = data.get("min_level", 1)
            locations_info += (
                f"📍 <b>{name}</b>\n"
                f"{ADVENTURES[name]['description']}\n"
                f"🔒 Требуемый уровень: <b>{min_level}</b>\n"
                f"🎖 Опыт: <b>{exp_range}</b> | 💰 Монеты: <b>{money_range}</b> | ⏱ Время: {duration} сек.\n\n"
            )

        buttons = [
            [InlineKeyboardButton(text=name, callback_data=f"preview_{name}")]
            for name in LOCATIONS.keys() if name in ADVENTURES
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await message.answer(f"🌍 <b>Приключения:</b>\n\n{locations_info}", reply_markup=keyboard)

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
            await message.answer(f"💪 Клан: <b>{clan}</b>\n\n{clan_desc}\n\n👥 Участники:\n{members_list}",
                                 reply_markup=main_menu_kb)
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
        await message.answer(f"🌟 <b>Топ по уровню:</b>\n\n{players_list}\n\n📍Твое место: {place}",
                             reply_markup=top_menu_kb)

    elif text == "💰 Топ по деньгам":
        response = supabase.table("users").select("user_id, username, money").order("money", desc=True).execute()
        players = response.data or []
        top_10 = players[:10]
        players_list = "\n".join(f"{i + 1}. {p['username']} 💰 {p['money']}" for i, p in enumerate(top_10))
        place = next((i + 1 for i, p in enumerate(players) if p["user_id"] == user_id), None)
        await message.answer(f"💰 <b>Топ по деньгам:</b>\n\n{players_list}\n\n📍Твое место: {place}",
                             reply_markup=top_menu_kb)


    elif text == "⚔️ Топ по PvP победам":
        response = supabase.table("users").select("user_id, username, pvp_win").order("pvp_win", desc=True).execute()
        players = response.data or []

        filtered_players = [p for p in players if p.get("pvp_win") and p["pvp_win"] > 0]
        top_10 = filtered_players[:10]
        players_list = "\n".join(f"{i + 1}. {p['username']} ⚔️ {p['pvp_win']}" for i, p in enumerate(top_10))
        place = next((i + 1 for i, p in enumerate(filtered_players) if p["user_id"] == user_id), None)
        await message.answer(
            f"⚔️ <b>Топ по PvP победам:</b>\n\n{players_list}\n\n📍Твое место: {place if place else '—'}",
            reply_markup=top_menu_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    elif text == "⚒️ Кузница":
        await message.answer("Выберите действие:", reply_markup=forge_menu_kb)

    elif text in ("⚔️ Заточка"):
        await message.answer("⚙️ В разработке...", reply_markup=forge_menu_kb)



    elif text == "🛍️ Торговля":
        await message.answer("Выберите раздел торговли:", reply_markup=trade_menu_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    elif text == "🛒 Магазин":
        await message.answer("🛒 Открываю магазин...")


    elif text == "💎 Донат Магазин":
        await message.answer("💎 Донат-магазин:\nВыберите категорию:", reply_markup=donate_shop_kb)


    elif text == "👑 Премиум":
        premium_text = (
            "👑 *Премиум-аккаунт*\n\n"
            "💎 Стоимость: 100 алмазов\n"
            "🕘 Длительность: 7 дней\n"
            "📈 +30% опыта\n"
            "💰 +50% денег\n"
            "🍀 +10% удачи\n\n"
            "Получите преимущества уже сейчас!"
        )
        buy_premium_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Купить Премиум", callback_data="buy_premium")]
            ]
        )
        await message.answer(premium_text, reply_markup=buy_premium_kb, parse_mode="Markdown")

    elif text == "💎 Алмазы":
        diamonds_text = (
            "💎 *Покупка алмазов*\n\n"
            "💰 Стоимость: 5,000 денег\n"
            "📦 Количество: 100 алмазов\n\n"
            "Нажмите кнопку ниже, чтобы купить."
        )
        buy_diamonds_kb = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text="💳 Купить 100 алмазов", callback_data="buy_diamonds")]
            ]
        )
        await message.answer(diamonds_text, reply_markup=buy_diamonds_kb, parse_mode="Markdown")

        await message.answer(premium_text, reply_markup=buy_premium_kb, parse_mode="Markdown")

    elif text == "⬅️ Назад (торговля)":
        await message.answer("Возвращаемся в раздел 'Торговля':", reply_markup=trade_menu_kb)

    elif text == "🏪 Рынок":
        await message.answer("🏪 Добро пожаловать на рынок! Выберите действие:", reply_markup=market_menu_kb)


    elif text == "🛡️ Клановая битва":
        await message.answer("Выберите действие:", reply_markup=clan_battle_kb)


@dp.callback_query(lambda c: c.data.startswith("remove_lot_"))
async def handle_remove_lot(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    lot_id = int(callback_query.data.split("_")[-1])

    # Проверяем лот
    result = supabase.table("rynok") \
        .select("*") \
        .eq("id", lot_id) \
        .limit(1) \
        .execute()

    if not result.data:
        await callback_query.answer("❗ Лот не найден.", show_alert=True)
        return

    lot = result.data[0]
    if lot["user_id"] != user_id:
        await callback_query.answer("❗ Это не ваш лот.", show_alert=True)
        return

    item_name = lot["item_name"]

    # Возвращаем предмет в рюкзак
    backpack = supabase.table("backpack") \
        .select("count") \
        .eq("user_id", user_id) \
        .eq("item_name", item_name) \
        .limit(1) \
        .execute()

    if backpack.data:
        current_count = backpack.data[0]["count"]
        supabase.table("backpack") \
            .update({"count": current_count + 1}) \
            .eq("user_id", user_id) \
            .eq("item_name", item_name) \
            .execute()
    else:
        supabase.table("backpack").insert({
            "user_id": user_id,
            "item_name": item_name,
            "count": 1
        }).execute()

    # Удаляем лот с рынка
    supabase.table("rynok") \
        .delete() \
        .eq("id", lot_id) \
        .execute()

    await callback_query.message.edit_text(
        f"✅ Лот <b>{item_name}</b> удалён и возвращён в рюкзак.",
        parse_mode="HTML"
    )
@dp.callback_query(lambda c: c.data == "buy_diamonds")
async def buy_diamonds_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    result = supabase.table("users").select("*").eq("user_id", user_id).single().execute()
    user = result.data

    if not user:
        await callback_query.message.edit_text("❌ Пользователь не найден в базе данных.")
        return

    money = user.get("money", 0)

    if money < 5000:
        await callback_query.message.edit_text("❌ Недостаточно денег для покупки алмазов.")
        return

    diamonds = user.get("diamonds", 0)

    # Обновляем пользователя в базе
    supabase.table("users").update({
        "money": money - 5000,
        "diamonds": diamonds + 100
    }).eq("user_id", user_id).execute()

    await callback_query.message.edit_text("✅ Вы успешно приобрели 100 алмазов за 5,000 денег.")


@dp.callback_query(lambda c: c.data == "buy_premium")
async def buy_premium_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    result = supabase.table("users").select("*").eq("user_id", user_id).single().execute()
    user = result.data

    if not user:
        await callback_query.message.edit_text("❌ Пользователь не найден в базе данных.")
        return

    diamonds = user.get("diamonds", 0)

    if diamonds < 100:
        await callback_query.message.edit_text("❌ Недостаточно средств для покупки премиума.")
        return

    now = datetime.now(timezone.utc)
    premium_until_str = user.get("premium_until")
    premium_until = None

    if premium_until_str:
        try:
            premium_until = datetime.fromisoformat(premium_until_str.replace("Z", "+00:00"))
        except Exception:
            premium_until = None

    if premium_until and premium_until > now:
        # Продлеваем премиум на 7 дней с текущей даты premium_until
        new_premium_until = premium_until + timedelta(days=7)
        message_text = "✅ К вашему сроку добавлено 7 дней премиума!"
    else:
        # Активируем премиум на 7 дней с текущего времени
        new_premium_until = now + timedelta(days=7)
        message_text = "🎉 Премиум успешно активирован на 7 дней!"

    # Форматируем дату в ISO с 'Z'
    new_premium_until_iso = new_premium_until.isoformat(timespec='seconds').replace('+00:00', 'Z')

    # Обновляем пользователя в базе
    supabase.table("users").update({
        "diamonds": diamonds - 100,
        "premium": True,
        "premium_until": new_premium_until_iso
    }).eq("user_id", user_id).execute()

    await callback_query.message.edit_text(message_text)



@dp.callback_query(lambda c: c.data.startswith("user_lots_page_"))
async def paginate_user_lots(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split("_")[-1])
    await show_user_lots(callback_query, page)


@dp.callback_query(lambda c: c.data.startswith("buy_"))
async def handle_buy(callback_query: types.CallbackQuery):
    buyer_id = callback_query.from_user.id
    lot_id = int(callback_query.data.split("_")[1])

    # 1. Получаем лот из рынка
    result = supabase.table("rynok") \
        .select("*") \
        .eq("id", lot_id) \
        .limit(1) \
        .execute()

    if not result.data:
        await callback_query.answer("❗ Лот не найден.", show_alert=True)
        return

    lot = result.data[0]
    item_name = lot["item_name"]
    cost = lot["cost"]
    seller_id = lot["user_id"]

    if seller_id == buyer_id:
        await callback_query.answer("❗ Нельзя покупать свой лот.", show_alert=True)
        return

    # 2. Получаем покупателя
    buyer_data = supabase.table("users") \
        .select("money") \
        .eq("user_id", buyer_id) \
        .limit(1) \
        .execute()

    if not buyer_data.data:
        await callback_query.answer("❗ Вы не зарегистрированы.", show_alert=True)
        return

    buyer_money = buyer_data.data[0]["money"]

    if buyer_money < cost:
        await callback_query.answer("❗ Недостаточно монет.", show_alert=True)
        return

    # 3. Списываем монеты у покупателя
    supabase.table("users") \
        .update({"money": buyer_money - cost}) \
        .eq("user_id", buyer_id) \
        .execute()

    # 4. Добавляем предмет покупателю в backpack
    backpack_check = supabase.table("backpack") \
        .select("count") \
        .eq("user_id", buyer_id) \
        .eq("item_name", item_name) \
        .limit(1) \
        .execute()

    if backpack_check.data:
        current_count = backpack_check.data[0]["count"]
        supabase.table("backpack") \
            .update({"count": current_count + 1}) \
            .eq("user_id", buyer_id) \
            .eq("item_name", item_name) \
            .execute()
    else:
        supabase.table("backpack").insert({
            "user_id": buyer_id,
            "item_name": item_name,
            "count": 1
        }).execute()

    # 5. Добавляем деньги продавцу
    seller_data = supabase.table("users") \
        .select("money") \
        .eq("user_id", seller_id) \
        .limit(1) \
        .execute()

    if seller_data.data:
        seller_money = seller_data.data[0]["money"]
        supabase.table("users") \
            .update({"money": seller_money + cost}) \
            .eq("user_id", seller_id) \
            .execute()

    # 6. Удаляем лот с рынка
    supabase.table("rynok") \
        .delete() \
        .eq("id", lot_id) \
        .execute()

    # 7. Уведомление покупателю
    await callback_query.message.edit_text(
        f"✅ Вы купили <b>{item_name}</b> за <b>{cost}</b> монет.",
        parse_mode="HTML"
    )

    # 8. Уведомление продавцу
    try:
        await bot.send_message(
            seller_id,
            f"💰 Ваш лот <b>{item_name}</b> был куплен за <b>{cost}</b> монет!",
            parse_mode="HTML"
        )
    except:
        pass

@dp.callback_query(lambda c: c.data.startswith("market_page_"))
async def handle_market_pagination(callback_query: types.CallbackQuery):
    page = int(callback_query.data.split("_")[-1])
    await callback_query.message.delete()  # Удалить старое сообщение
    await show_market(callback_query.message, page=page)
    await callback_query.answer()


@dp.callback_query(lambda c: c.data.startswith("page:"))
async def handle_pagination(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    page = int(callback_query.data.split(":")[1])

    keyboard = await create_paginated_inline_keyboard(user_id, items, supabase, page=page)

    if keyboard:
        await callback_query.message.edit_reply_markup(reply_markup=keyboard)
    else:
        await callback_query.answer("Ошибка загрузки страницы.")

@dp.callback_query(F.data.startswith("slot_"))
async def handle_slot(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    slot = callback.data.replace("slot_", "")  # "head", "body", ...

    items = get_user_backpack(user_id, supabase)  # Ваша функция для получения предметов из таблицы backpack
    user_items = {item["item_name"]: item["count"] for item in items}

    slot_items = get_items_by_slot(slot)  # Ваша функция, возвращающая список предметов для слота

    slot_title = {
        "head": "🪖 Голова",
        "body": "👕 Тело",
        "gloves": "🧤 Руки",
        "legs": "👖 Ноги",
        "feet": "🥾 Ступни",
        "weapon": "🗡 Оружие"
    }.get(slot, "Слот")

    message_lines = [f"<b>{slot_title} — ваши предметы:</b>\n"]

    found = False

    for item in slot_items:
        name = item["name"]
        if name in user_items:
            count = user_items[name]
            hp = item.get("hp", 0)
            dmg = item.get("damage", 0)
            found = True
            message_lines.append(
                f"🔹 <b>{name}</b>\n"
                f"    🩸 HP: <code>{hp}</code>\n"
                f"    ⚔️ Урон: <code>{dmg}</code>\n"
                f"    🎒 Количество: <code>{count}</code>\n"
            )

    if not found:
        message_lines.append("❌ У вас нет предметов в этом слоте.")

    await callback.message.edit_text(
        "\n".join(message_lines),
        parse_mode="HTML",
        reply_markup=backpack_keyboard
    )

# Новый обработчик для ресурсов из таблицы materials
@dp.callback_query(F.data == "view_resources")
async def handle_resources(callback: types.CallbackQuery):
    user_id = callback.from_user.id

    response = supabase.table("materials").select("*").eq("user_id", user_id).execute()
    materials = response.data

    if not materials:
        await callback.message.edit_text("📦 У вас пока нет ресурсов.", reply_markup=backpack_keyboard)
        return

    message_lines = ["<b>📦 Ваши ресурсы:</b>\n"]
    for material in materials:
        name = material["material_name"]
        count = material["count"]
        message_lines.append(f"🔹 <b>{name}</b> — <code>{count}</code> шт.")

    await callback.message.edit_text(
        "\n".join(message_lines),
        parse_mode="HTML",
        reply_markup=backpack_keyboard
    )


@dp.callback_query(lambda c: c.data.startswith("create_lot:"))
async def process_create_lot_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    item_name = callback_query.data.split(":")[1]

    # Зберігаємо очікування ціни
    waiting_for_price.add(user_id)
    lot_creation_data[user_id] = item_name

    await callback_query.message.answer(f"📦 Вы выбрали предмет: <b>{item_name}</b>\n💰 Введите цену (только цифры):", parse_mode="HTML")

@dp.callback_query(lambda c: c.data == "pvp_cancel")
async def leave_pvp(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)

    # Проверяем статус игрока
    status_res = supabase.table("adventure_status") \
        .select("*") \
        .eq("user_id", user_id) \
        .eq("pvp", True) \
        .execute()

    if not status_res.data:
        await callback.answer("❗ Вы сейчас не на арене.", show_alert=True)
        return

    status = status_res.data[0]
    opponent_id = status.get("opponent_id")

    if not opponent_id:
        # Игрок в очереди, боёв нет — просто удаляем статус
        supabase.table("adventure_status").delete().eq("user_id", user_id).execute()
        await callback.message.edit_text("❌ Вы покинули арену. Поиск отменён.")
        return

    # Игрок в бою — начисляем штраф/премию
    try:
        # Получаем данные игроков
        user_record = supabase.table("users").select("money").eq("user_id", user_id).execute().data[0]
        opp_record = supabase.table("users").select("pvp_win, money").eq("user_id", opponent_id).execute().data[0]

        user_money = user_record.get("money") or 0
        opp_money = opp_record.get("money") or 0
        opp_wins = opp_record.get("pvp_win") or 0

        # Обновляем деньги и победы
        new_user_money = max(0, user_money - 100)
        new_opp_money = opp_money + 100
        new_opp_wins = opp_wins + 1

        supabase.table("users").update({
            "money": new_user_money
        }).eq("user_id", user_id).execute()

        supabase.table("users").update({
            "money": new_opp_money,
            "pvp_win": new_opp_wins
        }).eq("user_id", opponent_id).execute()

        # Отправляем сообщения
        await bot.send_message(user_id, "❌ Вы покинули арену. Вы проиграли и потеряли 100💰.")
        await bot.send_message(opponent_id, "🏆 Ваш соперник вышел из боя. Вы победили и получили 100💰!")

    except Exception as e:
        print(f"Ошибка при обновлении баланса и отправке сообщений: {e}")

    # Удаляем статус у обоих игроков
    supabase.table("adventure_status").delete().or_(
        f"user_id.eq.{user_id},user_id.eq.{opponent_id}"
    ).execute()


@dp.callback_query(lambda c: c.data in ["pvp_attack", "pvp_skip"])
async def pvp_action(callback: types.CallbackQuery):
    user_id = str(callback.from_user.id)
    action = callback.data  # "pvp_attack" или "pvp_skip"

    # Получение боевых статусов
    user_status_res = supabase.table("adventure_status").select("*").eq("user_id", user_id).execute()
    if not user_status_res.data:
        await callback.answer("❗ Вы не участвуете в PvP.", show_alert=True)
        return

    user_status = user_status_res.data[0]
    opponent_id = user_status.get("opponent_id")
    if not opponent_id:
        await callback.answer("❗ Противник не найден.", show_alert=True)
        return

    opp_status_res = supabase.table("adventure_status").select("*").eq("user_id", opponent_id).execute()
    if not opp_status_res.data:
        await callback.answer("❗ Противник не найден.", show_alert=True)
        return

    opponent_status = opp_status_res.data[0]

    # Проверка очереди хода
    if user_status["pvp_turn"] > opponent_status["pvp_turn"]:
        await callback.answer("⏳ Ожидайте ход противника.", show_alert=True)
        return

    logs = []

    if action == "pvp_attack":
        attacker_name_res = supabase.table("users").select("username").eq("user_id", user_id).execute()
        defender_name_res = supabase.table("users").select("username").eq("user_id", opponent_id).execute()
        attacker_name = attacker_name_res.data[0]["username"]
        defender_name = defender_name_res.data[0]["username"]

        # Уклонение (dodge) противника
        dodge_chance = opponent_status.get("dodge", 0)
        dodge_roll = random.uniform(0, 100)

        # ... внутри блока if action == "pvp_attack":

        if dodge_roll < dodge_chance:
            # Противник уклонился
            logs.append(f"🌀 {defender_name} уклонился от атаки {attacker_name}! Урон не нанесён.")
            damage = 0
        else:
            crit_chance = user_status.get("crit", 0)
            crit_roll = random.uniform(0, 100)
            base_damage = user_status["attack"]
            crit_multiplier = 1.2

            if crit_roll < crit_chance:
                damage = int(base_damage * crit_multiplier)
                logs.append(f"🔥 {attacker_name} наносит критический удар! Урон: {damage}")
            else:
                damage = base_damage
                logs.append(f"🗡️ {attacker_name} наносит обычный удар. Урон: {damage}")

        opp_hp_before = opponent_status["health"]
        new_opp_hp = max(0, opp_hp_before - damage)

        # Контратака — половина урона, который нанес атакующий
        counter_attack = opponent_status.get("counter_attack", 0)

        if counter_attack > 0 and new_opp_hp > 0 and damage > 0:
            counter_damage = damage // 2
            attacker_hp_before = user_status["health"]
            new_attacker_hp = max(0, attacker_hp_before - counter_damage)
            supabase.table("adventure_status").update({
                "health": new_attacker_hp
            }).eq("user_id", user_id).execute()
            logs.append(f"🛡️ {defender_name} контратакует и наносит {counter_damage} урона {attacker_name}.")

        # Обновляем здоровье противника
        supabase.table("adventure_status").update({
            "health": new_opp_hp
        }).eq("user_id", opponent_id).execute()


    else:
        logs.append("⏭️ Вы пропускаете ход.")

    # Обновление хода и последнего действия
    supabase.table("adventure_status").update({
        "pvp_turn": user_status["pvp_turn"] + 1,
        "last_action": "\n".join(logs)
    }).eq("user_id", user_id).execute()

    # Проверка: оба ли сделали ход?
    updated_user_status = supabase.table("adventure_status").select("*").eq("user_id", user_id).execute().data[0]
    updated_opp_status = supabase.table("adventure_status").select("*").eq("user_id", opponent_id).execute().data[0]

    # Получаем имена для отчёта
    user_info = supabase.table("users").select("username").eq("user_id", user_id).execute().data[0]
    opponent_info = supabase.table("users").select("username").eq("user_id", opponent_id).execute().data[0]

    name1 = user_info["username"]
    name2 = opponent_info["username"]

    if updated_user_status["pvp_turn"] == updated_opp_status["pvp_turn"]:
        report = (
            f"📢 Ход завершён:\n\n"
            f"{name1}:\n{updated_user_status['last_action']}\n\n"
            f"{name2}:\n{updated_opp_status['last_action']}\n\n"
            f"❤️ {name1}: {updated_user_status['health']} HP\n"
            f"❤️ {name2}: {updated_opp_status['health']} HP"
        )

        # Проверка завершения боя
        result_msg = None
        if updated_user_status["health"] <= 0 and updated_opp_status["health"] <= 0:
            result_msg = "🤝 Ничья! Оба игрока пали одновременно."
        elif updated_user_status["health"] <= 0:
            result_msg = f"🏆 {name2} побеждает!\n💀 {name1} проигрывает."
        elif updated_opp_status["health"] <= 0:
            result_msg = f"🏆 {name1} побеждает!\n💀 {name2} проигрывает."

        reply_markup = get_pvp_keyboard() if not result_msg else None
        await bot.send_message(user_id, report, reply_markup=reply_markup)
        await bot.send_message(opponent_id, report, reply_markup=reply_markup)

        if result_msg:
            if updated_user_status["health"] <= 0 and updated_opp_status["health"] <= 0:
                # Ничья — ничего не меняем
                await bot.send_message(user_id, result_msg)
                await bot.send_message(opponent_id, result_msg)
            elif updated_user_status["health"] <= 0:
                # Победил opponent
                winner_record = \
                supabase.table("users").select("pvp_win, money").eq("user_id", opponent_id).execute().data[0]
                winner_wins = winner_record.get("pvp_win") or 0
                winner_money = winner_record.get("money") or 0

                loser_record = supabase.table("users").select("money").eq("user_id", user_id).execute().data[0]
                loser_money = loser_record.get("money") or 0

                # Обновляем победителю
                supabase.table("users").update({
                    "pvp_win": winner_wins + 1,
                    "money": winner_money + 100
                }).eq("user_id", opponent_id).execute()

                # Обновляем проигравшему (минус 100, но не меньше 0)
                new_loser_money = max(0, loser_money - 100)
                supabase.table("users").update({
                    "money": new_loser_money
                }).eq("user_id", user_id).execute()

                await bot.send_message(opponent_id, f"🏆 Вы победили и заработали 100💰!")
                await bot.send_message(user_id, f"💀 Вы проиграли и потеряли 100💰!")

                await bot.send_message(user_id, result_msg)
                await bot.send_message(opponent_id, result_msg)

            elif updated_opp_status["health"] <= 0:
                # Победил user
                winner_record = supabase.table("users").select("pvp_win, money").eq("user_id", user_id).execute().data[
                    0]
                winner_wins = winner_record.get("pvp_win") or 0
                winner_money = winner_record.get("money") or 0

                loser_record = supabase.table("users").select("money").eq("user_id", opponent_id).execute().data[0]
                loser_money = loser_record.get("money") or 0

                # Обновляем победителю
                supabase.table("users").update({
                    "pvp_win": winner_wins + 1,
                    "money": winner_money + 100
                }).eq("user_id", user_id).execute()

                # Обновляем проигравшему (минус 100, но не меньше 0)
                new_loser_money = max(0, loser_money - 100)
                supabase.table("users").update({
                    "money": new_loser_money
                }).eq("user_id", opponent_id).execute()

                await bot.send_message(user_id, f"🏆 Вы победили и заработали 100💰!")
                await bot.send_message(opponent_id, f"💀 Вы проиграли и потеряли 100💰!")

                await bot.send_message(user_id, result_msg)
                await bot.send_message(opponent_id, result_msg)

            # Удаление боевого статуса
            supabase.table("adventure_status").delete().or_(
                f"user_id.eq.{user_id},user_id.eq.{opponent_id}"
            ).execute()

    else:
        await callback.answer("✅ Ход принят.")

@dp.callback_query(lambda call: call.data == "back_to_forge")
async def handle_back_to_forge(call: types.CallbackQuery):
    crafter_sets = SETS.get("crafter", {})

    if not crafter_sets:
        await call.message.edit_text("⚠️ Нет доступных сетов для крафта.")
        return

    keyboard = [
        [InlineKeyboardButton(text=set_name, callback_data=f"craft_set:{set_name}")]
        for set_name in crafter_sets.keys()
    ]

    markup = InlineKeyboardMarkup(inline_keyboard=keyboard)
    await call.message.edit_text("🛠 Что вы хотите скрафтить?", reply_markup=markup)

@dp.callback_query(lambda call: call.data.startswith("craft_item:"))
async def handle_craft_item(call: types.CallbackQuery):
    item_id = int(call.data.split(":")[1])
    user_id = call.from_user.id

    found_item = None
    set_name = None

    # Ищем предмет по ID в crafter-сетах
    for s_name, s_data in SETS.get("crafter", {}).items():
        for item in s_data.get("items", []):
            if item["id"] == item_id:
                found_item = item
                set_name = s_name
                break
        if found_item:
            break

    if not found_item:
        await call.answer("❌ Предмет не найден.", show_alert=True)
        return

    item_name = found_item["name"]

    # Получаем нужные материалы
    craft_data = craft_sets.get(set_name, {})
    needed_materials = craft_data.get(item_name, {})

    # Проверка наличия всех нужных материалов
    for material_name, required_count in needed_materials.items():
        materials_resp = supabase.table("materials")\
            .select("count")\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()

        if not materials_resp.data or materials_resp.data[0]["count"] < required_count:
            await call.answer(f"❌ Не хватает материала: {material_name}", show_alert=True)
            return

    # Списываем материалы
    for material_name, required_count in needed_materials.items():
        materials_resp = supabase.table("materials")\
            .select("count")\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()

        current_count = materials_resp.data[0]["count"]
        supabase.table("materials")\
            .update({"count": current_count - required_count})\
            .eq("user_id", user_id)\
            .eq("material_name", material_name)\
            .execute()

    # Добавляем или обновляем предмет в рюкзаке
    existing = supabase.table("backpack")\
        .select("count")\
        .eq("user_id", user_id)\
        .eq("item_name", item_name)\
        .execute()

    if existing.data:
        current_count = existing.data[0]["count"]
        supabase.table("backpack")\
            .update({"count": current_count + 1})\
            .eq("user_id", user_id)\
            .eq("item_name", item_name)\
            .execute()
    else:
        supabase.table("backpack")\
            .insert({"user_id": user_id, "item_name": item_name, "count": 1})\
            .execute()

    # Сообщение об успехе
    await call.answer("✅ Вы успешно скрафтили предмет!", show_alert=True)
    await call.message.edit_text(
        f"🎉 Поздравляем! Вы создали предмет:\n<b>{item_name}</b>\n\n"
        f"🧱 Из сета: <b>{set_name}</b>",
        parse_mode="HTML"
    )
@dp.callback_query(lambda call: call.data.startswith("item_info:"))
async def handle_item_info(call: types.CallbackQuery):
    item_id = int(call.data.split(":")[1])
    found_item = None
    set_name = None

    # Ищем предмет по ID в crafter-сетах
    for s_name, s_data in SETS.get("crafter", {}).items():
        for item in s_data.get("items", []):
            if item["id"] == item_id:
                found_item = item
                set_name = s_name
                break
        if found_item:
            break

    if not found_item:
        await call.answer("❌ Предмет не найден.")
        return

    item_name = found_item["name"]
    hp = found_item.get("hp", 0)
    dmg = found_item.get("damage", 0)

    # Название части тела (ключ, кроме стандартных)
    part = next((k for k in found_item if k not in ["id", "name", "hp", "damage"]), "???")

    # Получаем нужные материалы из craft_sets
    craft_data = craft_sets.get(set_name, {})
    materials = craft_data.get(item_name, {})

    materials_text = "\n".join([f"- {mat}: {amt}" for mat, amt in materials.items()]) if materials else "❓ Нет данных."

    # Инлайн-кнопки
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛠 Скрафтить", callback_data=f"craft_item:{item_id}")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data=f"craft_set:{set_name}")]
    ])

    await call.message.edit_text(
        f"🧱 Сет: *{set_name}*\n"
        f"📦 Предмет: *{item_name}*\n\n"
        f"❤️ HP: {hp}\n⚔️ Урон: {dmg}\n"
        f"🔧 Необходимые материалы:\n{materials_text}",
        parse_mode="Markdown",
        reply_markup=keyboard
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("loc_"))
async def clan_battle_callback(callback: types.CallbackQuery):
    data = callback.data
    user_id = callback.from_user.id
    location_name = data[4:]

    if location_name not in allowed_locations:
        return

    # Получаем клан пользователя
    clan_resp = supabase.table("clan_members").select("clan_name").eq("user_id", user_id).execute()
    if not clan_resp.data:
        await callback.answer("Вы не состоите в клане.", show_alert=True)
        return
    clan = clan_resp.data[0]['clan_name']

    # Получаем health и attack пользователя из users
    user_resp = supabase.table("users").select("health", "attack").eq("user_id", user_id).execute()
    if not user_resp.data:
        await callback.answer("Пользователь не найден в таблице пользователей.", show_alert=True)
        return
    health = user_resp.data[0]['health']
    attack = user_resp.data[0]['attack']

    # Проверяем есть ли запись в clan_battle
    record_resp = supabase.table("clan_battle").select("pin").eq("user_id", user_id).execute()

    if not record_resp.data:
        # Добавляем новую запись с health и attack
        supabase.table("clan_battle").insert({
            "user_id": user_id,
            "clan_name": clan,
            "pin": location_name,
            "health": health,
            "attack": attack
        }).execute()

        await callback.answer(f"Вы выбрали локацию: {location_name}", show_alert=True)
    else:
        current_pin = record_resp.data[0]['pin']
        if current_pin == location_name:
            await callback.answer("Вы уже выбрали эту локацию!", show_alert=True)
        else:
            supabase.table("clan_battle").update({
                "pin": location_name,
                "health": health,
                "attack": attack
            }).eq("user_id", user_id).execute()

            await callback.answer(f"Локация изменена на: {location_name}", show_alert=True)




@dp.callback_query(lambda call: call.data.startswith("craft_set:"))
async def handle_craft_set_selection(call: types.CallbackQuery):
    set_name = call.data.split(":", 1)[1]
    crafter_sets = SETS.get("crafter", {})
    selected_set = crafter_sets.get(set_name)

    if not selected_set:
        await call.message.edit_text("❌ Сет не найден.")
        return

    description = selected_set.get("description", "Описание отсутствует.")
    items = selected_set.get("items", [])

    # Инлайн кнопки с названием + статы (❤️ HP, ⚔️ урон)
    item_buttons = []
    for item in items:
        name = item["name"]
        hp = item.get("hp", 0)
        dmg = item.get("damage", 0)
        stats_str = f"❤️ {hp} ⚔️ {dmg}"
        item_buttons.append([
            InlineKeyboardButton(
                text=f"{name}  {stats_str}",
                callback_data=f"item_info:{item['id']}"
            )
        ])

    # Кнопка назад
    item_buttons.append([
        InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_forge")
    ])

    markup = InlineKeyboardMarkup(inline_keyboard=item_buttons)

    # 👇 Считаем ресурсы из craft_sets
    materials_summary = {}

    craft_info = craft_sets.get(set_name, {})  # set_name должен совпадать (например "Осенний Лист 🍁")
    for item_materials in craft_info.values():
        for material, amount in item_materials.items():
            materials_summary[material] = materials_summary.get(material, 0) + amount

    # Формируем текст итоговый
    materials_text = "\n".join([f"- {mat}: {amt}" for mat, amt in materials_summary.items()])

    # Ответ
    await call.message.edit_text(
        f"🧱 Вы выбрали сет: *{set_name}*\n\n"
        f"{description}\n\n"
        f"*Необходимые материалы для всего сета:*\n{materials_text}",
        parse_mode="Markdown",
        reply_markup=markup
    )


@dp.callback_query(lambda c: c.data.startswith("equip_"))
async def handle_item_selection(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    selected_item_callback = callback_query.data

    selected_item = None
    item_category = None

    # Поиск предмета в full_items
    for category_name, category_data in full_items.items():
        for item in category_data:
            if item['callback_data'] == selected_item_callback:
                selected_item = item
                item_category = category_name
                break
        if selected_item:
            break

    if not selected_item:
        await callback_query.answer("❗ Предмет не найден.", show_alert=True)
        return

    # Получаем данные пользователя
    user_data = supabase.table("users").select("*").eq("user_id", user_id).single().execute()
    if not user_data.data:
        await callback_query.answer("❗ Пользователь не найден.", show_alert=True)
        return

    # Проверка, не надето ли уже что-то в этом слоте
    current_equipped = user_data.data.get(item_category)
    if current_equipped and current_equipped != "нет":
        await callback_query.answer(f"⛔ Уже надето: {current_equipped}", show_alert=True)
        return

    # Проверка, есть ли предмет в рюкзаке
    item_name = selected_item["name"]
    backpack_entry = supabase.table("backpack").select("count")\
        .eq("user_id", user_id).eq("item_name", item_name).single().execute()

    if not backpack_entry.data or backpack_entry.data["count"] < 1:
        await callback_query.answer("❗ У вас нет этого предмета.", show_alert=True)
        return

    new_count = backpack_entry.data["count"] - 1

    # Уменьшаем количество или удаляем предмет из рюкзака
    if new_count == 0:
        supabase.table("backpack").delete().eq("user_id", user_id).eq("item_name", item_name).execute()
    else:
        supabase.table("backpack").update({"count": new_count})\
            .eq("user_id", user_id).eq("item_name", item_name).execute()

    # Получаем характеристики предмета
    hp_bonus, damage_bonus = get_item_stats(item_name)

    # Обновляем экипировку и характеристики пользователя
    supabase.table("users").update({
        item_category: item_name,
        "health": user_data.data.get("health", 0) + hp_bonus,
        "attack": user_data.data.get("attack", 0) + damage_bonus
    }).eq("user_id", user_id).execute()

    await callback_query.message.edit_reply_markup()
    await callback_query.message.answer(f"✅ Надето: <b>{item_name}</b>")

@dp.callback_query()
async def handle_clan_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    try:
        user_id = callback.from_user.id
        data = callback.data

        # 🔒 Проверка статуса премиума
        user_result = supabase.table("users").select("premium_until, premium").eq("user_id", user_id).single().execute()
        user = user_result.data

        if user:
            premium_until_str = user.get("premium_until")
            if premium_until_str:
                premium_until = datetime.fromisoformat(premium_until_str.replace("Z", "+00:00"))
                now = datetime.now(timezone.utc)  # Зонований поточний час UTC
                if premium_until < now:
                    # Преміум закінчився
                    supabase.table("users").update({
                        "premium": False,
                        "premium_until": None
                    }).eq("user_id", user_id).execute()

                    await callback.answer("⛔ Ваш премиум закончился.", show_alert=True)
                    return
        if data.startswith("clan_"):
            await callback.answer()
            clan_key = data[5:]
            clan_name = next((name for name in CLANS if name.startswith(clan_key)), None)
            if not clan_name:
                await callback.answer("❗ Ошибка: клан не найден.", show_alert=True)
                return
            desc = CLANS[clan_name]
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text="Выбрать", callback_data=f"select_{clan_key}"),
                    InlineKeyboardButton(text="Назад", callback_data="back_to_clans")
                ]
            ])
            await callback.message.edit_text(desc, reply_markup=keyboard)

        elif data.startswith("select_"):
            await callback.answer()
            clan_key = data[7:]
            clan_name = next((name for name in CLANS if name.startswith(clan_key)), None)
            if not clan_name:
                await callback.answer("❗ Ошибка: клан не найден.", show_alert=True)
                return

            supabase.table("users").update({"clan": clan_name}).eq("user_id", user_id).execute()
            supabase.table("clan_members").upsert({"clan_name": clan_name, "user_id": user_id}).execute()

            await callback.message.edit_text(f"✅ Вы успешно выбрали клан:\n\n{CLANS[clan_name]}")
            await bot.send_message(user_id, "Теперь тебе доступно главное меню ⬇️", reply_markup=main_menu_kb)

        elif data == "back_to_clans":
            await callback.answer()
            await ask_clan_choice(callback.message)

        elif data.startswith("adventure_"):
            await callback.answer()
            location_name = data[len("adventure_"):]
            adventure = ADVENTURES.get(location_name)
            if not adventure:
                await callback.answer("❗ Приключение не найдено.", show_alert=True)
                return

            mob_preview = random.choice(adventure["mobs"])
            location_info = LOCATIONS[location_name]
            exp_range = f"{location_info['exp'][0]}–{location_info['exp'][1]}"
            money_range = f"{location_info['money'][0]}–{location_info['money'][1]}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать приключение", callback_data=f"start_adv_{location_name}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_adventures")]
            ])

            await callback.message.edit_text(
                f"📍 <b>{location_name}</b>\n"
                f"{adventure['description']}\n\n"
                f"👾 Возможные враги: <i>{', '.join(adventure['mobs'])}</i>\n"
                f"🎖 Опыт: <b>{exp_range}</b>\n"
                f"💰 Монеты: <b>{money_range}</b>",
                reply_markup=keyboard
            )

        elif data.startswith("preview_"):
            await callback.answer()
            location_name = data[len("preview_"):]
            adventure = ADVENTURES.get(location_name)
            location = LOCATIONS.get(location_name)

            if not adventure or not location:
                await callback.answer("❗ Локация не найдена.", show_alert=True)
                return

            exp_range = f"{location['exp'][0]}–{location['exp'][1]}"
            money_range = f"{location['money'][0]}–{location['money'][1]}"

            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🚀 Начать приключение", callback_data=f"start_adv_{location_name}")],
                [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_adventures")]
            ])

            await callback.message.edit_text(
                f"📍 <b>{location_name}</b>\n"
                f"{adventure['description']}\n\n"
                f"👾 Возможные враги: <i>{', '.join(adventure['mobs'])}</i>\n"
                f"🎖 Опыт: <b>{exp_range}</b>\n"
                f"💰 Монеты: <b>{money_range}</b>",
                reply_markup=keyboard
            )
        elif data.startswith("start_adv_"):
            location_name = data[len("start_adv_"):]
            location = LOCATIONS.get(location_name)
            if not location:
                await callback.answer("❗ Локация не найдена.", show_alert=True)
                return

            user_data = supabase.table("users").select("level").eq("user_id", user_id).execute()
            user_level = user_data.data[0]["level"] if user_data.data else 1
            required_level = location.get("min_level", 1)
            if user_level < required_level:
                await callback.answer(f"🔒 Доступно с {required_level} уровня.", show_alert=True)
                return

            now = datetime.utcnow()
            existing_status = supabase.table("adventure_status").select("*").eq("user_id", user_id).execute()
            if existing_status.data:
                end_time_str = existing_status.data[0]["end_time"]
                end_time = datetime.fromisoformat(end_time_str)
                if end_time > now:
                    remaining = (end_time - now).seconds
                    await callback.answer(f"⏳ Ты уже в приключении! Осталось {remaining} сек.", show_alert=True)
                    return
                else:
                    supabase.table("adventure_status").delete().eq("user_id", user_id).execute()

            await callback.answer()  # 👈 ОБЯЗАТЕЛЬНО ДО sleep или create_task

            duration = location["duration"]
            end_time = now + timedelta(seconds=duration)
            supabase.table("adventure_status").upsert({
                "user_id": user_id,
                "location": location_name,
                "end_time": end_time.isoformat()
            }).execute()

            adventure = ADVENTURES.get(location_name)
            monster = get_random_monster(location_name, adventure["mobs"])

            try:
                await callback.message.delete()
            except Exception:
                pass

            # Сообщение о начале
            await bot.send_message(
                user_id,
                f"🏃‍♂️ Ты отправился в <b>{location_name}</b>\n\n"
                f"👾 <b>Вы встретили монстра: {monster['name']}</b>\n"
                f"📖 <i>{monster['description']}</i>\n"
                f"🏷 Редкость: <b>{monster['rarity'].capitalize()}</b>\n\n"
                f"❤️ Здоровье: <b>{monster['hp']}</b>\n"
                f"💥 Урон: <b>{monster['damage']}</b>\n"
                f"🌀 Уклонение: <b>{monster['dodge']}%</b>\n"
                f"🔁 Контратака: <b>{monster['counter']}%</b>\n\n"
                f"⏳ Приключение продлится <b>{duration}</b> сек."
            )

            # ✅ Запуск фона
            asyncio.create_task(handle_adventure(user_id, location_name, monster, duration))

        elif data == "back_to_adventures":
            await callback.answer()
            buttons = [
                [InlineKeyboardButton(text=f"{name} {emoji}", callback_data=f"adventure_{name}")]
                for name, emoji in zip(ADVENTURES.keys(), ["🌲", "🏚️", "🏰"])
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.edit_text("🌍 <b>Выбери локацию:</b>", reply_markup=keyboard)

        else:
            await callback.answer("❓ Неизвестное действие.", show_alert=True)

    except Exception as e:
        await callback.answer("⚠️ Произошла ошибка. Попробуйте позже.", show_alert=True)
        print(f"Callback error: {e}")


# ---------- Run bot ----------
async def main():
    await notify_users_on_start()
    asyncio.create_task(scheduler())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

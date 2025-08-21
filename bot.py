import os
import asyncio
import re
import random
from datetime import datetime, timedelta
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
async def notify_users_on_start():
    print("Бот запущен и уведомляет пользователей...")
    # Тут можна зробити розсилку або інші дії


# ----------EXP ----------
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

    # Оновлення рівня, досвіду та очок прокачки
    supabase.table("users").update({
        "exp": new_exp,
        "level": level,
        "exp_max": exp_max,
        "level_points": level_points + level_ups
    }).eq("user_id", user_id).execute()

    if level_ups > 0:
        await bot.send_message(
            user_id,
            f"🌟 <b>Поздравляем!</b> Вы достигли <b>{level} уровня</b>!\n"
            f"🎉 Вы получили <b>{level_ups}</b> очко прокачки!"
        )

# ---------- Clans ----------
CLANS = {
    "Звездные стражи 🌌": "🛡 <b>Звездные стражи</b> — это древнее и неуловимое братство, чья связь с космосом и тайнами вселенной глубока и неразрывна. Они — вечные наблюдатели, хранители небесного порядка и защитники миров от угроз, исходящих из бездны космоса. Их взгляд устремлен к звездам, а сердца бьются в ритме галактических циклов.",
    "Сияющие маяки 🔥": "🔥 <b>Сияющие маяки</b> — это древний и благородный орден, чья миссия заключается в том, чтобы нести свет, надежду и истину через самые темные времена. Они — путеводная звезда для заблудших, символ непоколебимой веры и оплот против тьмы и хаоса. Их сила исходит из чистоты намерений, непоколебимой решимости и внутренней гармонии, которая отражается во всем, что они делают.",
    "Тенистые клинки 🌑": "🌑 <b>Тенистые клинки</b> — это древнее братство, чье существование окутано тайной и легендами. Они не стремятся к славе или открытому признанию, предпочитая действовать из теней, словно невидимые вихри, которые оставляют за собой лишь след судьбы.",
    "Безмолвные песни 🎵": "🎵 <b>Безмолвные песни</b> — это загадочное и меланхоличное сообщество, чье существование окутано завесой печали и древних тайн. Они не владеют острыми клинками или громогласными криками, их оружие — это эмоции, воспоминания и эхо забытых мелодий. Члены этого клана — хранители скорби, носители утерянных историй и проводники через лабиринты человеческих чувств."
}

SETS = {
    "strong": {
        "Бастион Титана": {
            "description": "🛡️ Массивный сет, дающий большое количество здоровья и щит для защиты",
            "items": [
                {"name": "Шлем Стража", "hp": 150, "damage": 0, "head": "Голова"},
                {"name": "Плащ Жизни", "hp": 250, "damage": 0, "body": "Тело"},
                {"name": "Перчатки Защиты", "hp": 70, "damage": 0, "gloves": "Перчатки"},
                {"name": "Пояс Скалы", "hp": 130, "damage": 0, "legs": "Ноги"},
                {"name": "Наручи Титана", "hp": 50, "damage": 0, "feet": "Ступни"},
                {"name": "Щит Вечной Стали", "hp": 150, "damage": 50, "weapon": "Оружие"}
            ]
        },
        "Клинок Бури": {
            "description": "⚔️ Легкий и стремительный сет с фокусом на урон",
            "items": [
                {"name": "Серьги Хищника", "hp": 30, "damage": 0, "head": "Голова"},
                {"name": "Амулет Хищника", "hp": 60, "damage": 0, "body": "Тело"},
                {"name": "Перчатки Гнева", "hp": 20, "damage": 0, "gloves": "Перчатки"},
                {"name": "Пояс Хищника", "hp": 30, "damage": 0, "legs": "Ноги"},
                {"name": "Сапоги Бури", "hp": 20, "damage": 0, "feet": "Ступни"},
                {"name": "Меч Бури", "hp": 0, "damage": 200, "weapon": "Оружие"}
            ]
        },
        "Возмездие": {
            "description": "🗡️ Сбалансированный сет с упором на среднее здоровье и урон",
            "items": [
                {"name": "Шлем Судьбы", "hp": 60, "damage": 0, "head": "Голова"},
                {"name": "Амулет Правосудия", "hp": 120, "damage": 0, "body": "Тело"},
                {"name": "Перчатки Карающего", "hp": 40, "damage": 0, "gloves": "Перчатки"},
                {"name": "Пояс Ответа", "hp": 60, "damage": 0, "legs": "Ноги"},
                {"name": "Сапоги Ярости", "hp": 40, "damage": 0, "feet": "Ступни"},
                {"name": "Клинок Возмездия", "hp": 0, "damage": 100, "weapon": "Оружие"}
            ]
        }
    },
    "weak": {
        "Забытый Страж": {
            "description": "🛡️ Надёжный сет с умеренным здоровьем и слабым уроном",
            "items": [
                {"name": "Шлем Былого", "hp": 25, "damage": 0, "head": "Голова"},
                {"name": "Доспех Чести", "hp": 75, "damage": 0, "body": "Тело"},
                {"name": "Наручи Былого", "hp": 25, "damage": 0, "gloves": "Перчатки"},
                {"name": "Пояс Нерушимости", "hp": 50, "damage": 0, "legs": "Ноги"},
                {"name": "Поножи Былого", "hp": 25, "damage": 0, "feet": "Ступни"},
                {"name": "Ржавая Секира", "hp": 0, "damage": 25, "weapon": "Оружие"}
            ]
        },
        "Звёздный Живописец": {
            "description": "✨ Легкий сет с минимальным здоровьем, но сильным оружием",
            "items": [
                {"name": "Капюшон Света", "hp": 5, "damage": 0, "head": "Голова"},
                {"name": "Куртка Света", "hp": 15, "damage": 0, "body": "Тело"},
                {"name": "Перчатки Красок", "hp": 15, "damage": 0, "gloves": "Перчатки"},
                {"name": "Юбка Света", "hp": 10, "damage": 0, "legs": "Ноги"},
                {"name": "Сапоги Света", "hp": 5, "damage": 0, "feet": "Ступни"},
                {"name": "Клинок Света", "hp": 0, "damage": 100, "weapon": "Оружие"}
            ]
        },
        "Охотник": {
            "description": "🏹 Сет для ловкости и средней защиты, с акцентом на оружие",
            "items": [
                {"name": "Шляпа Охотника", "hp": 10, "damage": 0, "head": "Голова"},
                {"name": "Плащ Теней", "hp": 40, "damage": 5, "body": "Тело"},
                {"name": "Перчатки Охотника", "hp": 15, "damage": 0, "gloves": "Перчатки"},
                {"name": "Штаны Охотника", "hp": 15, "damage": 0, "legs": "Ноги"},
                {"name": "Кожаные Сапоги", "hp": 20, "damage": 0, "feet": "Ступни"},
                {"name": "Трость-хлыст", "hp": 0, "damage": 45, "weapon": "Оружие"}
            ]
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

    # Основная клавиатура профиля
    profile_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎒 Рюкзак"), KeyboardButton(text="⚙️ Прокачка")],
            [KeyboardButton(text="⬅️ Главная")]
        ],
        resize_keyboard=True
    )

    # Створимо клавіатуру для предметів
    backpack_action_kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="⚔️ Надеть"), KeyboardButton(text="❌ Снять")],
            [KeyboardButton(text="⬅️ Назад")]
        ],
        resize_keyboard=True
    )

    # Функція для відображення рюкзака
    async def show_backpack(message: types.Message):
        user_id = message.from_user.id  # Отримуємо ID користувача

        # Отримуємо дані про рюкзак з таблиці backpack в Supabase
        backpack_data = supabase.table("backpack").select("item_name, count").eq("user_id", user_id).execute()

        if backpack_data.data:
            items_message = "Ваши вещи в рюкзаке:\n\n"

            for item in backpack_data.data:
                item_name = item['item_name']
                item_count = item['count']
                items_message += f"{item_name} (Количество: {item_count} шт.)\n\n"

            # Відправляємо список предметів і клавіатуру
            await message.answer(items_message, reply_markup=backpack_action_kb)
        else:
            await message.answer("У вас нет вещей в рюкзаке.", reply_markup=backpack_action_kb)

        # Дожидаемся ввода названия предмета


    async def process_item_name(msg: types.Message):
        item_name = msg.text.strip()  # Убираем лишние пробелы
        user_id = msg.from_user.id

        # Получаем данные из рюкзака пользователя
        backpack_data = supabase.table("backpack").select("item_name, count").eq("user_id", user_id).execute()

        item_found = False
        for item in backpack_data.data:
            if item['item_name'] == item_name:
                item_found = True
                item_count = item['count']
                if item_count > 0:
                    # Перебираем все сеты, чтобы найти нужную часть тела
                    item_details = None
                    part_of_body = None  # Для слота
                    for set_type, set_data in SETS.items():
                        for set_name, set_items in set_data.items():
                            for set_item in set_items['items']:
                                if set_item['name'] == item_name:
                                    item_details = set_item
                                    part_of_body = next(iter(set_item.keys()))  # Получаем название части тела
                                    break
                            if item_details:
                                break
                        if item_details:
                            break

                    if item_details and part_of_body:
                        # Если нашли нужный слот, обновляем данные пользователя
                        update_data = {part_of_body: item_name}
                        supabase.table("users").update(update_data).eq("user_id", user_id).execute()

                        # Уменьшаем количество предмета в рюкзаке
                        new_count = item_count - 1
                        supabase.table("backpack").update({"count": new_count}).eq("user_id", user_id).eq(
                            "item_name", item_name).execute()

                        await msg.answer(f"Вы одели {item_name} на {part_of_body}!", reply_markup=backpack_action_kb)
                        return
                    else:
                        await msg.answer("Не удалось найти подходящий слот для этого предмета.",
                                         reply_markup=backpack_action_kb)
                        return
                else:
                    await msg.answer(f"У вас нет предмета: {item_name} в рюкзаке.", reply_markup=backpack_action_kb)
                    return

        if not item_found:
            await msg.answer("Предмет не найден в рюкзаке.", reply_markup=backpack_action_kb)

    # Обробка натискання кнопки "Надеть"
    async def handle_equip(message: types.Message):
        await message.answer("Введите название предмета, который вы хотите надеть:",
                             reply_markup=types.ReplyKeyboardRemove())

    # Основной блок обработки сообщений
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
                f"Очки прокачки: {row.get('level_points', 0)}\n"
                f"❤️{row['health']} | 🗡{row['attack']}\n\n"
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
        await show_backpack(message)

    elif text == "⚔️ Надеть":
        await handle_equip(message)

    elif text == "❌ Снять":
        await message.answer("Виберіть предмет для зняття.", reply_markup=backpack_action_kb)

    elif text == "⬅️ Назад":
        await message.answer("Головне меню:", reply_markup=profile_kb)

    elif text == "⚙️ Прокачка":
        upgrade_kb = ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="❤️ Здоровье"), KeyboardButton(text="🗡️ Урон")],
                [KeyboardButton(text="⬅️ Назад")]
            ],
            resize_keyboard=True
        )
        await message.answer("Выберите, что прокачать:", reply_markup=upgrade_kb)

    elif text in ("❤️ Здоровье", "🗡️ Урон"):
        resp = supabase.table("users").select("level_points", "health", "attack").eq("user_id", user_id).execute()
        if not resp.data:
            return
        user = resp.data[0]
        points = user["level_points"]
        if points <= 0:
            await message.answer("❗ У вас нет очков прокачки.", reply_markup=profile_kb)
            return
        new_points = points - 1
        updates = {"level_points": new_points}
        if text == "❤️ Здоровье":
            updates["health"] = user["health"] + 10
            await message.answer("❤️ <b>Здоровье +10!</b>\nВы стали крепче и выносливее.")
        else:  # "🗡️ Урон"
            updates["attack"] = user["attack"] + 10
            await message.answer("🗡️ <b>Атака +10!</b>\nТвоя сила увеличилась!")
        supabase.table("users").update(updates).eq("user_id", user_id).execute()
        updated = supabase.table("users").select("level_points", "health", "attack").eq("user_id", user_id).execute()
        new_user = updated.data[0]
        await message.answer(
            f"🧬 <b>Текущие характеристики:</b>\n"
            f"❤️ Здоровье: <b>{new_user['health']}</b>\n"
            f"🗡️ Урон: <b>{new_user['attack']}</b>\n"
            f"🎯 Очки прокачки: <b>{new_user['level_points']}</b>"
        )

    elif text == "⬅️ Назад":
        await message.answer("Главное меню:", reply_markup=profile_kb)

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)


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

    elif text == "⬅️ Главная":
        await message.answer("Главное меню:", reply_markup=main_menu_kb)

    elif text == "⚒️ Кузница":
        await message.answer("Выберите действие:", reply_markup=forge_menu_kb)

    elif text in ("⚔️ Заточка", "🔨 Крафт"):
        await message.answer("⚙️ В разработке...", reply_markup=forge_menu_kb)

    elif text == "🛍️ Торговля":
        await message.answer("⚙️ В разработке...", reply_markup=main_menu_kb)

# ---------- Callback: Clan selection ----------
@dp.callback_query()
async def handle_clan_callbacks(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    try:
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
            await callback.answer()
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
            duration = location["duration"]
            end_time = now + timedelta(seconds=duration)
            adventure = ADVENTURES.get(location_name)
            monster = get_random_monster(location_name, adventure["mobs"])
            mob = monster["name"]
            desc = monster["description"]
            hp = monster["hp"]
            dmg = monster["damage"]
            dodge = monster["dodge"]
            counter = monster["counter"]
            rarity = monster["rarity"].capitalize()
            exp = random.randint(*location["exp"])
            money = random.randint(*location["money"])
            try:
                await callback.message.delete()
            except Exception:
                pass
            supabase.table("adventure_status").upsert({
                "user_id": user_id,
                "location": location_name,
                "end_time": end_time.isoformat()
            }).execute()
            await bot.send_message(
                user_id,
                f"🏃‍♂️ Ты отправился в <b>{location_name}</b>\n\n"
                f"👾 <b>Вы встретили монстра: {mob}</b>\n"
                f"📖 <i>{desc}</i>\n"
                f"🏷 Редкость: <b>{rarity}</b>\n\n"
                f"❤️ Здоровье: <b>{hp}</b>\n"
                f"💥 Урон: <b>{dmg}</b>\n"
                f"🌀 Уклонение: <b>{dodge}%</b>\n"
                f"🔁 Контратака: <b>{counter}%</b>\n\n"
                f"⏳ Приключение продлится <b>{duration}</b> сек."
            )
            await asyncio.sleep(duration)
            # Завершение приключения — награды
            # Обновляем деньги и опыт
            user_data = supabase.table("users").select("money").eq("user_id", user_id).execute()
            current_money = user_data.data[0]["money"] if user_data.data else 0
            await add_experience(user_id, exp)
            supabase.table("users").update({
                "money": current_money + money
            }).eq("user_id", user_id).execute()

            # Удаляем статус приключения
            supabase.table("adventure_status").delete().eq("user_id", user_id).execute()

            # Попытка выпадения предмета
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

            # Сообщаем о предмете и кладём в инвентарь, если есть дроп
            if item_dropped:
                item_name = item_dropped["name"]
                await bot.send_message(
                    user_id,
                    f"🎉 Тебе выпал {rarity_type} предмет из сета <b>{set_name}</b>:\n"
                    f"🧩 <b>{item_name}</b>"
                )
                existing = supabase.table("backpack").select("count").eq("user_id", user_id).eq("item_name",
                                                                                                item_name).execute()
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

            # Финальное сообщение о завершении приключения
            await bot.send_message(
                user_id,
                f"✅ <b>Приключение завершено!</b>\n\n"
                f"🏞️ Локация: <b>{location_name}</b>\n"
                f"⚔️ Побежденный враг: <b>{mob}</b>\n\n"
                f"🎖 Получено опыта: <b>{exp}</b>\n"
                f"💰 Получено монет: <b>{money}</b>",
                reply_markup=main_menu_kb
            )


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
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

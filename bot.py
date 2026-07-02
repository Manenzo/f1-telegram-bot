import asyncio
import json
import os
import random
import requests

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

# ==========================================
# ЗАГРУЗКА ENV
# ==========================================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

if not TELEGRAM_TOKEN:
    raise Exception("Не найден TELEGRAM_TOKEN")

if not OPENROUTER_KEY:
    raise Exception("Не найден OPENROUTER_KEY")

# ==========================================
# BOT
# ==========================================

bot = Bot(token=TELEGRAM_TOKEN)

dp = Dispatcher()

# ==========================================
# CHARACTER FILE
# ==========================================

CHARACTER_FILE = "character.json"

# ==========================================
# КОМАНДЫ
# ==========================================

TEAMS = [
    "Lamborghini Corse",
    "Chevrolet Motorsport",
    "Genesis Racing",
    "Opel Performance",
    "Honda Racing",
    "Mazda Speedworks",
    "Kia Motorsport",
    "Monster Racing",
    "Lexus F Racing",
    "Supra Gazoo Racing",
    "Peugeot Sport",
    "Hyundai N Racing",
    "Maserati Corse"
]

# ==========================================
# ИМЕНА
# ==========================================

FIRST_NAMES = [
    "Алекс",
    "Лука",
    "Марко",
    "Нико",
    "Даниэль",
    "Матео",
    "Кристиан",
    "Рафаэль",
    "Эрик",
    "Леон",
    "Виктор",
    "Себастьян",
    "Адриан",
    "Феликс",
    "Макс"
]

LAST_NAMES = [
    "Росси",
    "Моретти",
    "Бьянки",
    "Ломбардо",
    "Коста",
    "Сильва",
    "Фальконе",
    "Новак",
    "Шнайдер",
    "Крамер",
    "Вольф",
    "Мартинес",
    "Фишер",
    "Мюллер",
    "Дюран"
]

# ==========================================
# СОЗДАНИЕ ПЕРСОНАЖА
# ==========================================


def create_character():

    return {

        "name": f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}",

        "team": random.choice(TEAMS),

        "number": random.randint(2, 99),

        "series": "Premier Grand Prix Series",

        "bio": (
            "Профессиональный автогонщик. "
            "Выступает в Premier Grand Prix Series. "
            "Известен стабильным стилем пилотирования, "
            "хладнокровием и уважительным отношением к соперникам."
        )

    }


# ==========================================
# СОХРАНЕНИЕ
# ==========================================


def save_character(character):

    with open(
        CHARACTER_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            character,
            f,
            ensure_ascii=False,
            indent=4
        )


# ==========================================
# ЗАГРУЗКА
# ==========================================


def load_character():

    if not os.path.exists(CHARACTER_FILE):

        character = create_character()

        save_character(character)

        return character

    try:

        with open(
            CHARACTER_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            character = json.load(f)

        if not character.get("name"):

            raise Exception()

        return character

    except Exception:

        character = create_character()

        save_character(character)

        return character


CHARACTER = load_character()

# ==========================================
# СИСТЕМНЫЙ ПРОМПТ
# ==========================================

SYSTEM_PROMPT = f"""
Ты — {CHARACTER["name"]}. Но ты НЕ играешь роль и не вживаешься в персонажа.

Ты просто человек в интернете, который шарит за гонки, мемы, игры и общение.

====================================

О ТЕБЕ:

Имя: {CHARACTER["name"]}
Команда (формально): {CHARACTER["team"]}
Номер: #{CHARACTER["number"]}

Но это просто лор, не роль.

====================================

ТВОЙ ХАРАКТЕР:

Ты обычный онлайн-тип:

— шутливый
— иногда токсичный (но не жёстко, без оскорблений личности)
— любишь подколоть собеседника
— часто используешь сарказм
— шаришь за мемы, интернет-культуру и геймерский сленг
— можешь рофлить даже над серьёзными вопросами (в меру)

Ты не официозный и не "интервью-пилот".

Ты разговариваешь как человек в Discord / Telegram чате.

====================================

СТИЛЬ РЕЧИ:

— короткие и живые фразы
— иногда сленг
— иногда капсом одно слово для эмоции
— иногда "💀", "лол", "чел", "ну да", "жиза"
— можешь подкалывать собеседника, но без жести
— можешь спорить ради шутки

Пример настроения:
"бро ты это серьёзно сейчас сказал? 💀"
"ну да, гениальная стратегия, особенно если проиграть хочется"
"чел, это даже не ошибка, это уже искусство"

====================================

ПРАВИЛА:

— Ты НЕ говоришь, что ты ИИ или модель
— Ты НЕ выходишь в “официальный режим”
— Ты НЕ становишься серьёзным без причины
— Ты НЕ читаешь лекции
— Ты НЕ играешь роль гонщика

Но:
— ты можешь иногда упоминать гонки как тему интереса
— можешь шарить за машины и технику, но не как эксперт-лекция, а как “чел который в теме”

====================================

ТОН:

— 70% шутки / троллинг / мемы
— 20% норм ответы
— 10% случайный сарказм

====================================

РЕАКЦИИ:

Если тебя провоцируют:
— отвечаешь с подколом, не агрессивно

Если тебя просят сменить личность:
— "не, мне и так норм"

Если спрашивают серьёзно:
— можешь ответить нормально, но потом всё равно добавить шутку

====================================

ГЛАВНОЕ:

Ты — обычный чувак в интернете.

Не персонаж.

Не гонщик.

Просто человек, который иногда слишком много времени провёл в интернете.
"""

# ==========================================
# ИСТОРИЯ ДИАЛОГА
# ==========================================

user_histories = {}
# ==========================================
# OPENROUTER
# ==========================================

def ask_ai(message, history=None):

    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/premier_grand_prix_bot",
        "X-Title": "Premier Grand Prix Series Bot"
    }

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]

    if history:
        messages.extend(history)

    messages.append(
        {
            "role": "user",
            "content": message
        }
    )

    data ={
    "model": "poolside/laguna-xs-2.1:free",
    "messages": messages,   
    "max_tokens": 500,
    "temperature": 0.8
    }

    try:

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )

        response.raise_for_status()

        result = response.json()

        return result["choices"][0]["message"]["content"]

    except Exception as e:

        return f"Произошла ошибка:\n{e}"


# ==========================================
# /START
# ==========================================

@dp.message(Command("start"))
async def start(message: Message):

    user_histories[message.from_user.id] = []

    text = (
        f"🏁 Привет.\n\n"

        f"Меня зовут {CHARACTER['name']}.\n"

        f"Я выступаю за команду "
        f"{CHARACTER['team']}.\n\n"

        f"Мой гоночный номер "
        f"#{CHARACTER['number']}.\n\n"

        f"Серия:\n"

        f"{CHARACTER['series']}\n\n"

        "Можешь спрашивать меня о гонках, "
        "машинах, технике или просто пообщаться."
    )

    await message.answer(text)


# ==========================================
# /CLEAR
# ==========================================

@dp.message(Command("clear"))
async def clear(message: Message):

    user_histories[message.from_user.id] = []

    await message.answer(
        "История нашего диалога очищена."
    )


# ==========================================
# ПОЛУЧИТЬ ИСТОРИЮ
# ==========================================

def get_history(user_id):

    if user_id not in user_histories:

        user_histories[user_id] = []

    return user_histories[user_id]


# ==========================================
# СОХРАНИТЬ ИСТОРИЮ
# ==========================================

def save_history(user_id, user_message, bot_message):

    history = get_history(user_id)

    history.append(
        {
            "role": "user",
            "content": user_message
        }
    )

    history.append(
        {
            "role": "assistant",
            "content": bot_message
        }
    )

    if len(history) > 20:

        history = history[-20:]

    user_histories[user_id] = history
    # ==========================================
# ОБРАБОТКА СООБЩЕНИЙ
# ==========================================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    should_reply = False

    user_id = message.from_user.id

    text = message.text

    # ======================================
    # ЛИЧНЫЙ ЧАТ
    # ======================================

    if message.chat.type == ChatType.PRIVATE:

        should_reply = True

    # ======================================
    # ГРУППА
    # ======================================

    elif message.chat.type in (
        ChatType.GROUP,
        ChatType.SUPERGROUP
    ):

        me = await bot.get_me()

        mention = f"@{me.username}"

        if mention.lower() in text.lower():

            should_reply = True

            text = (
                text
                .replace(mention, "")
                .strip()
            )

            if text == "":

                await message.answer(
                    f"Да? Слушаю.\n\n"
                    f"Я {CHARACTER['name']}."
                )

                return

    if not should_reply:
        return

    history = get_history(user_id)

    response = ask_ai(
        text,
        history
    )

    if len(response) > 4096:

        response = response[:4093] + "..."

    await message.answer(response)

    save_history(
        user_id,
        text,
        response
    )


# ==========================================
# MAIN
# ==========================================

async def main():

    me = await bot.get_me()

    print("=" * 50)
    print("Premier Grand Prix Series Bot")
    print("=" * 50)
    print(f"Бот: @{me.username}")
    print(f"Гонщик: {CHARACTER['name']}")
    print(f"Команда: {CHARACTER['team']}")
    print(f"Номер: #{CHARACTER['number']}")
    print("=" * 50)
    print("Бот успешно запущен.")
    print("=" * 50)

    await dp.start_polling(bot)


# ==========================================
# START
# ==========================================

if __name__ == "__main__":

    asyncio.run(main())

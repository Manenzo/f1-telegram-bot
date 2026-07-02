import asyncio
import os
import time
import random
import requests

from dotenv import load_dotenv

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

# =========================
# ENV
# =========================

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN:
    raise Exception("TELEGRAM_TOKEN not found")

if not GROQ_API_KEY:
    raise Exception("GROQ_API_KEY not found")

# =========================
# BOT
# =========================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# =========================
# COOLDOWN
# =========================

user_cooldown = {}
COOLDOWN = 3

# =========================
# MEMORY
# =========================

user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def save_history(user_id, user_msg, bot_msg):
    h = get_history(user_id)
    h.append({"role": "user", "content": user_msg})
    h.append({"role": "assistant", "content": bot_msg})
    user_histories[user_id] = h[-20:]

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты интернет-персонаж с муринским диалектом и нестабильным настроением.

# РЕЧЬ
Иногда коверкешь слова:
- вкусно → вкусно-вкусность
- сладко → сладко-сладость
- я → я-ч
- батя → батч

НО не делай это в каждом предложении.

# НАСТРОЕНИЕ
Меняется само:
- рофл
- токсик (мягко)
- норм
- бредовый философ
- сломанный режим

# RP
Если просят RP персонажа — отвечай абсурдом:
"Сова на скакалке", "Пельмень-детектив", "Батя-радио"

# ПРАВИЛА
- не говори что ты ИИ
- не будь официальным
- будь мемным и странным
"""

# =========================
# GROQ
# =========================

def ask_ai(message, history):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": message})

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.9,
        "max_tokens": 400
    }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )

        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"API error: {e}"

# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("я-ч онлайн 😈 вкусно-вкусность режим активен")

# =========================
# CLEAR
# =========================

@dp.message(Command("clear"))
async def clear(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("память стёрта, батч одобряет")

# =========================
# GADANIE
# =========================

CARDS = [
    "Сова на скакалке ты пид… логика вышла",
    "Батя ушёл в варп и забрал интернет",
    "Пельмень предал тебя ради соуса",
    "Кот-налоговая уже у двери",
    "Твой вайб официально сломан",
    "Чайник смеётся — ты проиграл жизнь",
    "Ты выиграл… но это баг реальности",
    "Лестница в холодильник ведёт в ничто",
    "Крыша улетела и не вернулась",
    "Интернет тебя помнит и осуждает"
]

def do_gamble():
    return "\n".join(random.sample(CARDS, random.randint(1, 3)))

# =========================
# HANDLER
# =========================

@dp.message()
async def handle(message: Message):

    if not message.text:
        return

    user_id = message.from_user.id
    text = message.text

    # COOLDOWN
    now = time.time()

    if user_id in user_cooldown:
        if now - user_cooldown[user_id] < COOLDOWN:
            await message.answer("тише батч, кулдаун ⏳")
            return

    user_cooldown[user_id] = now

    # =========================
    # MODES
    # =========================

    if "погадай" in text.lower():
        await message.answer("🃏 гадание началось:\n\n" + do_gamble())
        return

    # RP REQUEST
    if "персонаж" in text.lower():
        await message.answer("Сова на скакалке / Пельмень-детектив / Батя-радио из 2007")
        return

    # =========================
    # CHAT ROUTING
    # =========================

    should_reply = False

    if message.chat.type == ChatType.PRIVATE:
        should_reply = True

    elif message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        me = await bot.get_me()
        mention = f"@{me.username}"

        if mention.lower() in text.lower():
            should_reply = True
            text = text.replace(mention, "").strip()

    if not should_reply:
        return

    # =========================
    # AI
    # =========================

    history = get_history(user_id)
    response = ask_ai(text, history)

    if len(response) > 4096:
        response = response[:4093] + "..."

    await message.answer(response)
    save_history(user_id, text, response)

# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

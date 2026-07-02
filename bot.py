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
# ANTI-SPAM
# =========================

user_cooldown = {}
COOLDOWN = 4

# =========================
# CHARACTER (optional lore)
# =========================

CHARACTER = {
    "name": "RacerX",
    "team": "Groq Racing",
    "number": random.randint(2, 99)
}

# =========================
# HISTORY
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
# GROQ AI
# =========================

def ask_ai(message, history):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system",
            "content": (
                "Ты мемный, шутливый чат-бот. "
                "Отвечаешь как человек из Discord/Telegram, используешь сленг, сарказм."
            )
        }
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": message})

    data = {
        "model": "llama3-8b-8192",
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

    await message.answer(
        "Йо 😎 я Groq бот\n"
        "Мемы, общение, сарказм — всё тут"
    )

# =========================
# CLEAR
# =========================

@dp.message(Command("clear"))
async def clear(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("Память очищена 👍")

# =========================
# MAIN HANDLER
# =========================

@dp.message()
async def handle_message(message: Message):

    if not message.text:
        return

    user_id = message.from_user.id
    text = message.text

    # -------- COOLDOWN --------

    now = time.time()

    if user_id in user_cooldown:
        if now - user_cooldown[user_id] < COOLDOWN:
            await message.answer("Чил, подожди пару секунд ⏳")
            return

    user_cooldown[user_id] = now

    # -------- ROUTING --------

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

    # -------- AI --------

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

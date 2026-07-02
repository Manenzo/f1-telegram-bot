import asyncio
import json
import os
import random
import requests
import time

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
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

if not TELEGRAM_TOKEN:
    raise Exception("Не найден TELEGRAM_TOKEN")

if not OPENROUTER_KEY:
    raise Exception("Не найден OPENROUTER_KEY")

# =========================
# BOT
# =========================

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# =========================
# ANTI-SPAM
# =========================

user_cooldown = {}
COOLDOWN = 3

# =========================
# CHARACTER
# =========================

CHARACTER = {
    "name": "Alex Rossi",
    "team": "Lamborghini Corse",
    "number": random.randint(2, 99),
    "series": "Premier Grand Prix Series",
}

# =========================
# HISTORY
# =========================

user_histories = {}

def get_history(user_id):
    if user_id not in user_histories:
        user_histories[user_id] = []
    return user_histories[user_id]

def save_history(user_id, user_message, bot_message):
    history = get_history(user_id)

    history.append({"role": "user", "content": user_message})
    history.append({"role": "assistant", "content": bot_message})

    user_histories[user_id] = history[-20:]

# =========================
# AI REQUEST
# =========================

def ask_ai(message, history):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
    }

    messages = [
        {
            "role": "system",
            "content": "Ты мемный, слегка токсичный, шутливый чат-бот, как Discord пользователь."
        }
    ]

    messages.extend(history)
    messages.append({"role": "user", "content": message})

    data = {
        "model": "poolside/laguna-xs-2.1:free",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.9
    }

    try:
        r = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"]

    except Exception as e:
        return f"Ошибка API: {e}"

# =========================
# START
# =========================

@dp.message(Command("start"))
async def start(message: Message):
    user_histories[message.from_user.id] = []

    await message.answer(
        f"Привет, я {CHARACTER['name']} 😎\n"
        f"Команда: {CHARACTER['team']}\n"
        f"Номер: #{CHARACTER['number']}"
    )

# =========================
# CLEAR
# =========================

@dp.message(Command("clear"))
async def clear(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("История очищена 👍")

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
            await message.answer("Подожди пару секунд ⏳")
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
# MAIN LOOP
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
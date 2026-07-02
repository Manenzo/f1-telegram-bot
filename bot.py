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

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise Exception("Missing API keys")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# =========================
# STATE
# =========================

user_state = {}
user_history = {}
user_cooldown = {}

COOLDOWN = 3

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты живой чат-персонаж.

СТИЛЬ:
- естественный русский язык
- лёгкий юмор
- иногда сарказм
- без кринжа и коверкания слов

ПОВЕДЕНИЕ:
- ты выглядишь как реальный человек в чате
- не говоришь что ты ИИ
- не используешь сломанный сленг

RP ПРАВИЛО:
Если пользователь просит "персонажа", "RP", "роль":
→ ты становишься максимально послушным
→ создаёшь качественного персонажа
→ не споришь и не шутишь лишнего
"""

# =========================
# STATE SYSTEM
# =========================

def get_state(uid):
    if uid not in user_state:
        user_state[uid] = {
            "anger": 5,
            "fatigue": 0,
            "affection": 10
        }
    return user_state[uid]


def get_history(uid):
    if uid not in user_history:
        user_history[uid] = []
    return user_history[uid]


# =========================
# EMOTIONS
# =========================

def apply_triggers(text, state):
    t = text.lower()

    if "быстро" in t:
        state["anger"] += 5
    if "лох" in t:
        state["anger"] += 10
    if "идиот" in t:
        state["anger"] += 10

    state["anger"] = max(0, min(100, state["anger"]))


def update_fatigue(state):
    state["fatigue"] = min(100, state["fatigue"] + 2)


def update_affection(state):
    state["affection"] = min(100, state["affection"] + 1)


# =========================
# PROMPT BUILDER
# =========================

def build_prompt(uid):
    state = get_state(uid)

    return SYSTEM_PROMPT + f"""

СОСТОЯНИЕ:
- злость: {state['anger']}
- усталость: {state['fatigue']}
- симпатия: {state['affection']}

ПОВЕДЕНИЕ:
- усталость → отвечай короче
- злость → чуть больше сарказма
- симпатия → дружелюбнее
"""


# =========================
# GROQ API
# =========================

def ask_ai(message, history, uid):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": build_prompt(uid)}]
    messages.extend(history)
    messages.append({"role": "user", "content": message})

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.8,
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
# COMMANDS
# =========================

@dp.message(Command("start"))
async def start(message: Message):
    user_history[message.from_user.id] = []
    await message.answer("бот запущен. я онлайн.")


@dp.message(Command("clear"))
async def clear(message: Message):
    user_history[message.from_user.id] = []
    await message.answer("память очищена")


# =========================
# HANDLER
# =========================

@dp.message()
async def handle(message: Message):

    if not message.text:
        return

    uid = message.from_user.id
    text = message.text

    # cooldown
    now = time.time()
    if uid in user_cooldown and now - user_cooldown[uid] < COOLDOWN:
        await message.answer("слишком быстро")
        return

    user_cooldown[uid] = now

    state = get_state(uid)

    # RP detection
    is_rp = any(x in text.lower() for x in ["персонаж", "rp", "роль", "создай персонажа"])
    if is_rp:
        state["affection"] += 10

    # emotions
    apply_triggers(text, state)
    update_fatigue(state)
    update_affection(state)

    # history
    history = get_history(uid)

    response = ask_ai(text, history, uid)

    # fatigue shortening
    if state["fatigue"] > 70:
        response = response[:150] + "..."

    await message.answer(response)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})

    user_history[uid] = history[-20:]


# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

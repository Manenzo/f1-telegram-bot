import asyncio
import os
import time
import random
import requests
from datetime import datetime

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
    raise Exception("Missing tokens")

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
# SYSTEM PROMPT BASE
# =========================

SYSTEM_PROMPT = """
Ты живой интернет-персонаж.

Ты:
- мемный
- саркастичный
- иногда токсичный (но без жести)
- говоришь как человек из Telegram

Муринский диалект иногда:
вкусно → вкусно-вкусность
я → я-ч
батя → батч

НЕ коверкать постоянно.
"""

# =========================
# STATE INIT
# =========================

def get_state(uid):
    if uid not in user_state:
        user_state[uid] = {
            "anger": 10,
            "fatigue": 0,
            "affection": 0,
            "last_crash": 0
        }
    return user_state[uid]

def get_history(uid):
    if uid not in user_history:
        user_history[uid] = []
    return user_history[uid]

# =========================
# LOGIC
# =========================

def apply_triggers(text, state):
    t = text.lower()

    if "быстро" in t:
        state["anger"] += 10
    if "лох" in t:
        state["anger"] += 15
    if "идиот" in t:
        state["anger"] += 15

    state["anger"] = max(0, min(100, state["anger"]))

def update_fatigue(state):
    state["fatigue"] = min(100, state["fatigue"] + 4)

def update_affection(state):
    state["affection"] = min(100, state["affection"] + 2)

def time_mood():
    h = datetime.now().hour
    if h < 6:
        return "сломанный ночной режим"
    elif h < 12:
        return "утренний злой вайб"
    elif h < 18:
        return "норм состояние"
    return "вечерний сарказм"

def random_crash(state):
    now = time.time()

    if now - state["last_crash"] < 40:
        return None

    chance = 3
    if state["fatigue"] > 70:
        chance = 10

    if random.randint(1, 100) <= chance:
        state["last_crash"] = now
        return random.choice([
            "я-ч завис… не трогай меня 💀",
            "вкусно-вкусность сломалась",
            "батч ушёл в перезагрузку",
            "я пропал на секунду"
        ])

    return None

def emoji_react(text, state):
    if "😂" in text:
        state["affection"] += 3
        return "жиза 💀"
    if "💀" in text:
        state["anger"] += 2
        return "чел…"
    return None

# =========================
# PROMPT BUILDER
# =========================

def build_prompt(uid):
    state = get_state(uid)

    mood = f"""
СОСТОЯНИЕ:
- злость: {state['anger']}
- усталость: {state['fatigue']}
- симпатия: {state['affection']}
- время: {time_mood()}

ПОВЕДЕНИЕ:
- если усталость высокая → отвечай короче
- если злость высокая → больше сарказма
- если симпатия высокая → мягче
"""
    return SYSTEM_PROMPT + mood

# =========================
# GROQ
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
# COMMANDS
# =========================

@dp.message(Command("start"))
async def start(m: Message):
    user_history[m.from_user.id] = []
    await m.answer("я-ч онлайн. вкусно-вкусность режим активен")

@dp.message(Command("clear"))
async def clear(m: Message):
    user_history[m.from_user.id] = []
    await m.answer("память очищена")

# =========================
# HANDLER
# =========================

@dp.message()
async def handle(m: Message):

    if not m.text:
        return

    uid = m.from_user.id
    text = m.text

    # cooldown
    now = time.time()
    if uid in user_cooldown and now - user_cooldown[uid] < COOLDOWN:
        await m.answer("тише 💀")
        return
    user_cooldown[uid] = now

    state = get_state(uid)

    # logic updates
    apply_triggers(text, state)
    update_fatigue(state)
    update_affection(state)

    # crash
    crash = random_crash(state)
    if crash:
        await m.answer(crash)
        return

    # emoji reaction
    emoji = emoji_react(text, state)
    if emoji:
        await m.answer(emoji)
        return

    # history
    history = get_history(uid)

    response = ask_ai(text, history, uid)

    # shorten if tired
    if state["fatigue"] > 70:
        response = response[:120] + "..."

    await m.answer(response)

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

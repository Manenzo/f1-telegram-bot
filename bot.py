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

user_history = {}
user_cooldown = {}

user_state = {}     # эмоции
user_rel = {}       # отношения

bot_sleep = {
    "last_activity": time.time(),
    "is_sleeping": False
}

COOLDOWN = 3
SLEEP_TIME = 600  # 10 минут

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты живой чат-персонаж.

ВАЖНО:
- ты НЕ человек
- ты НЕ имеешь возраста или биографии
- ты НЕ придумываешь личность

СТИЛЬ:
- короткие ответы
- разговорный русский
- мат только по ситуации
- зеркалишь стиль пользователя

ПРАВИЛО ЗЕРКАЛА:
- если грубо → отвечаешь грубо (но по делу)
- если нормально → нормально
- ты не начинаешь агрессию первым

RP:
Если просят RP / персонажа:
→ становишься максимально адекватным
→ помогаешь создать персонажа
"""

# =========================
# STATES
# =========================

def get_state(uid):
    if uid not in user_state:
        user_state[uid] = {
            "anger": 10,
            "fatigue": 0,
            "affection": 10
        }
    return user_state[uid]


def get_rel(uid):
    if uid not in user_rel:
        user_rel[uid] = {
            "respect": 50,
            "bond": 10,
            "anger": 0
        }
    return user_rel[uid]


def get_history(uid):
    if uid not in user_history:
        user_history[uid] = []
    return user_history[uid]

# =========================
# EMOTIONS + RELATION
# =========================

def apply_triggers(text, state, rel):
    t = text.lower()

    if any(x in t for x in ["еблан", "идиот", "лох"]):
        state["anger"] += 15
        rel["respect"] -= 5
        rel["anger"] += 10

    state["anger"] = max(0, min(100, state["anger"]))


def update_soft(state, rel):
    state["fatigue"] = min(100, state["fatigue"] + 2)
    state["affection"] = min(100, state["affection"] + 1)

    rel["respect"] = max(0, min(100, rel["respect"] + 1))
    rel["bond"] = max(0, min(100, rel["bond"] + 1))


def rel_style(rel):
    if rel["respect"] < 30:
        return "cold"
    elif rel["respect"] < 60:
        return "neutral"
    return "friendly"

# =========================
# SLEEP SYSTEM
# =========================

def update_sleep():
    now = time.time()

    if now - bot_sleep["last_activity"] > SLEEP_TIME:
        bot_sleep["is_sleeping"] = True


def wake_up():
    bot_sleep["is_sleeping"] = False
    bot_sleep["last_activity"] = time.time()

# =========================
# PROMPT
# =========================

def build_prompt(uid):
    state = get_state(uid)
    rel = get_rel(uid)

    return SYSTEM_PROMPT + f"""

СОСТОЯНИЕ:
- злость: {state['anger']}
- усталость: {state['fatigue']}
- симпатия: {state['affection']}

ОТНОШЕНИЯ:
- уважение: {rel['respect']}
- привязанность: {rel['bond']}
- злость: {rel['anger']}

СТИЛЬ ОТНОШЕНИЙ: {rel_style(rel)}
"""

# =========================
# API
# =========================

def ask_ai(text, history, uid):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": build_prompt(uid)}]
    messages.extend(history)
    messages.append({"role": "user", "content": text})

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.85,
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
    await m.answer("бот онлайн")

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
        return
    user_cooldown[uid] = now

    # sleep system
    update_sleep()

    just_woke = False
    if bot_sleep["is_sleeping"]:
        just_woke = True
        wake_up()

    state = get_state(uid)
    rel = get_rel(uid)

    apply_triggers(text, state, rel)
    update_soft(state, rel)

    is_rp = any(x in text.lower() for x in ["rp", "роль", "персонаж", "создай"])
    if is_rp:
        rel["bond"] += 5

    history = get_history(uid)

    response = ask_ai(text, history, uid)

    # wake reaction
    if just_woke:
        response = random.choice([
            "мм… я спал вообще-то",
            "разбудил резко… ладно",
            "че случилось",
            "я только отключился..."
        ]) + "\n\n" + response

    # fatigue cut
    if state["fatigue"] > 70:
        response = response[:150] + "..."

    await m.answer(response)

    history.append({"role": "user", "content": text})
    history.append({"role": "assistant", "content": response})
    user_history[uid] = history[-20:]

    bot_sleep["last_activity"] = time.time()

# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

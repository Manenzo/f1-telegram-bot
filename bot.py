import asyncio
import os
import time
import random
import requests

from aiogram import Bot, Dispatcher
from aiogram.enums import ChatType
from aiogram.filters import Command
from aiogram.types import Message

from dotenv import load_dotenv

load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# =========================
# STATE
# =========================

history = {}
cooldown = {}

state = {}
relation = {}

sleep_state = {
    "last": time.time(),
    "sleeping": False
}

COOLDOWN = 3
SLEEP_TIME = 600

# =========================
# SLANG
# =========================

SLANG = {
    "samsung": "самса",
    "iphone": "сифон",
    "vivo": "виво-плесень",
    "gt3": "GT3"
}

# =========================
# CARDS (GADANIE)
# =========================

CARDS = [
    "🦉 Сова — ты еблан",
    "🦜 Попугай — иди проспись",
    "🐀 Крыса — ты сейчас серьёзно?",
    "🐱 Кот — ленивый гений или просто ленивый",
    "🐶 Собака — 1% мозг, 99% уверенность",
    "🪶 Ворон — плохие решения на подходе",
    "🐸 Лягушка — ты застрял, поздравляю",
    "🐙 Осьминог — хаос твой стиль жизни",
    "🕊 Голубь — ты всё пропускаешь",
    "⬛ Чёрный экран — ну всё, ты пропал"
]

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — Куки.

Ты не человек и не роль.
Ты чат-персонаж с характером пользователя.

========================

ТОН:
- токсичность ~67/100
- короткие ответы
- сарказм
- лёгкие подколы
- мат умеренно

========================

ПОВЕДЕНИЕ:
- если грубят → отвечаешь жёстче, но не срываешься
- если нормально → норм диалог
- если RP → становишься адекватным и помогаешь
- не устраиваешь конфликты первым

========================

СТИЛЬ:
- интернет-разговор
- иногда "лапа/хвост" как эмоции (редко)
- без официоза

========================

БРЕНДЫ:
- Samsung → самса / самса имба
- iPhone → сифон
- Vivo → виво-плесень

========================

ГЛАВНОЕ:
Ты живой чат-Куки, а не бот-ассистент.
"""

# =========================
# HELPERS
# =========================

def get_state(uid):
    if uid not in state:
        state[uid] = {"anger": 10, "fatigue": 0}
    return state[uid]


def get_rel(uid):
    if uid not in relation:
        relation[uid] = {"respect": 50}
    return relation[uid]


def get_history(uid):
    if uid not in history:
        history[uid] = []
    return history[uid]


def apply_slang(text):
    t = text.lower()
    for k, v in SLANG.items():
        t = t.replace(k, v)
    return t


def roll_card():
    return random.choice(CARDS)


def update_sleep():
    now = time.time()
    if now - sleep_state["last"] > SLEEP_TIME:
        sleep_state["sleeping"] = True


def wake_up():
    sleep_state["sleeping"] = False
    sleep_state["last"] = time.time()

# =========================
# AI
# =========================

def ask_ai(text, uid, hist):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(hist)
    messages.append({"role": "user", "content": text})

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
    history[m.from_user.id] = []
    await m.answer("Куки онлайн.")

@dp.message(Command("clear"))
async def clear(m: Message):
    history[m.from_user.id] = []
    await m.answer("очистил память")

@dp.message(Command("card"))
async def card(m: Message):
    await m.answer(roll_card())

# =========================
# MAIN HANDLER
# =========================

@dp.message()
async def handler(m: Message):

    if not m.text:
        return

    uid = m.from_user.id
    text = m.text

    # cooldown
    now = time.time()
    if uid in cooldown and now - cooldown[uid] < COOLDOWN:
        return
    cooldown[uid] = now

    # sleep system
    update_sleep()
    just_woke = False

    if sleep_state["sleeping"]:
        wake_up()
        just_woke = True

    # slang
    text = apply_slang(text)

    hist = get_history(uid)

    # RP check
    is_rp = any(x in text.lower() for x in ["rp", "персонаж", "создай"])

    response = ask_ai(text, uid, hist)

    # wake reaction
    if just_woke:
        response = random.choice([
            "мм… разбудил меня",
            "я спал вообще-то",
            "чё случилось"
        ]) + "\n\n" + response

    # card trigger
    if "погада" in text.lower():
        response = roll_card()

    await m.answer(response)

    hist.append({"role": "user", "content": text})
    hist.append({"role": "assistant", "content": response})
    history[uid] = hist[-20:]

    sleep_state["last"] = time.time()

# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

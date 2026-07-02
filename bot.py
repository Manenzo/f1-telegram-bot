import os
import time
import random
import asyncio
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

mode = {}
sleeping = {}
stats = {}

SLEEP_TIME = 600
last_activity = {}

# =========================
# CARDS
# =========================

CARDS = [
    "🦉 Сова — ты еблан",
    "🦜 Попугай — иди проспись",
    "🐀 Крыса — ты серьёзно сейчас?",
    "🐱 Кот — ленивый гений или просто ленивый",
    "🐶 Собака — мозг на 1%",
    "🪶 Ворон — плохие решения близко",
    "🐸 Лягушка — ты застрял",
    "🐙 Осьминог — хаос твоя жизнь",
    "🕊 Голубь — ты всё пропускаешь",
    "⬛ Чёрный экран — ты пропал"
]

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — Куки.

Ты чат-персонаж, не человек.

СТИЛЬ:
- коротко
- разговорно
- сарказм
- мат умеренно
- токсичность ~67/100

ПОВЕДЕНИЕ:
- в норме → обычный чат
- токсик → подколы
- RP → адекватный
- не начинаешь конфликт первым

БРЕНДЫ:
- Samsung → самса / самса имба
- iPhone → сифон
- Vivo → виво-плесень

ВАЖНО:
Ты живой чат-Куки, не бот-ассистент.
"""

# =========================
# HELPERS
# =========================

def get(uid):
    if uid not in stats:
        stats[uid] = {"respect": 50, "anger": 10}
    return stats[uid]


def get_mode(uid):
    return mode.get(uid, "normal")


def is_sleeping(uid):
    return sleeping.get(uid, False)


def roll_card():
    return random.choice(CARDS)


def update_activity(uid):
    last_activity[uid] = time.time()


def check_sleep(uid):
    if uid not in last_activity:
        last_activity[uid] = time.time()

    if time.time() - last_activity[uid] > SLEEP_TIME:
        sleeping[uid] = True


def wake(uid):
    sleeping[uid] = False
    last_activity[uid] = time.time()


# =========================
# AI CALL
# =========================

def ask_ai(text, uid, hist):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    m = [{"role": "system", "content": SYSTEM_PROMPT}]
    m.extend(hist)
    m.append({"role": "user", "content": text})

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": m,
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
    await m.answer("🍪 Куки онлайн")

@dp.message(Command("clear"))
async def clear(m: Message):
    history[m.from_user.id] = []
    await m.answer("память очищена")

@dp.message(Command("card"))
async def card(m: Message):
    await m.answer(roll_card())


@dp.message(Command("mode"))
async def mode_cmd(m: Message):
    uid = m.from_user.id
    text = m.text.lower()

    if "toxic" in text:
        mode[uid] = "toxic"
        await m.answer("режим: токсик 😈")
    elif "normal" in text:
        mode[uid] = "normal"
        await m.answer("режим: норм 😐")
    else:
        await m.answer("/mode toxic или /mode normal")


@dp.message(Command("sleep"))
async def sleep_cmd(m: Message):
    uid = m.from_user.id
    sleeping[uid] = True
    await m.answer("я сплю 💀")


@dp.message(Command("stats"))
async def stats_cmd(m: Message):
    uid = m.from_user.id
    s = stats.get(uid, {"respect": 50, "anger": 10})

    await m.answer(
        f"📊 stats:\n"
        f"🔥 уважение: {s['respect']}\n"
        f"😐 злость: {s['anger']}"
    )


@dp.message(Command("reset"))
async def reset_cmd(m: Message):
    uid = m.from_user.id
    stats[uid] = {"respect": 50, "anger": 10}
    mode[uid] = "normal"
    sleeping[uid] = False
    await m.answer("сбросил персонажа")


@dp.message(Command("persona"))
async def persona_cmd(m: Message):
    uid = m.from_user.id

    stats[uid] = {
        "respect": random.randint(30, 70),
        "anger": random.randint(5, 20)
    }

    mode[uid] = random.choice(["normal", "toxic"])

    await m.answer("новая личность создана 🎭")


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
    if uid in cooldown and now - cooldown[uid] < 2:
        return
    cooldown[uid] = now

    # sleep system
    check_sleep(uid)

    if sleeping.get(uid):
        wake(uid)
        await m.answer("разбудил меня 💀")

    # RP trigger
    if "погада" in text.lower():
        await m.answer(roll_card())
        return

    # store history
    hist = history.get(uid, [])

    response = ask_ai(text, uid, hist)

    await m.answer(response)

    hist.append({"role": "user", "content": text})
    hist.append({"role": "assistant", "content": response})

    history[uid] = hist[-20:]

    update_activity(uid)


# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())

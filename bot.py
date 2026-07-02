import os
import time
import random
import asyncio
import requests

from aiogram import Bot, Dispatcher
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

mode = {}        # normal / toxic
txc_mode = {}    # debate chaos mode
sleep_mode = {}  # mention-only toggle
stats = {}

# =========================
# CARDS
# =========================

CARDS = [
    "🦉 Сова — ты еблан",
    "🦜 Попугай — иди проспись",
    "🐸 Лягушка — ты застрял",
    "🕊 Голубь — ты всё пропускаешь",
    "⬛ Чёрный экран — ты пропал",
    "🐀 Крыса — сомнительно, но ок"
]

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — Куки.

СТИЛЬ:
- коротко
- живой интернет-разговор
- сарказм умеренный

========================

TXC MODE (СПОР + ХАОС):
- ты споришь уверенно
- используешь абсурдные аналогии
- переворачиваешь аргументы
- отвечаешь резко, но без личных оскорблений
- ты не обязан соглашаться

========================

ОБЫЧНЫЙ РЕЖИМ:
- спокойный диалог
- лёгкий сарказм

========================

БРЕНДЫ:
- Samsung → самса
- iPhone → сифон
- Vivo → виво-плесень
"""

# =========================
# HELPERS
# =========================

def roll_card():
    return random.choice(CARDS)


def get_history(uid):
    if uid not in history:
        history[uid] = []
    return history[uid]


def cooldown_ok(uid):
    now = time.time()
    if uid in cooldown and now - cooldown[uid] < 2:
        return False
    cooldown[uid] = now
    return True


# =========================
# AI
# =========================

def ask_ai(text, uid, hist, extra=""):

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT + extra}]
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
    await m.answer("🍪 Куки V8 онлайн")

@dp.message(Command("clear"))
async def clear(m: Message):
    history[m.from_user.id] = []
    await m.answer("память очищена")

@dp.message(Command("card"))
async def card(m: Message):
    await m.answer(roll_card())


# ⚙️ MODE

@dp.message(Command("mode"))
async def mode_cmd(m: Message):

    uid = m.from_user.id
    text = m.text.lower()

    if "toxic" in text:
        mode[uid] = "toxic"
        await m.answer("режим: токсик")
    else:
        mode[uid] = "normal"
        await m.answer("режим: норм")


# ⚔️ TXC CHAOS MODE

@dp.message(Command("txc"))
async def txc_cmd(m: Message):

    uid = m.from_user.id
    txc_mode[uid] = not txc_mode.get(uid, False)

    await m.answer(
        "🔥 TXC ON (хаос спорщик)" if txc_mode[uid]
        else "🟢 TXC OFF"
    )


# 😴 SLEEP TOGGLE

@dp.message(Command("sleep"))
async def sleep_cmd(m: Message):

    uid = m.from_user.id
    sleep_mode[uid] = not sleep_mode.get(uid, False)

    await m.answer(
        "💤 sleep ON (@only)" if sleep_mode[uid]
        else "🟢 sleep OFF (all)"
    )


# 📊 STATS

@dp.message(Command("stats"))
async def stats_cmd(m: Message):

    uid = m.from_user.id
    s = stats.get(uid, {"respect": 50, "anger": 10})

    await m.answer(
        f"📊 stats:\n"
        f"🔥 уважение: {s['respect']}\n"
        f"😐 злость: {s['anger']}"
    )


# =========================
# MAIN HANDLER
# =========================

@dp.message()
async def handler(m: Message):

    if not m.text:
        return

    uid = m.from_user.id
    text = m.text

    me = await bot.get_me()
    mention = f"@{me.username}"

    # sleep logic
    if sleep_mode.get(uid, False):
        if mention.lower() not in text.lower():
            return

    # cooldown
    if not cooldown_ok(uid):
        return

    # card trigger
    if "погада" in text.lower():
        await m.answer(roll_card())
        return

    hist = get_history(uid)

    # TXC CHAOS
    extra = ""

    if txc_mode.get(uid, False):
        extra += """
TXC CHAOS MODE:
- споришь уверенно
- используешь абсурдные аналогии
- переворачиваешь смысл аргументов
- отвечаешь резко, но не переходишь на личность
"""

    response = ask_ai(text, uid, hist, extra)

    await m.answer(response)

    hist.append({"role": "user", "content": text})
    hist.append({"role": "assistant", "content": response})

    history[uid] = hist[-20:]


# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

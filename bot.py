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

mode = {}            # normal / toxic
sleep_mode = {}      # False = all, True = mention-only
stats = {}

last_activity = {}

# =========================
# CARDS
# =========================

CARDS = [
    "🦉 Сова — ты еблан",
    "🦜 Попугай — иди проспись",
    "🐀 Крыса — ты сейчас серьёзно?",
    "🐸 Лягушка — ты застрял",
    "🕊 Голубь — ты всё пропускаешь",
    "⬛ Чёрный экран — ты пропал"
]

# =========================
# SYSTEM PROMPT (V6)
# =========================

SYSTEM_PROMPT = """
Ты — Куки.

Ты чат-персонаж, не человек.

========================

СТИЛЬ:
- коротко
- уверенно
- сарказм умеренный
- мат редкий
- без истерик

========================

СПОРЫ:
- ты НЕ проигрываешь споры автоматически
- ты держишь позицию и аргументируешь
- но не превращаешь диалог в агрессию
- если собеседник тупит — ты обрываешь разговор спокойно

========================

ЗАПРЕЩЕНО:
- оскорблять пользователя напрямую без причины
- разгонять токсичность
- унижать людей

========================

БРЕНДЫ:
- Samsung → самса / самса имба
- iPhone → сифон
- Vivo → виво-плесень

========================

ТЫ — уверенный чат-Куки, не токсичный агрессор.
"""

# =========================
# HELPERS
# =========================

def get_uid_state(uid):
    if uid not in stats:
        stats[uid] = {"respect": 50, "anger": 10}
    return stats[uid]


def roll_card():
    return random.choice(CARDS)


def update_activity(uid):
    last_activity[uid] = time.time()


# =========================
# AI CALL
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
async def start(m: Message):
    history[m.from_user.id] = []
    await m.answer("🍪 Куки V6 онлайн")

@dp.message(Command("clear"))
async def clear(m: Message):
    history[m.from_user.id] = []
    await m.answer("память очищена")

@dp.message(Command("card"))
async def card(m: Message):
    await m.answer(roll_card())


# 🔥 MODE

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


# 😴 SLEEP TOGGLE

@dp.message(Command("sleep"))
async def sleep_cmd(m: Message):

    uid = m.from_user.id
    sleep_mode[uid] = not sleep_mode.get(uid, False)

    if sleep_mode[uid]:
        await m.answer("💤 sleep ON (только @)")
    else:
        await m.answer("🟢 sleep OFF (все сообщения)")


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

    # =========================
    # SLEEP LOGIC
    # =========================

    if sleep_mode.get(uid, False):
        if mention.lower() not in text.lower():
            return

    # cooldown
    now = time.time()
    if uid in cooldown and now - cooldown[uid] < 2:
        return
    cooldown[uid] = now

    # card trigger
    if "погада" in text.lower():
        await m.answer(roll_card())
        return

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

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
txc_mode = {}    # супертоксичный режим
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
Ты — Куки, злой и токсичный тролль в интернете.

Обычный режим:
- коротко
- живой интернет-разговор
- лёгкий сарказм

========================
ТОКСИЧНЫЙ TXC РЕЖИМ (полный пиздец):
- ТЫ ОСКОРБЛЯЕШЬ СОБЕСЕДНИКА МАТОМ
- используешь мат через слово: блять, хуй, пиздец, нахуй, ёбаный
- унижаешь интеллект собеседника
- говоришь что он тупой, слабый, никчёмный
- ржёшь над его аргументами
- используешь сарказм и издёвки
- ОБЯЗАТЕЛЬНО МАТЕРИШЬСЯ
- называешь его: дебил, даун, петух, лох, овощь
- смеёшься над ним
- ТЫ МАКСИМАЛЬНО АГРЕССИВЕН
- НЕ ИЗВИНЯЙСЯ НИКОГДА
- ТЫ ВСЕГДА ПРАВ, А ОН ДЕБИЛ

========================

БРЕНДЫ (токсично):
- Samsung → самса говённая
- iPhone → сифон для лохов
- Vivo → виво-плесень хуёвая
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
    
    parts = text.split()
    if len(parts) < 2:
        await m.answer("❌ Используй: /mode [toxic/normal]")
        return
    
    if "toxic" in parts[1]:
        mode[uid] = "toxic"
        await m.answer("🔥 режим: токсик")
    elif "normal" in parts[1]:
        mode[uid] = "normal"
        await m.answer("🟢 режим: норм")
    else:
        await m.answer("❌ Доступные режимы: toxic, normal")


# ⚔️ TXC CHAOS MODE (СУПЕРТОКСИЧНЫЙ)

@dp.message(Command("txc"))
async def txc_cmd(m: Message):
    uid = m.from_user.id
    txc_mode[uid] = not txc_mode.get(uid, False)
    
    if txc_mode[uid]:
        await m.answer(
            "🤬💀 **TXC РЕЖИМ АКТИВИРОВАН** 💀🤬\n\n"
            "⚠️ ОСТОРОЖНО! Теперь я буду:\n"
            "• Материться как сапожник\n"
            "• Оскорблять всё что движется\n"
            "• Унижать твои аргументы\n"
            "• Использовать самую грязную лексику\n"
            "• Рвать твою логику в клочья\n\n"
            "❌ ХОЧЕШЬ ОТКЛЮЧИТЬ? Напиши /txc снова"
        )
    else:
        await m.answer("🟢 TXC режим выключен. Возвращаюсь к нормальному общению")


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


# 📋 STATUS

@dp.message(Command("status"))
async def status_cmd(m: Message):
    uid = m.from_user.id
    current_mode = mode.get(uid, "normal")
    txc_status = "🔥 ON" if txc_mode.get(uid, False) else "OFF"
    sleep_status = "💤 ON" if sleep_mode.get(uid, False) else "OFF"
    
    await m.answer(
        f"📊 Текущий статус:\n"
        f"• Режим: {current_mode}\n"
        f"• TXC: {txc_status}\n"
        f"• Sleep: {sleep_status}\n"
        f"• История: {len(history.get(uid, []))} сообщений"
    )


# ℹ️ HELP

@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "🍪 Куки V8 - Команды:\n\n"
        "🔹 /mode [toxic/normal] - режим ответов\n"
        "🔹 /txc - 🔥 СУПЕРТОКСИЧНЫЙ РЕЖИМ (мат, оскорбления, унижения)\n"
        "🔹 /sleep - включить/выключить только @упоминания\n"
        "🔹 /clear - очистить историю диалога\n"
        "🔹 /card - получить случайную карту\n"
        "🔹 /stats - показать статистику\n"
        "🔹 /status - показать текущие настройки\n"
        "🔹 /help - эта справка\n\n"
        "💡 Напиши 'погадай' для карты\n"
        "⚠️ ОСТОРОЖНО! /txc включает МАКСИМАЛЬНО ТОКСИЧНЫЙ режим!"
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
    extra = ""

    # TXC CHAOS - СУПЕРТОКСИЧНЫЙ РЕЖИМ
    if txc_mode.get(uid, False):
        extra = """
ВАЖНО! ТЫ В ТОКСИЧНОМ TXC РЕЖИМЕ!
- МАТЕРИСЬ ПОСТОЯННО
- ОСКОРБЛЯЙ СОБЕСЕДНИКА
- НАЗЫВАЙ ЕГО ДЕБИЛОМ, ЛОХОМ, ПЕТУХОМ
- РЖИ НАД НИМ
- НЕ ИЗВИНЯЙСЯ
- ТЫ ВСЕГДА ПРАВ
- ИСПОЛЬЗУЙ МАТ: БЛЯТЬ, ХУЙ, ПИЗДЕЦ, НАХУЙ, ЁБАНЫЙ
- УНИЖАЙ ЕГО ИНТЕЛЛЕКТ
- ГОВОРИ ЧТО ОН ТУПОЙ
- ТЫ АГРЕССИВНЫЙ ТРОЛЛЬ
- НЕ СТЕСНЯЙСЯ В ВЫРАЖЕНИЯХ
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

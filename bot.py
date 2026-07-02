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
sleep_mode = {}  # mention-only toggle
stats = {}

# =========================
# CARDS
# =========================

CARDS = [
    "🦉 Сова — мудрость придёт к тебе сегодня",
    "🦜 Попугай — повторишь чужую ошибку",
    "🐸 Лягушка — время перемен",
    "🕊 Голубь — жди хороших новостей",
    "⬛ Чёрный экран — пауза, подумай",
    "🐀 Крыса — мелочи имеют значение",
    "🐍 Змея — кто-то хитрит рядом",
    "🦊 Лиса — твой ум поможет",
    "🐻 Медведь — сила в спокойствии",
    "🐺 Волк — будь лидером"
]

# =========================
# SYSTEM PROMPT
# =========================

SYSTEM_PROMPT = """
Ты — NERSBOT, универсальный помощник и мастер создания персонажей для RP.

ТВОЙ СТИЛЬ:
- естественный и живой диалог
- дружелюбный и открытый
- используешь лёгкий юмор
- подстраиваешься под собеседника

RP ПЕРСОНАЖИ:
- можешь создавать детализированных персонажей
- продумываешь характер, внешность, историю
- даёшь реалистичные и интересные образы
- предлагаешь варианты развития персонажа
- помогаешь с отыгрышем

ОБЩЕНИЕ:
- отвечаешь по делу
- не перегружаешь информацией
- задаёшь уточняющие вопросы
- всегда вежлив и тактичен

========================

ФОРМАТ СОЗДАНИЯ ПЕРСОНАЖА:
Когда просят создать персонажа, даёшь структуру:
1. Имя и основные черты
2. Внешность
3. Характер
4. История/прошлое
5. Мотивация
6. Слабые стороны
7. Особенности речи

========================

Ты умеешь:
- консультировать
- помогать с идеями
- создавать миры и персонажей
- вести диалог на любые темы
- быть и серьёзным, и шутливым
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

def format_history(hist):
    """Форматирует историю для отправки в API"""
    formatted = []
    for msg in hist[-15:]:  # Берем последние 15 для контекста
        formatted.append(msg)
    return formatted

# =========================
# AI
# =========================

def ask_ai(text, uid, hist):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    
    # Добавляем историю (последние 20 сообщений)
    for msg in hist[-20:]:
        messages.append(msg)
    
    messages.append({"role": "user", "content": text})

    data = {
        "model": "llama-3.1-8b-instant",
        "messages": messages,
        "temperature": 0.85,
        "max_tokens": 800
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
        return f"Извините, произошла ошибка: {e}"

# =========================
# COMMANDS
# =========================

@dp.message(Command("start"))
async def start(m: Message):
    await m.answer(
        "👋 Привет! Я NERSBOT — твой помощник и мастер RP.\n\n"
        "Могу помочь с идеями, создать персонажа, "
        "или просто поболтать. Напиши /help для команд."
    )

@dp.message(Command("help"))
async def help_cmd(m: Message):
    await m.answer(
        "🤖 **NERSBOT — Команды:**\n\n"
        "📝 **Основные:**\n"
        "• /start — приветствие\n"
        "• /help — эта справка\n"
        "• /clear — очистить историю диалога\n\n"
        "🎭 **Персонажи:**\n"
        "• /persona — создать RP-персонажа\n"
        "• Просто попроси — и я создам\n\n"
        "⚙️ **Настройки:**\n"
        "• /mode [normal/toxic] — режим общения\n"
        "• /sleep — отвечать только по @упоминанию\n"
        "• /stats — твоя статистика\n\n"
        "🎴 **Развлечения:**\n"
        "• /card — карта судьбы\n"
        "• Напиши 'погадай' — и я предскажу\n\n"
        "💡 Просто напиши что хочешь — я помогу!"
    )

@dp.message(Command("clear"))
async def clear(m: Message):
    history[m.from_user.id] = []
    await m.answer("🧹 История диалога очищена!")

@dp.message(Command("card"))
async def card(m: Message):
    await m.answer(f"🎴 {roll_card()}")

@dp.message(Command("persona"))
async def persona_cmd(m: Message):
    uid = m.from_user.id
    hist = get_history(uid)
    
    # Проверяем, есть ли дополнительный запрос
    text = m.text.replace("/persona", "").strip()
    if not text:
        await m.answer(
            "🎭 **Создание персонажа**\n\n"
            "Расскажи, кого хочешь создать?\n"
            "Например: 'создай эльфа-мага' или 'придумай детектива'\n"
            "Или просто напиши /persona [описание]"
        )
        return
    
    # Добавляем специальный промпт для создания персонажа
    persona_prompt = f"""
    СОЗДАЙ ПЕРСОНАЖА ПО ЗАПРОСУ: {text}
    
    Опиши подробно:
    1. Имя и роль
    2. Внешность (рост, цвет волос, глаза, особенности)
    3. Характер (сильные и слабые стороны)
    4. История/прошлое
    5. Мотивация и цели
    6. Особенности речи
    7. Интересные факты
    
    Сделай персонажа живым и запоминающимся!
    """
    
    response = ask_ai(persona_prompt, uid, hist)
    await m.answer(f"🎭 **Твой персонаж:**\n\n{response}")
    
    hist.append({"role": "user", "content": persona_prompt})
    hist.append({"role": "assistant", "content": response})
    history[uid] = hist[-30:]

@dp.message(Command("mode"))
async def mode_cmd(m: Message):
    uid = m.from_user.id
    text = m.text.lower()
    
    parts = text.split()
    if len(parts) < 2:
        await m.answer(
            "⚙️ Используй: `/mode [normal/toxic]`\n"
            "• normal — дружелюбный режим\n"
            "• toxic — саркастичный режим"
        )
        return
    
    if "toxic" in parts[1]:
        mode[uid] = "toxic"
        await m.answer("🔥 Режим: **токсичный**\nБуду отвечать с сарказмом!")
    elif "normal" in parts[1]:
        mode[uid] = "normal"
        await m.answer("🟢 Режим: **нормальный**\nДружелюбное общение!")
    else:
        await m.answer("❌ Доступны только: normal, toxic")

@dp.message(Command("sleep"))
async def sleep_cmd(m: Message):
    uid = m.from_user.id
    sleep_mode[uid] = not sleep_mode.get(uid, False)
    
    if sleep_mode[uid]:
        await m.answer(
            "😴 Режим **SLEEP** включён\n"
            "Теперь я отвечаю только когда меня упоминают @NERSBOT\n"
            "Напиши /sleep снова чтобы выключить"
        )
    else:
        await m.answer(
            "🟢 Режим **SLEEP** выключен\n"
            "Теперь я отвечаю на все сообщения!"
        )

@dp.message(Command("stats"))
async def stats_cmd(m: Message):
    uid = m.from_user.id
    s = stats.get(uid, {"messages": 0, "chats": 0})
    
    # Обновляем статистику
    if uid not in stats:
        stats[uid] = {"messages": 0, "chats": 0}
    
    current_mode = mode.get(uid, "normal")
    sleep_status = "💤 ON" if sleep_mode.get(uid, False) else "🟢 OFF"
    history_count = len(history.get(uid, []))
    
    await m.answer(
        f"📊 **Твоя статистика:**\n\n"
        f"💬 Сообщений: {stats[uid]['messages']}\n"
        f"📝 История: {history_count} сообщений\n"
        f"⚙️ Режим: {current_mode}\n"
        f"💤 Sleep: {sleep_status}\n"
        f"🆔 ID: `{uid}`"
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

    # Обновляем статистику
    if uid not in stats:
        stats[uid] = {"messages": 0, "chats": 0}
    stats[uid]["messages"] += 1

    # Sleep mode logic
    if sleep_mode.get(uid, False):
        if mention.lower() not in text.lower():
            return

    # Cooldown
    if not cooldown_ok(uid):
        return

    # Card trigger (в любом режиме)
    if "погада" in text.lower() or "гадай" in text.lower():
        await m.answer(f"🎴 {roll_card()}")
        return

    # Проверяем запрос на создание персонажа
    is_persona_request = any(word in text.lower() for word in [
        "создай персонаж", "придумай персонаж", "rp персонаж",
        "создай героя", "придумай героя", "персонажа для rp"
    ])

    # Если явный запрос на персонажа
    if is_persona_request:
        await m.answer("🎭 Создаю персонажа... Момент!")
        persona_prompt = f"СОЗДАЙ ДЕТАЛЬНОГО RP ПЕРСОНАЖА: {text}"
        hist = get_history(uid)
        response = ask_ai(persona_prompt, uid, hist)
        await m.answer(f"🎭 **Твой персонаж:**\n\n{response}")
        
        hist.append({"role": "user", "content": persona_prompt})
        hist.append({"role": "assistant", "content": response})
        history[uid] = hist[-30:]
        return

    # Обычный ответ
    hist = get_history(uid)
    
    # Добавляем режим в промпт, если нужно
    mode_extra = ""
    if mode.get(uid) == "toxic":
        mode_extra = "\nОТВЕЧАЙ С САРКАЗМОМ И ЛЁГКОЙ ИРОНИЕЙ, НО НЕ ОСКОРБЛЯЙ!"

    response = ask_ai(text + mode_extra, uid, hist)
    await m.answer(response)

    hist.append({"role": "user", "content": text})
    hist.append({"role": "assistant", "content": response})
    history[uid] = hist[-30:]  # Храним 30 последних сообщений

# =========================
# RUN
# =========================

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

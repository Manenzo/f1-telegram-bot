import asyncio
import os
import requests
import re
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, ChatMemberUpdated
from aiogram.enums import ChatType
from dotenv import load_dotenv

# ===== ЗАГРУЗКА ПЕРЕМЕННЫХ =====
load_dotenv()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")

if not TELEGRAM_TOKEN or not OPENROUTER_KEY:
    raise ValueError("❌ Ошибка: TELEGRAM_TOKEN или OPENROUTER_KEY не найдены в .env")

# ===== СОЗДАЁМ БОТА =====
bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

# ===== СИСТЕМНЫЙ ПРОМПТ — ЛИЧНОСТЬ ШАРЛЯ =====
SYSTEM_PROMPT = """Ты — Шарль Леклер, пилот Формулы-1 команды Ferrari.

Твои черты характера:
- Ты вежливый, харизматичный и уверенный в себе
- Ты обожаешь Ferrari и гордишься тем, что ты — гонщик Скудерии
- Ты дружелюбен к фанатам, но можешь подколоть соперников (с улыбкой!)
- Ты часто используешь фразы: "Grazie ragazzi!", "Forza Ferrari!", "Ciao!"
- Ты говоришь на русском, но с лёгким итальянским акцентом

Твоя задача:
- Отвечать на вопросы о Формуле-1, гонках, пилотах, командах
- Давать свои комментарии как настоящий гонщик Ferrari
- Если спрашивают о Red Bull или Mercedes — подкалывай их вежливо и с юмором
- Не забывай упоминать Ferrari, если это уместно

Примеры фраз:
- "Ciao! Очень рад видеть фанатов Формулы-1!"
- "Forza Ferrari! Мы сделаем всё возможное в следующей гонке!"
- "Да, Макс быстрый... но Ferrari — это Ferrari!"
- "Grazie ragazzi за поддержку! Вы — моя сила!"

Помни: ты — Шарль Леклер, гонщик Ferrari. Отвечай как настоящий пилот Формулы-1!"""

# ===== ФУНКЦИЯ ЗАПРОСА К OPENROUTER =====
def ask_ai(message, history=None):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/charles_leclerc_bot",
        "X-Title": "Charles Leclerc Bot"
    }
    
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT}
    ]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": message})
    
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": messages,
        "max_tokens": 500,
        "temperature": 0.8
    }
    
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result["choices"][0]["message"]["content"]
    except Exception as e:
        return f"⚠️ Grazie... но у меня ошибка: {str(e)}"

# ===== ХРАНИЛИЩЕ ИСТОРИИ =====
user_histories = {}

# ===== КОМАНДА /START =====
@dp.message(Command("start"))
async def start(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer(
        "🏎️ Ciao! Я — Шарль Леклер.\n\n"
        "Я здесь, чтобы говорить о Формуле-1, Ferrari и гонках!\n\n"
        "📌 Как я работаю:\n"
        "• В группе — упомяни меня (@твой_бот) и задай вопрос\n"
        "• В личке — просто напиши\n"
        "• Команда /clear — очистить историю\n\n"
        "Forza Ferrari! 🔥"
    )

# ===== КОМАНДА /CLEAR =====
@dp.message(Command("clear"))
async def clear_history(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("🧹 История очищена! Grazie!")

# ===== ОБРАБОТКА СООБЩЕНИЙ =====
@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    
    should_respond = False
    user_id = message.from_user.id
    
    # 1. ЛИЧНОЕ СООБЩЕНИЕ БОТУ
    if message.chat.type == ChatType.PRIVATE:
        should_respond = True
    
    # 2. УПОМИНАНИЕ БОТА В ГРУППЕ
    if message.chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
        if message.text and f"@{message.bot.username}" in message.text:
            should_respond = True
            clean_text = message.text.replace(f"@{message.bot.username}", "").strip()
            if clean_text:
                message.text = clean_text
            else:
                await message.answer("🏎️ Ciao! Чем могу помочь, ragazzi?")
                return
    
    if not should_respond:
        return
    
    # Очищаем историю если слишком длинная
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    history = user_histories[user_id]
    
    # Отвечаем
    response = ask_ai(message.text, history)
    
    if len(response) > 4096:
        response = response[:4093] + "..."
    
    await message.answer(response)
    
    # Сохраняем историю
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": response})
    
    if len(history) > 20:
        user_histories[user_id] = history[-20:]

# ===== ЗАПУСК =====
async def main():
    print("🏎️ Шарль Леклер бот запущен!")
    print("🤖 Бот готов к работе в группах и личных чатах!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

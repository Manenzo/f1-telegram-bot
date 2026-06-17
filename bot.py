import asyncio
import os
import requests
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
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

# ===== ФУНКЦИЯ ЗАПРОСА К OPENROUTER =====
def ask_ai(message, history=None):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://t.me/f1_assistant_bot",
        "X-Title": "F1 Assistant Bot"
    }
    
    messages = [
        {"role": "system", "content": "Ты — помощник по Формуле-1. Отвечай на русском языке. Если вопрос не о F1, вежливо скажи, что ты специализируешься только на Формуле-1."}
    ]
    
    if history:
        messages.extend(history)
    
    messages.append({"role": "user", "content": message})
    
    data = {
        "model": "openai/gpt-4o-mini",
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
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
        return f"⚠️ Ошибка: {str(e)}"

# ===== ХРАНИЛИЩЕ ИСТОРИИ =====
user_histories = {}

# ===== КОМАНДА /START =====
@dp.message(Command("start"))
async def start(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer(
        "🏁 Привет! Я бот-помощник по Формуле-1.\n\n"
        "📌 Доступные команды:\n"
        "/start — начать\n"
        "/help — помощь\n"
        "/clear — очистить историю\n\n"
        "Просто задавай вопросы о F1! 🏎️"
    )

# ===== КОМАНДА /HELP =====
@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🤖 Я отвечаю на вопросы о Формуле-1:\n\n"
        "🏎️ Пилоты — статистика, факты, карьера\n"
        "🏁 Команды — история, достижения\n"
        "📅 Гонки — результаты, расписание\n"
        "📊 Техника — болиды, двигатели, шины\n\n"
        "Просто напиши вопрос! 🔥"
    )

# ===== КОМАНДА /CLEAR =====
@dp.message(Command("clear"))
async def clear_history(message: Message):
    user_histories[message.from_user.id] = []
    await message.answer("🧹 История диалога очищена!")

# ===== ОБРАБОТКА СООБЩЕНИЙ =====
@dp.message()
async def handle_message(message: Message):
    if not message.text:
        return
    
    user_id = message.from_user.id
    
    if user_id not in user_histories:
        user_histories[user_id] = []
    
    history = user_histories[user_id]
    
    response = ask_ai(message.text, history)
    
    if len(response) > 4096:
        response = response[:4093] + "..."
    
    await message.answer(response)
    
    history.append({"role": "user", "content": message.text})
    history.append({"role": "assistant", "content": response})
    
    if len(history) > 20:
        user_histories[user_id] = history[-20:]

# ===== ЗАПУСК БОТА =====
async def main():
    print("🏁 Бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

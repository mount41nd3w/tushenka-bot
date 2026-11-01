"""
Тушёнка — простой Telegram-бот с ответами на частые вопросы.

На Render (webhook) — достаточно переменной TOKEN:
    Render сам подставит RENDER_EXTERNAL_URL и PORT.

Локально (polling):
    export TOKEN="..."
    python bot.py
"""

import logging
import os
import asyncio

try:
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.environ.get("TOKEN", "").strip()

# На Render адрес сервиса приходит в RENDER_EXTERNAL_URL автоматически.
WEBHOOK_URL = (
    os.environ.get("WEBHOOK_URL", "").strip()
    or os.environ.get("RENDER_EXTERNAL_URL", "").strip()
).rstrip("/")

PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("tushenka")

if not TOKEN:
    raise SystemExit(
        "Не задан TOKEN. Добавьте переменную окружения TOKEN со значением из BotFather."
    )

# ---------------------------------------------------------------------------
# Словарь вопросов-ответов. Ключ — корень слова, проверяется вхождением
# в текст сообщения (в нижнем регистре). Побеждает самое длинное совпадение.
# ---------------------------------------------------------------------------
QA = {
    "привет": "Привет! Чем могу помочь?",
    "здравствуй": "Здравствуйте! Задайте вопрос — постараюсь ответить.",
    "хай": "Привет! Слушаю вас.",
    "добрый день": "Добрый день! Что вас интересует?",
    "доброе утро": "Доброе утро! Чем помочь?",
    "добрый вечер": "Добрый вечер! Слушаю ваш вопрос.",
    "как дела": "У меня всё отлично — я же банка тушёнки :) А у вас?",
    "как ты": "Работаю без перерыва на обед. Готов отвечать на вопросы.",
    "спасибо": "Пожалуйста! Обращайтесь.",
    "пока": "До встречи! Возвращайтесь.",
    "кто ты": "Я Тушёнка — Telegram-бот, который отвечает на простые вопросы.",
    "как тебя зовут": "Меня зовут Тушёнка.",
    "что ты умеешь делать": "Пока я умею отвечать на простые вопросы. Функции будут расширяться.",
    "что ты умеешь": (
        "Пока я умею отвечать на простые вопросы: приветствия, "
        "«как дела», «кто ты». Скоро добавлю новые функции."
    ),
    "ты бот": "Да, я бот. И, как видите, из тушёнки.",
    "что такое туш": "Тушёнка — консервированное мясо, обычно говядина или свинина.",
    "погода": "Прогноз я не смотрю — банки обычно не выходят на улицу.",
    "время": "Точное время лучше уточнить на устройстве: у меня нет часов.",
}

GREETING = (
    "Я Тушёнка, отвечаю на простые вопросы. "
    "Попробуйте: «привет», «как дела», «кто ты»."
)


def find_answer(text: str) -> str:
    """Возвращает самое точное совпадение из QA или приветствие."""
    lowered = text.lower().strip()
    best_key, best_answer = "", GREETING
    for key, answer in QA.items():
        if key in lowered and len(key) > len(best_key):
            best_key, best_answer = key, answer
    return best_answer


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Привет! Я Тушёнка — отвечаю на простые вопросы.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(GREETING)


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    await update.message.reply_text(find_answer(update.message.text))


def build_application():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, respond))
    return app


if __name__ == "__main__":
    application = build_application()
    if WEBHOOK_URL:
        log.info("Запуск через webhook: %s (порт %s)", WEBHOOK_URL, PORT)
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL}/{TOKEN}",
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
        )
    else:
        log.info("Запуск через polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

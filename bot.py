"""
Тушенка — простой Telegram-бот с ответами на частые вопросы.

Локально (polling):
    export TOKEN="9234686778:AAFSBapiM2BYOgGwmvYRKBfdZq6jC0BKdp4"
    python bot.py

На хостинге (webhook) — достаточно задать WEBHOOK_URL:
    export TOKEN="..."
    export WEBHOOK_URL="https://<ваш-сервис>/"
    python bot.py
"""

import logging
import os

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

TOKEN = os.environ.get(
    "TOKEN", "9234686778:AAFSBapiM2BYOgGwmvYRKBfdZq6jC0BKdp4"
)
WEBHOOK_URL = os.environ.get("WEBHOOK_URL", "").strip()
PORT = int(os.environ.get("PORT", 8080))

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
logging.getLogger("httpx").setLevel(logging.WARNING)
log = logging.getLogger("tushenka")

# ---------------------------------------------------------------------------
# Словарь вопросов-ответов. Ключ — корень слова, проверяется вхождением
# в текст сообщения (в нижнем регистре). Порядок важен: более специфичные
# формулировки должны идти выше общих.
# ---------------------------------------------------------------------------
QA = {
    # приветствия
    "привет": "Привет! Чем могу помочь?",
    "здравствуй": "Здравствуйте! Задайте вопрос — постараюсь ответить.",
    "хай": "Привет! Слушаю вас.",
    "добрый день": "Добрый день! Что вас интересует?",
    "доброе утро": "Доброе утро! Чем помочь?",
    "добрый вечер": "Добрый вечер! Слушаю ваш вопрос.",
    # вежливость и состояние
    "как дела": "У меня всё отлично — я же банка тушёнки :) А у вас?",
    "как ты": "Работаю без перерыва на обед. Готов отвечать на вопросы.",
    "спасибо": "Пожалуйста! Обращайтесь.",
    "пока": "До встречи! Возвращайтесь.",
    # о боте
    "кто ты": "Я Тушёнка — Telegram-бот, который отвечает на простые вопросы.",
    "как тебя зовут": "Меня зовут Тушёнка.",
    "что ты умеешь": (
        "Пока я умею отвечать на простые вопросы: приветствия, "
        "«как дела», «кто ты». Скоро добавлю новые функции."
    ),
    "что ты умеешь делать": (
        "Пока я умею отвечать на простые вопросы. Функции будут расширяться."
    ),
    "ты бот": "Да, я бот. И, как видите, из тушёнки.",
    # простые справочные
    "что такое туш": "Тушёнка — консервированное мясо, обычно говядина или свинина.",
    "погода": "Прогноз я не смотрю — банки обычно не выходят на улицу.",
    "время": "Точное время лучше уточнить на устройстве: у меня нет часов.",
    "помощь": "Напишите вопрос простыми словами — я поищу ответ.",
    "help": "Напишите вопрос простыми словами — я поищу ответ.",
}

GREETING = (
    "Я Тушёнка, отвечаю на простые вопросы. "
    "Попробуйте: «привет», «как дела», «кто ты»."
)


def find_answer(text: str) -> str:
    """Возвращает первый подходящий ответ или приветствие."""
    lowered = text.lower().strip()
    best = None
    for key, answer in QA.items():
        if key in lowered:
            # предпочитаем более длинное совпадение (более точный вопрос)
            if best is None or len(key) > len(best[0]):
                best = (key, answer)
    return best[1] if best else GREETING


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Привет! Я Тушёнка — отвечаю на простые вопросы."
    )


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
        # Продакшн: Telegram сам присылает обновления на HTTPS-адрес.
        log.info("Запуск через webhook: %s", WEBHOOK_URL)
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{WEBHOOK_URL.rstrip('/')}/{TOKEN}",
            allowed_updates=Update.ALL_TYPES,
        )
    else:
        # Разработка: бот сам опрашивает Telegram.
        log.info("Запуск через polling")
        application.run_polling(allowed_updates=Update.ALL_TYPES)

"""
Тушёнка — Telegram-бот с меню на кнопках.

На Render (webhook) — достаточно переменной TOKEN:
    Render сам подставит RENDER_EXTERNAL_URL и PORT.

Локально (polling):
    export TOKEN="..."
    python bot.py
"""

import asyncio
import logging
import os

try:  # Python 3.14 требует явного создания event loop
    asyncio.get_event_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
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

GREETING = (
    "Привет! Я <b>Тушёнка</b> 🥫\n"
    "Выберите раздел в меню ниже — или просто напишите вопрос текстом."
)

# ---------------------------------------------------------------------------
# Меню: текст экрана + кнопки. callback_data — ключ следующего экрана.
# ---------------------------------------------------------------------------
MENU = {
    "root": {
        "text": GREETING,
        "buttons": [
            ("ℹ️ О боте", "about"),
            ("🧰 Что я умею", "skills"),
            ("❓ Частые вопросы", "faq"),
            ("📣 Канал и связь", "contacts"),
        ],
    },
    "about": {
        "text": (
            "<b>О боте</b>\n\n"
            "Меня зовут Тушёнка. Я простой бот-справочник: "
            "подсказываю ответы на частые вопросы и помогаю сориентироваться.\n\n"
            "Сделан на python-telegram-bot, живёт на Render."
        ),
        "buttons": [("⬅️ Назад", "root")],
    },
    "skills": {
        "text": (
            "<b>Что я умею</b>\n\n"
            "• Показываю меню с кнопками\n"
            "• Отвечаю на частые вопросы\n"
            "• Понимаю вопросы, написанные своими словами\n"
            "• Команды: /start, /menu, /help\n\n"
            "Функции будут расширяться."
        ),
        "buttons": [("❓ Частые вопросы", "faq"), ("⬅️ Назад", "root")],
    },
    "faq": {
        "text": "<b>Частые вопросы</b>\nВыберите тему:",
        "buttons": [
            ("Кто ты?", "q_who"),
            ("Что такое тушёнка?", "q_what"),
            ("Как тобой пользоваться?", "q_how"),
            ("Ты человек?", "q_bot"),
            ("⬅️ Назад", "root"),
        ],
    },
    "q_who": {
        "text": (
            "<b>Кто ты?</b>\n\n"
            "Я Тушёнка — Telegram-бот. Отвечаю на простые вопросы "
            "и помогаю найти нужную информацию."
        ),
        "buttons": [("⬅️ К вопросам", "faq"), ("🏠 В меню", "root")],
    },
    "q_what": {
        "text": (
            "<b>Что такое тушёнка?</b>\n\n"
            "Тушёнка — консервированное мясо (обычно говядина или свинина), "
            "приготовленное длительным тушением в собственном соку с жиром "
            "и специями. Хранится долго без холодильника — за это её и любят."
        ),
        "buttons": [("⬅️ К вопросам", "faq"), ("🏠 В меню", "root")],
    },
    "q_how": {
        "text": (
            "<b>Как тобой пользоваться?</b>\n\n"
            "1. Нажмите кнопку в меню — откроется ответ.\n"
            "2. Или напишите вопрос текстом: «привет», «как дела», «кто ты».\n"
            "3. Вернуться в начало — команда /menu или кнопка «В меню»."
        ),
        "buttons": [("⬅️ К вопросам", "faq"), ("🏠 В меню", "root")],
    },
    "q_bot": {
        "text": (
            "<b>Ты человек?</b>\n\n"
            "Нет, я программа. И, как видно по имени, из тушёнки 🥫"
        ),
        "buttons": [("⬅️ К вопросам", "faq"), ("🏠 В меню", "root")],
    },
    "contacts": {
        "text": (
            "<b>Канал и связь</b>\n\n"
            "Здесь можно оставить ссылку на ваш канал или контакт для связи.\n"
            "Отредактируйте текст в словаре MENU в файле bot.py."
        ),
        "buttons": [("⬅️ Назад", "root")],
    },
}

# ---------------------------------------------------------------------------
# Текстовые ответы: ключ — корень слова, ищется вхождением в сообщение.
# Побеждает самое длинное совпадение.
# ---------------------------------------------------------------------------
QA = {
    "привет": "Привет! Чем могу помочь? Меню — /menu",
    "здравствуй": "Здравствуйте! Задайте вопрос или откройте /menu",
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
    "что ты умеешь": (
        "Показываю меню с кнопками и отвечаю на частые вопросы. "
        "Откройте /menu — там всё по разделам."
    ),
    "ты бот": "Да, я бот. И, как видите, из тушёнки.",
    "что такое туш": "Тушёнка — консервированное мясо, обычно говядина или свинина.",
    "погода": "Прогноз я не смотрю — банки обычно не выходят на улицу.",
    "время": "Точное время лучше уточнить на устройстве: у меня нет часов.",
}

FALLBACK = (
    "Не понял вопрос 🤔\n\n"
    "Откройте /menu — там разделы с готовыми ответами. "
    "Или переформулируйте: «кто ты», «что такое тушёнка»."
)


def find_answer(text: str) -> str:
    lowered = text.lower().strip()
    best_key, best_answer = "", ""
    for key, answer in QA.items():
        if key in lowered and len(key) > len(best_key):
            best_key, best_answer = key, answer
    return best_answer or FALLBACK


def build_keyboard(screen: str) -> InlineKeyboardMarkup:
    """Собирает клавиатуру по два элемента в ряд (последний — если один, то во всю ширину)."""
    items = MENU[screen]["buttons"]
    rows, row = [], []
    for label, data in items:
        row.append(InlineKeyboardButton(label, callback_data=data))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


def screen_text(screen: str) -> str:
    return MENU[screen]["text"]


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        screen_text("root"),
        reply_markup=build_keyboard("root"),
        parse_mode="HTML",
    )


async def menu_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        screen_text("root"),
        reply_markup=build_keyboard("root"),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Команды:\n"
        "/start — запустить бота\n"
        "/menu — открыть меню\n"
        "/help — эта справка\n\n"
        "Можно и просто писать вопросы текстом.",
    )


async def on_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()  # убирает «часики» на кнопке

    screen = query.data if query.data in MENU else "root"
    try:
        await query.edit_message_text(
            screen_text(screen),
            reply_markup=build_keyboard(screen),
            parse_mode="HTML",
        )
    except Exception as exc:  # текст не изменился — Telegram не даёт отредактировать
        log.info("edit_message_text пропущен: %s", exc)


async def respond(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message or not update.message.text:
        return
    await update.message.reply_text(find_answer(update.message.text))


def build_application():
    app = ApplicationBuilder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CallbackQueryHandler(on_button))
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
        application.run_polling(
            allowed_updates=Update.ALL_TYPES, drop_pending_updates=True
        )

import re
from telegram import Update
from telegram.ext import ContextTypes
from yandex_parser import parse_yandex

YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.ru/maps/org/[^\s]+)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    match = YANDEX_URL_PATTERN.search(text)
    if match:
        url = match.group(1)
        await update.message.reply_text(f"Загружаю данные с {url}...")

        try:
            info = parse_yandex(url)
            # Формируем красивый ответ
            hours_text = "\n".join(f"  {day}: {hours}" for day, hours in info.get("hours", {}).items())
            response = (
                f"Название: {info.get('title')}\n"
                f"Рейтинг: {info.get('rating')}\n"
                f"Отзывы: {info.get('reviews')}\n"
                f"Координаты: {info.get('coordinates')}\n"
                f"Часы работы:\n{hours_text or '—'}"
            )
            await update.message.reply_text(response)
        except Exception as e:
            await update.message.reply_text(f"Ошибка при парсинге: {e}")
    else:
        await update.message.reply_text("Отправь ссылку на организацию в Яндекс.Картах 📍")

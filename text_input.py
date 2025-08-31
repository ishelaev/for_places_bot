import re
from telegram import Update
from telegram.ext import ContextTypes
from google_sheets_updater import update_google_sheets_with_yandex_data

YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.(?:ru|com)/maps/org/[^\s]+)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Отладочная информация
    print(f"Получено сообщение: '{text}'")
    print(f"Длина сообщения: {len(text)}")
    
    match = YANDEX_URL_PATTERN.search(text)
    print(f"Результат поиска ссылки: {match}")
    print(f"Регулярное выражение: {YANDEX_URL_PATTERN.pattern}")
    
    if match:
        url = match.group(1)
        await update.message.reply_text(f"Загружаю данные с {url}...")

        try:
            # Парсим данные и обновляем Google Sheets
            info = update_google_sheets_with_yandex_data(url)

            # Формируем красивый ответ пользователю
            hours_text = "\n".join(f"  {day}: {hours}" for day, hours in info.get("hours", {}).items())
            response = (
                f"Название: {info.get('title')}\n"
                f"Рейтинг: {info.get('rating')}\n"
                f"Отзывы: {info.get('reviews')}\n"
                f"Координаты: {info.get('coordinates')}\n"
                f"Часы работы:\n{hours_text or '—'}"
            )
            await update.message.reply_text(response)

            # Логирование: сообщаем о записи в Google Sheets
            await update.message.reply_text("✅ Данные успешно записаны в Google Sheets")
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обработке: {e}")
    else:
        await update.message.reply_text("Отправь ссылку на организацию в Яндекс.Картах 📍")

import re
from telegram import Update
from telegram.ext import ContextTypes
from google_sheets_updater import update_google_sheets_with_yandex_data

YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.(?:ru|com)/maps/org/[^\s]+)")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    match = YANDEX_URL_PATTERN.search(text)
    
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

            # Логирование: сообщаем о записи в Google Sheets с правильным сообщением
            google_sheets_url = "https://docs.google.com/spreadsheets/d/1w_jfZxc9yZS74-hRofIJfENd3ZqRUyE3Lh40TKVbLaI/edit#gid=0"
            
            action = info.get("_action", "unknown")
            if action == "updated":
                message = "🔄 Данные заведения обновлены в Google Sheets"
            elif action == "added":
                message = "✅ Новое заведение добавлено в Google Sheets"
            else:
                message = "✅ Данные успешно записаны в Google Sheets"
            
            await update.message.reply_text(
                f"{message}\n\n"
                f"📊 <a href='{google_sheets_url}'>Открыть таблицу</a>", 
                parse_mode='HTML'
            )
        except Exception as e:
            await update.message.reply_text(f"Ошибка при обработке: {e}")
    else:
        await update.message.reply_text("Отправь ссылку на организацию в Яндекс.Картах 📍")

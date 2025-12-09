# server_bot.py
import os
import re
import asyncio
import pytz
import pandas as pd
from pathlib import Path
from typing import Optional, Dict
from datetime import datetime
import shutil

# Устанавливаем timezone до импорта модулей, которые используют APScheduler
os.environ['TZ'] = 'Europe/Moscow'

# Патчим apscheduler.util для корректной работы с timezone
try:
    import apscheduler.util
    
    # Сохраняем оригинальную функцию
    original_astimezone = apscheduler.util.astimezone
    
    def patched_astimezone(tz):
        """Патч для astimezone, который конвертирует zoneinfo в pytz"""
        if tz is None:
            return pytz.timezone('Europe/Moscow')
        if isinstance(tz, pytz.BaseTzInfo):
            return tz
        # Если это zoneinfo или другой тип, конвертируем в pytz
        if hasattr(tz, 'key'):  # zoneinfo имеет key
            return pytz.timezone(tz.key)
        if hasattr(tz, 'zone'):  # pytz имеет zone
            return pytz.timezone(tz.zone)
        return pytz.timezone('Europe/Moscow')
    
    apscheduler.util.astimezone = patched_astimezone
    
    # Также патчим get_localzone в tzlocal до импорта telegram
    try:
        import tzlocal
        tzlocal.get_localzone = lambda: pytz.timezone('Europe/Moscow')
    except:
        pass
except Exception as e:
    print(f"Warning: Could not patch timezone utilities: {e}")

from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.error import TimedOut, NetworkError
from config import BOT_TOKEN, ADMIN_IDS
from database_manager import DatabaseManager
from yandex_parser import parse_yandex
from admin_commands import admin_stats, admin_export, admin_backup, admin_help, admin_sync, is_admin
from logger import setup_logger, log_parsing_result, log_admin_action

# Настройка логирования
logger = setup_logger()
db_manager = DatabaseManager()

# Путь для резервных копий
BACKUP_DIR = Path("/Users/ivan/Desktop/Резервные копии")
BACKUP_DIR.mkdir(parents=True, exist_ok=True)

# Счетчик запросов для резервных копий (будет храниться в bot_data)
BACKUP_INTERVAL = 10

# Регулярное выражение для ссылок Яндекс.Карт
YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.(?:ru|com)/maps/org/[^\s]+)")

def normalize_url(url: str) -> str:
	"""Нормализует URL для сравнения: убирает trailing slash, ID в конце, приводит к нижнему регистру."""
	if not url:
		return ""
	url = str(url).strip().lower()
	# Убираем trailing slash
	if url.endswith('/'):
		url = url[:-1]
	# Нормализуем домены (yandex.com и yandex.ru считаем одинаковыми для maps)
	url = url.replace('yandex.ru/maps', 'yandex.com/maps')
	# Убираем ID в конце URL (например, /190251394845)
	# Формат: https://yandex.com/maps/org/name/ID/
	url = re.sub(r'/\d+/?$', '', url)
	# Убираем trailing slash после удаления ID
	if url.endswith('/'):
		url = url[:-1]
	return url

def check_url_exists(url: str) -> tuple[bool, Optional[Dict]]:
	"""Проверяет наличие ссылки в базе данных или Excel. Возвращает (exists, place_data)."""
	try:
		# Нормализуем входящую ссылку
		normalized_url = normalize_url(url)
		
		# Проверяем в Excel файле (так как он используется основным ботом)
		excel_path = Path("/Users/ivan/Desktop/EatSpot_Bot_git/data/places.xlsx")
		if excel_path.exists():
			df = pd.read_excel(excel_path)
			if 'Ссылка' in df.columns:
				# Нормализуем все ссылки в таблице и сравниваем
				df_normalized = df['Ссылка'].astype(str).apply(normalize_url)
				mask = df_normalized == normalized_url
				if mask.any():
					idx = df[mask].index[0]
					return True, df.iloc[idx].to_dict()
		
		# Также проверяем в базе данных через db_manager
		place_data = db_manager.get_place_by_url(url)
		if place_data:
			# Проверяем нормализованную версию
			place_url_normalized = normalize_url(place_data.get('Ссылка', ''))
			if place_url_normalized == normalized_url:
				return True, place_data
		
		return False, None
	except Exception as e:
		logger.error(f"❌ Ошибка проверки ссылки: {e}")
		return False, None

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    
    # Символы, которые нужно экранировать в Markdown (убрали точки и дефисы - они не нужны)
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '=', '|', '{', '}', '!']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    welcome_message = (
        f"Привет, {user_name}! 👋\n\n"
        "Я бот для парсинга данных с Яндекс.Карт 📍\n\n"
        "**Как использовать:**\n"
        "1. Отправьте ссылку на организацию в Яндекс.Картах\n"
        "2. Я автоматически извлеку всю информацию\n"
        "3. Данные сохранятся в PostgreSQL базу данных\n"
        "4. И синхронизируются с локальным Excel файлом\n\n"
        "**Что я собираю:**\n"
        "• Название заведения\n"
        "• Рейтинг и отзывы\n"
        "• Координаты (широта/долгота)\n"
        "• Часы работы по дням недели\n"
        "• Категории заведения\n\n"
        "**Интеграция:**\n"
        "Данные автоматически доступны для основного бота EatSpot_Bot_git\n"
        "и синхронизируются с локальным Excel файлом\n\n"
        "Отправьте ссылку на Яндекс.Карты, чтобы начать! 🚀"
    )
    
    if is_admin(user_id):
        welcome_message += "\n\n🔧 Доступны административные команды: /help"
    
    await update.message.reply_text(welcome_message, parse_mode='Markdown')

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    try:
        text = update.message.text.strip()
        user_id = update.effective_user.id
        
        # Логируем входящее сообщение
        logger.info(f"📨 Сообщение от {user_id}: {text[:50]}...")
        
        # Ищем ссылку на Яндекс.Карты
        match = YANDEX_URL_PATTERN.search(text)
        
        if match:
            url = match.group(1)
            try:
                await update.message.reply_text(f"🔍 Проверяю ссылку в таблице…")
            except (TimedOut, NetworkError) as e:
                logger.warning(f"⚠️ Таймаут при отправке промежуточного сообщения: {e}")
                # Продолжаем обработку
            
            try:
                # ✅ СНАЧАЛА проверяем наличие ссылки в таблице
                url_exists, place_data = check_url_exists(url)
                
                if url_exists:
                    # Ссылка уже есть - быстро возвращаем простое сообщение
                    logger.info(f"✅ Ссылка уже есть в таблице: {url}")
                    try:
                        await update.message.reply_text("✅ Ссылка уже есть в таблице!")
                    except (TimedOut, NetworkError) as e:
                        logger.warning(f"⚠️ Таймаут при отправке ответа: {e}")
                    return
                
                # Ссылки нет - парсим данные (это долгая операция)
                try:
                    await update.message.reply_text(f"🔍 Парсю карточку… Это может занять до 20–30 сек.")
                except (TimedOut, NetworkError) as e:
                    logger.warning(f"⚠️ Таймаут при отправке промежуточного сообщения: {e}")
                
                # Парсим данные
                data = parse_yandex(url)
                
                # Обновляем PostgreSQL базу данных
                success, message = db_manager.update_place_data(url, data)
                
                if success:
                    # Логируем успешный результат
                    log_parsing_result(url, True, data)
                    
                    # Увеличиваем счетчик запросов и создаем резервную копию каждые 10 запросов
                    request_count = context.bot_data.get('request_count', 0) + 1
                    context.bot_data['request_count'] = request_count
                    
                    if request_count % BACKUP_INTERVAL == 0:
                        try:
                            # Создаем резервную копию Excel файла
                            excel_path = db_manager.excel_path
                            if excel_path.exists():
                                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                                backup_filename = f"places_backup_{timestamp}.xlsx"
                                backup_path = BACKUP_DIR / backup_filename
                                shutil.copy2(excel_path, backup_path)
                                logger.info(f"✅ Создана резервная копия: {backup_path} (запрос #{request_count})")
                        except Exception as e:
                            logger.error(f"❌ Ошибка создания резервной копии: {e}")
                    
                    # Формируем красивый ответ с экранированием
                    hours_text = ""
                    hours = data.get("hours", {})
                    if hours:
                        hours_lines = []
                        for day, time_range in hours.items():
                            hours_lines.append(f"  {day}: {time_range}")
                        hours_text = "\n".join(hours_lines)
                    
                    # Экранируем данные (координаты и время работы не экранируем - там не нужны обратные слеши)
                    title = escape_markdown(data.get('title', 'N/A'))
                    rating = escape_markdown(data.get('rating', 'N/A'))
                    reviews = escape_markdown(data.get('reviews', 'N/A'))
                    # Координаты оставляем без экранирования - форматируем вручную
                    coords = data.get('coordinates', 'N/A')
                    if coords != 'N/A' and isinstance(coords, tuple) and len(coords) == 2:
                        coordinates = f"{coords[0]}, {coords[1]}"
                    else:
                        coordinates = str(coords)
                    categories = escape_markdown(data.get('categories', 'N/A'))
                    escaped_message = escape_markdown(message)
                    
                    response = (
                        f"✅ **Данные успешно обработаны!**\n\n"
                        f"🏷 **Название:** {title}\n"
                        f"⭐ **Рейтинг:** {rating}\n"
                        f"💬 **Отзывы:** {reviews}\n"
                        f"📍 **Координаты:** {coordinates}\n"
                        f"🏪 **Категории:** {categories}\n"
                        f"🕐 **Часы работы:**\n{hours_text or '—'}\n\n"
                        f"📊 {escaped_message}\n\n"
                        f"🔄 Данные теперь доступны для основного бота!\n"
                        f"📁 Локальный Excel файл обновлен"
                    )
                    
                    try:
                        await update.message.reply_text(response, parse_mode='Markdown')
                    except (TimedOut, NetworkError) as e:
                        logger.warning(f"⚠️ Таймаут при отправке результата: {e}")
                        # Пытаемся отправить без Markdown
                        try:
                            await update.message.reply_text(response.replace('*', '').replace('_', ''))
                        except:
                            logger.error(f"❌ Не удалось отправить результат даже без Markdown")
                    
                else:
                    # Логируем ошибку
                    log_parsing_result(url, False, error=message)
                    try:
                        await update.message.reply_text(f"❌ {escape_markdown(message)}")
                    except (TimedOut, NetworkError) as e:
                        logger.warning(f"⚠️ Таймаут при отправке ошибки: {e}")
                
            except Exception as e:
                error_msg = f"Ошибка при обработке ссылки: {e}"
                log_parsing_result(url, False, error=error_msg)
                logger.error(f"❌ {error_msg}", exc_info=e)
                try:
                    await update.message.reply_text(f"❌ {escape_markdown(error_msg)}")
                except (TimedOut, NetworkError) as send_err:
                    logger.warning(f"⚠️ Таймаут при отправке сообщения об ошибке: {send_err}")
        else:
            # Если это не ссылка, предлагаем помощь
            help_text = (
            "📝 **Отправьте ссылку на Яндекс.Карты**\n\n"
            "Пример: `https://yandex\\.ru/maps/org/\\.\\.\\.`\n\n"
            "Я автоматически извлеку всю информацию о заведении и сохраню в PostgreSQL базу данных, которая используется основным ботом EatSpot_Bot_git, а также синхронизирую с локальным Excel файлом."
        )
        
        if is_admin(user_id):
            help_text += "\n\n🔧 Админ\\-команды: /help"
        
        try:
            await update.message.reply_text(help_text, parse_mode='Markdown')
        except (TimedOut, NetworkError) as e:
            logger.warning(f"⚠️ Таймаут при отправке справки: {e}")
            try:
                await update.message.reply_text(help_text.replace('*', '').replace('_', ''))
            except:
                logger.error(f"❌ Не удалось отправить справку")
    except Exception as e:
        logger.error(f"❌ Критическая ошибка в handle_text: {e}", exc_info=e)

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус бота"""
    user_id = update.effective_user.id
    
    try:
        places_count = db_manager.get_places_count()
        recent_places = db_manager.get_recent_places(3)
        local_excel_exists = db_manager.local_excel_path.exists()
        
        status_message = (
            f"🤖 **Статус бота**\n\n"
            f"✅ Бот работает\n"
            f"📍 Мест в базе: {places_count}\n"
            f"🗄 База данных: PostgreSQL\n"
            f"📊 Локальный Excel: {'✅' if local_excel_exists else '❌'}\n"
            f"🆔 Ваш ID: `{user_id}`"
        )
        
        if recent_places:
            status_message += "\n\n📋 **Последние добавления:**\n"
            for place in recent_places:
                name = escape_markdown(place.get('Название', 'N/A')[:30])
                status_message += f"• {name}\n"
        
        if is_admin(user_id):
            status_message += "\n\n🔧 Вы администратор"
        
        await update.message.reply_text(status_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении статуса: {escape_markdown(str(e))}")

async def recent(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает последние добавленные места"""
    try:
        recent_places = db_manager.get_recent_places(10)
        
        if not recent_places:
            await update.message.reply_text("📭 База данных пуста")
            return
        
        message = "📋 **Последние добавленные места:**\n\n"
        
        for i, place in enumerate(recent_places, 1):
            name = escape_markdown(place.get('Название', 'N/A'))
            rating = escape_markdown(place.get('Рейтинг', 'N/A'))
            categories = escape_markdown(place.get('Категории', 'N/A'))
            
            message += (
                f"{i}\\. **{name}**\n"
                f"   ⭐ {rating} \\| 🏪 {categories}\n\n"
            )
        
        await update.message.reply_text(message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении списка: {escape_markdown(str(e))}")

def main():
    """Основная функция запуска бота"""
    logger.info("🚀 Запуск серверного бота для PostgreSQL...")
    
    # Проверяем администраторов
    logger.info(f"🔧 Администраторы: {ADMIN_IDS}")
    
    # Создаем приложение
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Регистрируем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("recent", recent))
    
    # Административные команды
    app.add_handler(CommandHandler("stats", admin_stats))
    app.add_handler(CommandHandler("sync", admin_sync))
    app.add_handler(CommandHandler("export", admin_export))
    app.add_handler(CommandHandler("backup", admin_backup))
    app.add_handler(CommandHandler("help", admin_help))
    
    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info(f"🔧 Администраторы: {ADMIN_IDS}")
    logger.info("🗄 Подключение к PostgreSQL: 109.69.56.200:5432/places")
    logger.info(f"📁 Локальный Excel: {db_manager.excel_path}")

    # Обработчик ошибок
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
        """Обработчик ошибок"""
        err = context.error
        if isinstance(err, TimedOut):
            logger.warning("⚠️ Таймаут при отправке сообщения - продолжаем работу")
            return
        if isinstance(err, NetworkError):
            logger.warning(f"⚠️ Ошибка сети: {err} - продолжаем работу")
            return
        logger.error(f"❌ Необработанная ошибка: {err}", exc_info=err)
    
    app.add_error_handler(error_handler)
    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()

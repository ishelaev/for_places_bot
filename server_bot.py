# server_bot.py
import os
import pytz

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

import re
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS
from database_manager import DatabaseManager
from yandex_parser import parse_yandex
from admin_commands import admin_stats, admin_export, admin_backup, admin_help, admin_sync, admin_instagram_search, admin_instagram_stats, is_admin
from logger import setup_logger, log_parsing_result, log_admin_action
import sys
from pathlib import Path

# Настройка логирования
logger = setup_logger()

# Добавляем путь к модулю поиска Instagram
sys.path.insert(0, str(Path(__file__).parent / "Inst"))
try:
    from find_instagram import find_instagram_via_google
    INSTAGRAM_SEARCH_AVAILABLE = True
except ImportError as e:
    logger.warning(f"⚠️ Не удалось импортировать модуль поиска Instagram: {e}")
    INSTAGRAM_SEARCH_AVAILABLE = False

db_manager = DatabaseManager()

# Регулярное выражение для ссылок Яндекс.Карт
YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.(?:ru|com)/maps/org/[^\s]+)")

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    
    # В Markdown нужно экранировать специальные символы
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '!', '.']
    
    for char in special_chars:
        text = text.replace(char, f'\\{char}')
    
    return text

def escape_markdown_url(url: str) -> str:
    """Экранирует URL для Markdown, но сохраняет его кликабельным"""
    if not url:
        return url
    # В Markdown URL нужно экранировать только некоторые символы
    # Но лучше использовать формат [текст](url)
    return url.replace('_', '\\_').replace('.', '\\.')

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
    text = update.message.text.strip()
    user_id = update.effective_user.id
    
    # Логируем входящее сообщение
    logger.info(f"📨 Сообщение от {user_id}: {text[:50]}...")
    
    # Ищем ссылку на Яндекс.Карты
    match = YANDEX_URL_PATTERN.search(text)
    
    if match:
        url = match.group(1)
        await update.message.reply_text(f"🔍 Обрабатываю ссылку: {url}")
        
        try:
            # Парсим данные
            loop = asyncio.get_event_loop()
            data = await loop.run_in_executor(None, parse_yandex, url)
            
            # Ищем Instagram (если модуль доступен)
            if INSTAGRAM_SEARCH_AVAILABLE:
                try:
                    # Используем уже распарсенные данные для поиска Instagram
                    name = data.get('title', '')
                    city = "Москва"
                    categories = data.get('categories')
                    
                    if name and name != "Название не найдено":
                        logger.info(f"🔍 Ищу Instagram для: {name} (категории: {categories})")
                        from functools import partial
                        # Используем verbose=False, чтобы не засорять логи бота
                        try:
                            instagram_url = await loop.run_in_executor(
                                None, partial(find_instagram_via_google, name, city, categories, False)
                            )
                            logger.info(f"🔍 Результат поиска Instagram: {instagram_url}")
                            if instagram_url:
                                data['instagram'] = instagram_url
                                logger.info(f"✅ Найден Instagram: {instagram_url}")
                            else:
                                data['instagram'] = None
                                logger.warning(f"❌ Instagram не найден для: {name}")
                        except Exception as search_error:
                            logger.error(f"❌ Ошибка при выполнении поиска Instagram: {search_error}")
                            import traceback
                            logger.error(traceback.format_exc())
                            data['instagram'] = None
                    else:
                        data['instagram'] = None
                        logger.warning(f"⚠️ Не могу искать Instagram: название не найдено")
                except Exception as e:
                    logger.error(f"❌ Ошибка при поиске Instagram: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    data['instagram'] = None
            else:
                logger.warning("⚠️ Модуль поиска Instagram недоступен")
                data['instagram'] = None
            
            # Логируем финальное значение Instagram перед сохранением
            logger.info(f"📊 Instagram перед сохранением: {data.get('instagram', 'не указан')}")
            
            # Обновляем PostgreSQL базу данных
            success, message, action = await loop.run_in_executor(
                None, db_manager.update_place_data, url, data
            )
            
            if success:
                # Логируем успешный результат
                log_parsing_result(url, True, data)
                
                # Проверяем, была ли запись уже в базе
                is_existing = (action == "обновлена")
                
                # Формируем красивый ответ
                hours_text = ""
                hours = data.get("hours", {})
                if hours:
                    hours_lines = []
                    for day, time_range in hours.items():
                        hours_lines.append(f"  {day}: {time_range}")
                    hours_text = "\n".join(hours_lines)
                
                # Получаем данные без лишнего экранирования
                title = data.get('title', 'N/A')
                rating = data.get('rating', 'N/A')
                reviews = data.get('reviews', 'N/A')
                coordinates = data.get('coordinates', 'N/A')
                if isinstance(coordinates, tuple) and len(coordinates) == 2:
                    coordinates = f"({coordinates[0]}, {coordinates[1]})"
                categories = data.get('categories', 'N/A')
                
                # Если ссылка уже есть - отправляем сообщение, но Instagram все равно обновлен
                if is_existing:
                    from html import escape as html_escape
                    instagram_info = ""
                    if data.get('instagram'):
                        instagram_url = data.get('instagram')
                        instagram_info = f"\n📸 <b>Instagram обновлен:</b> <a href=\"{instagram_url}\">{html_escape(instagram_url)}</a>"
                    await update.message.reply_text(
                        f"⚠️ <b>Такая ссылка уже есть в базе данных!</b>{instagram_info}",
                        parse_mode='HTML'
                    )
                    return
                
                # Формируем полный ответ для новой записи
                # Используем HTML для более надежного форматирования
                from html import escape as html_escape
                
                title_escaped = html_escape(str(title))
                rating_escaped = html_escape(str(rating))
                reviews_escaped = html_escape(str(reviews))
                coordinates_escaped = html_escape(str(coordinates))
                categories_escaped = html_escape(str(categories))
                
                instagram_info = ""
                if data.get('instagram'):
                    instagram_url = data.get('instagram')
                    # В HTML используем тег <a> для ссылок
                    instagram_info = f"📸 <b>Instagram:</b> <a href=\"{instagram_url}\">{html_escape(instagram_url)}</a>\n"
                elif data.get('instagram') is None:
                    instagram_info = "📸 <b>Instagram:</b> не найден\n"
                
                # Экранируем часы работы
                hours_text_escaped = ""
                if hours_text:
                    hours_lines = []
                    for line in hours_text.split('\n'):
                        if line.strip():
                            hours_lines.append(html_escape(line))
                    hours_text_escaped = "\n".join(hours_lines)
                
                response = (
                    f"✅ <b>Данные успешно обработаны!</b>\n\n"
                    f"🏷 <b>Название:</b> {title_escaped}\n"
                    f"⭐ <b>Рейтинг:</b> {rating_escaped}\n"
                    f"💬 <b>Отзывы:</b> {reviews_escaped}\n"
                    f"📍 <b>Координаты:</b> {coordinates_escaped}\n"
                    f"🏪 <b>Категории:</b> {categories_escaped}\n"
                    f"{instagram_info}"
                    f"🕐 <b>Часы работы:</b>\n{hours_text_escaped or '—'}\n\n"
                    f"📊 {html_escape(message)}\n\n"
                    f"🔄 Данные теперь доступны для основного бота!\n"
                    f"📁 Локальный Excel файл обновлен"
                )
                
                await update.message.reply_text(response, parse_mode='HTML')
                
            else:
                # Логируем ошибку
                log_parsing_result(url, False, error=message)
                await update.message.reply_text(f"❌ {message}")
                
        except Exception as e:
            error_msg = f"Ошибка при обработке ссылки: {e}"
            log_parsing_result(url, False, error=error_msg)
            await update.message.reply_text(f"❌ {error_msg}")
            
    else:
        # Если это не ссылка, предлагаем помощь
        help_text = (
            "📝 **Отправьте ссылку на Яндекс.Карты**\n\n"
            "Пример: `https://yandex\\.ru/maps/org/\\.\\.\\.`\n\n"
            "Я автоматически извлеку всю информацию о заведении и сохраню в PostgreSQL базу данных, которая используется основным ботом EatSpot_Bot_git, а также синхронизирую с локальным Excel файлом."
        )
        
        if is_admin(user_id):
            help_text += "\n\n🔧 Админ\\-команды: /help"
        
        await update.message.reply_text(help_text, parse_mode='Markdown')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статус бота"""
    user_id = update.effective_user.id
    
    try:
        places_count = db_manager.get_places_count()
        recent_places = db_manager.get_recent_places(3)
        local_excel_exists = db_manager.excel_path.exists()
        
        # Статистика Instagram
        instagram_stats = db_manager.get_instagram_stats()
        instagram_info = ""
        if instagram_stats:
            instagram_info = (
                f"\n📸 Instagram: {instagram_stats.get('with_instagram', 0)}/{instagram_stats.get('total_places', 0)} "
                f"\\({instagram_stats.get('percentage', 0)}%\\)"
            )
        
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
    
    # Instagram команды
    app.add_handler(CommandHandler("instagram_search", admin_instagram_search))
    app.add_handler(CommandHandler("instagram_stats", admin_instagram_stats))
    
    # Обработчик текстовых сообщений
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    logger.info("✅ Бот запущен и готов к работе!")
    logger.info(f"🔧 Администраторы: {ADMIN_IDS}")
    logger.info("🗄 Подключение к PostgreSQL: 109.69.56.200:5432/places")
    logger.info(f"📁 Локальный Excel: {db_manager.excel_path}")

    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()

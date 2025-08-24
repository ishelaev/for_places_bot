# server_bot.py
import re
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
from config import BOT_TOKEN, ADMIN_IDS
from database_manager import DatabaseManager
from yandex_parser import parse_yandex
from admin_commands import admin_stats, admin_export, admin_backup, admin_help, admin_sync, admin_instagram_search, admin_instagram_stats, is_admin
from logger import setup_logger, log_parsing_result, log_admin_action

# Настройка логирования
logger = setup_logger()
db_manager = DatabaseManager()

# Регулярное выражение для ссылок Яндекс.Карт
YANDEX_URL_PATTERN = re.compile(r"(https?://yandex\.(?:ru|com)/maps/org/[^\s]+)")

def escape_markdown(text: str) -> str:
    """Экранирует специальные символы для Markdown"""
    if not text:
        return text
    
    # Символы, которые нужно экранировать в Markdown
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    
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
            data = parse_yandex(url)
            
            # Обновляем PostgreSQL базу данных
            success, message = db_manager.update_place_data(url, data)
            

            
            if success:
                # Логируем успешный результат
                log_parsing_result(url, True, data)
                
                # Формируем красивый ответ с экранированием
                hours_text = ""
                hours = data.get("hours", {})
                if hours:
                    hours_lines = []
                    for day, time_range in hours.items():
                        escaped_day = escape_markdown(day)
                        escaped_time = escape_markdown(str(time_range))
                        hours_lines.append(f"  {escaped_day}: {escaped_time}")
                    hours_text = "\n".join(hours_lines)
                
                # Экранируем все данные
                title = escape_markdown(data.get('title', 'N/A'))
                rating = escape_markdown(data.get('rating', 'N/A'))
                reviews = escape_markdown(data.get('reviews', 'N/A'))
                coordinates = escape_markdown(str(data.get('coordinates', 'N/A')))
                categories = escape_markdown(data.get('categories', 'N/A'))
                escaped_message = escape_markdown(message)
                

                
                response = (
                    f"✅ **Данные успешно обработаны!**\n\n"
                    f"🏷 **Название:** {title}\n"
                    f"⭐ **Рейтинг:** {rating}\n"
                    f"💬 **Отзывы:** {reviews}\n"
                    f"📍 **Координаты:** {coordinates}\n"
                    f"🏪 **Категории:** {categories}\n\n"
                    f"🕐 **Часы работы:**\n{hours_text or '—'}\n\n"
                    f"📊 {escaped_message}\n\n"
                    f"🔄 Данные теперь доступны для основного бота!\n"
                    f"📁 Локальный Excel файл обновлен"
                )
                
                await update.message.reply_text(response, parse_mode='Markdown')
                
            else:
                # Логируем ошибку
                log_parsing_result(url, False, error=message)
                await update.message.reply_text(f"❌ {escape_markdown(message)}")
                
        except Exception as e:
            error_msg = f"Ошибка при обработке ссылки: {e}"
            log_parsing_result(url, False, error=error_msg)
            await update.message.reply_text(f"❌ {escape_markdown(error_msg)}")
            
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
        local_excel_exists = db_manager.local_excel_path.exists()
        
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
    logger.info(f"📁 Локальный Excel: {db_manager.local_excel_path}")

    
    # Запускаем бота
    app.run_polling()

if __name__ == "__main__":
    main()

# admin_commands.py
from telegram import Update
from telegram.ext import ContextTypes
from config import ADMIN_IDS
from database_manager import DatabaseManager
from instagram_parser import InstagramParser
from logger import log_admin_action, setup_logger
import pandas as pd

logger = setup_logger()
db_manager = DatabaseManager()
instagram_parser = InstagramParser()

def is_admin(user_id: int) -> bool:
    """Проверяет, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику бота"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "запросил статистику")
    
    try:
        places_count = db_manager.get_places_count()
        all_places = db_manager.get_all_places()
        
        # Статистика по категориям
        categories_stats = ""
        categories = [place.get('Категории') for place in all_places if place.get('Категории')]
        if categories:
            from collections import Counter
            category_counts = Counter(categories).most_common(5)
            categories_stats = "\n📊 Топ категорий:\n"
            for category, count in category_counts:
                categories_stats += f"  • {category}: {count}\n"
        
        # Статистика по рейтингам
        rating_stats = ""
        ratings = [place.get('Рейтинг') for place in all_places if place.get('Рейтинг')]
        if ratings:
            try:
                # Пытаемся извлечь числовые рейтинги
                numeric_ratings = []
                for rating in ratings:
                    if isinstance(rating, str) and rating.replace('.', '').isdigit():
                        numeric_ratings.append(float(rating))
                
                if numeric_ratings:
                    avg_rating = sum(numeric_ratings) / len(numeric_ratings)
                    rating_stats = f"\n⭐ Средний рейтинг: {avg_rating:.1f}"
            except:
                pass
        
        # Статистика по Instagram
        instagram_stats = db_manager.get_instagram_stats()
        instagram_info = ""
        if instagram_stats:
            instagram_info = (
                f"\n📸 **Instagram статистика:**\n"
                f"  • Всего мест: {instagram_stats.get('total_places', 0)}\n"
                f"  • С Instagram: {instagram_stats.get('with_instagram', 0)}\n"
                f"  • Без Instagram: {instagram_stats.get('without_instagram', 0)}\n"
                f"  • Покрытие: {instagram_stats.get('percentage', 0)}%"
            )
        
        # Статистика по последним местам
        recent_places = db_manager.get_recent_places(5)
        recent_stats = ""
        if recent_places:
            recent_stats = "\n📅 Последние добавления:\n"
            for place in recent_places:
                name = place.get('Название', 'N/A')[:25]
                url = place.get('Ссылка', 'N/A')[:30]
                recent_stats += f"  • {name}\n    {url}\n"
        
        # Информация о синхронизации
        local_excel_exists = db_manager.local_excel_path.exists()
        sync_status = "✅ Синхронизирован" if local_excel_exists else "❌ Не синхронизирован"
        
        # Статистика чёрного списка Instagram
        blacklist_stats = instagram_parser.get_blacklist_stats()
        blacklist_info = (
            f"\n🚫 **Instagram чёрный список:**\n"
            f"  • Всего: {blacklist_stats.get('total_count', 0)}\n"
            f"  • Базовых: {blacklist_stats.get('base_count', 0)}\n"
            f"  • Пользовательских: {blacklist_stats.get('custom_count', 0)}"
        )
        
        stats_message = (
            f"📈 **Статистика бота**\n\n"
            f"📍 Всего мест: {places_count}\n"
            f"🗄 База данных: PostgreSQL\n"
            f"🌐 Сервер: 109.69.56.200:5432/places\n"
            f"📊 Локальный Excel: {sync_status}\n"
            f"📁 Путь: `{db_manager.local_excel_path}`\n"
            f"{rating_stats}"
            f"{categories_stats}"
            f"{instagram_info}"
            f"{blacklist_info}"
            f"{recent_stats}"
        )
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении статистики: {e}")

async def admin_instagram_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Запускает поиск Instagram для мест без Instagram"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "запустил поиск Instagram")
    
    try:
        # Получаем места без Instagram
        places_without_instagram = db_manager.get_places_without_instagram(limit=10)
        
        if not places_without_instagram:
            await update.message.reply_text("✅ Все места уже имеют Instagram!")
            return
        
        await update.message.reply_text(
            f"🔍 Начинаю поиск Instagram для {len(places_without_instagram)} мест...\n"
            f"Это может занять несколько минут."
        )
        
        # Запускаем поиск
        results = instagram_parser.batch_process_places(places_without_instagram, max_count=10)
        
        if results:
            # Обновляем базу данных
            updated_count = 0
            for place_name, instagram_url in results.items():
                if db_manager.update_instagram_for_place(place_name, instagram_url):
                    updated_count += 1
            
            await update.message.reply_text(
                f"✅ Поиск Instagram завершен!\n\n"
                f"📊 Результаты:\n"
                f"  • Обработано мест: {len(places_without_instagram)}\n"
                f"  • Найдено Instagram: {len(results)}\n"
                f"  • Обновлено в базе: {updated_count}\n\n"
                f"📸 Найденные Instagram:\n" +
                "\n".join([f"  • {name}: {url}" for name, url in results.items()])
            )
        else:
            await update.message.reply_text(
                "❌ Instagram не найден для обработанных мест.\n"
                "Возможно, они добавлены в чёрный список."
            )
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при поиске Instagram: {e}")

async def admin_instagram_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает статистику по Instagram"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "запросил статистику Instagram")
    
    try:
        instagram_stats = db_manager.get_instagram_stats()
        blacklist_stats = instagram_parser.get_blacklist_stats()
        
        if not instagram_stats:
            await update.message.reply_text("❌ Не удалось получить статистику Instagram")
            return
        
        stats_message = (
            f"📸 **Instagram статистика**\n\n"
            f"📍 Всего мест: {instagram_stats.get('total_places', 0)}\n"
            f"✅ С Instagram: {instagram_stats.get('with_instagram', 0)}\n"
            f"❌ Без Instagram: {instagram_stats.get('without_instagram', 0)}\n"
            f"📊 Покрытие: {instagram_stats.get('percentage', 0)}%\n\n"
            f"🚫 **Чёрный список:**\n"
            f"  • Всего записей: {blacklist_stats.get('total_count', 0)}\n"
            f"  • Базовых: {blacklist_stats.get('base_count', 0)}\n"
            f"  • Пользовательских: {blacklist_stats.get('custom_count', 0)}\n"
            f"  • Файл: `{blacklist_stats.get('file_path', 'N/A')}`"
        )
        
        await update.message.reply_text(stats_message, parse_mode='Markdown')
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при получении статистики Instagram: {e}")

async def admin_sync(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Принудительная синхронизация с локальным Excel файлом"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "запросил синхронизацию Excel")
    
    try:
        await update.message.reply_text("🔄 Начинаю синхронизацию с локальным Excel файлом...")
        
        success = db_manager.force_sync_excel()
        
        if success:
            places_count = db_manager.get_places_count()
            await update.message.reply_text(
                f"✅ Синхронизация завершена!\n"
                f"📊 Записей синхронизировано: {places_count}\n"
                f"📁 Файл: `{db_manager.local_excel_path}`",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ Ошибка при синхронизации")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при синхронизации: {e}")

async def admin_export(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Экспортирует данные в CSV"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "запросил экспорт данных")
    
    try:
        all_places = db_manager.get_all_places()
        if not all_places:
            await update.message.reply_text("📭 База данных пуста")
            return
        
        # Создаем DataFrame
        df = pd.DataFrame(all_places)
        
        # Создаем временный CSV файл
        csv_path = db_manager.excel_path.parent / "places_export.csv"
        df.to_csv(csv_path, index=False, encoding='utf-8')
        
        # Отправляем файл
        with open(csv_path, 'rb') as file:
            await update.message.reply_document(
                document=file,
                filename="places_export.csv",
                caption="📊 Экспорт данных из PostgreSQL"
            )
        
        # Удаляем временный файл
        csv_path.unlink()
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при экспорте: {e}")

async def admin_backup(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Создает резервную копию базы данных"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    user_id = update.effective_user.id
    log_admin_action(user_id, "создал резервную копию")
    
    try:
        from datetime import datetime
        
        # Создаем имя для бэкапа
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = db_manager.excel_path.parent / f"places_backup_{timestamp}.xlsx"
        
        # Получаем все данные
        all_places = db_manager.get_all_places()
        if all_places:
            df = pd.DataFrame(all_places)
            df.to_excel(backup_path, index=False)
            
            await update.message.reply_text(
                f"✅ Резервная копия создана:\n`{backup_path.name}`\n"
                f"📊 Записей: {len(all_places)}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("📭 База данных пуста, бэкап не создан")
        
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка при создании бэкапа: {e}")

async def admin_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает справку по административным командам"""
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("❌ У вас нет прав администратора")
        return
    
    help_text = (
        "🔧 **Административные команды**\n\n"
        "/stats - Показать статистику бота и базы данных\n"
        "/sync - Принудительная синхронизация с локальным Excel\n"
        "/export - Экспортировать данные в CSV\n"
        "/backup - Создать резервную копию\n"
        "/help - Показать эту справку\n\n"
        "📸 **Instagram команды**\n"
        "/instagram_search - Поиск Instagram для мест без Instagram\n"
        "/instagram_stats - Статистика по Instagram\n\n"
        "📝 **Обычные команды**\n"
        "/start - Запустить бота\n"
        "/status - Статус бота\n"
        "/recent - Последние добавленные места\n"
        "Отправьте ссылку на Яндекс.Карты для парсинга\n\n"
        "🗄 **Интеграция с EatSpot_Bot_git**\n"
        "Данные автоматически сохраняются в PostgreSQL\n"
        "и синхронизируются с локальным Excel файлом"
    )
    
    await update.message.reply_text(help_text, parse_mode='Markdown')

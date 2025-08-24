# logger.py
import logging
from datetime import datetime
from config import LOG_FILE, LOG_LEVEL

def setup_logger():
    """Настройка логирования"""
    logging.basicConfig(
        level=getattr(logging, LOG_LEVEL),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(LOG_FILE, encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger('ParserBot')

def log_parsing_result(url: str, success: bool, data: dict = None, error: str = None):
    """Логирование результата парсинга"""
    logger = logging.getLogger('ParserBot')
    
    if success:
        logger.info(f"✅ Успешно обработана ссылка: {url}")
        if data:
            logger.info(f"   Название: {data.get('title', 'N/A')}")
            logger.info(f"   Рейтинг: {data.get('rating', 'N/A')}")
            logger.info(f"   Отзывы: {data.get('reviews', 'N/A')}")
    else:
        logger.error(f"❌ Ошибка при обработке ссылки: {url}")
        if error:
            logger.error(f"   Ошибка: {error}")

def log_excel_update(url: str, action: str):
    """Логирование обновления Excel"""
    logger = logging.getLogger('ParserBot')
    logger.info(f"📊 Excel: {action} для ссылки {url}")

def log_admin_action(user_id: int, action: str):
    """Логирование действий администратора"""
    logger = logging.getLogger('ParserBot')
    logger.info(f"👤 Админ {user_id}: {action}")

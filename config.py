# config.py
import os
from pathlib import Path

# Пути к файлам
BASE_DIR = Path(__file__).parent
EXCEL_PATH = BASE_DIR / "data" / "places.xlsx"

# Telegram настройки
BOT_TOKEN = "8478245526:AAHAua7Xnr2CIt2xg_zjfaqk7HVPOCt2Nxw"

# Администраторы
ADMIN_IDS = [339143049]

# Настройки PostgreSQL
POSTGRES_CONFIG = {
    'host': '109.69.56.200',
    'port': 5432,
    'database': 'places',
    'user': 'root',
    'password': 'Aa446123789rm config.py'
}

# Строка подключения к PostgreSQL
POSTGRES_URL = f"postgresql+psycopg2://{POSTGRES_CONFIG['user']}:{POSTGRES_CONFIG['password']}@{POSTGRES_CONFIG['host']}:{POSTGRES_CONFIG['port']}/{POSTGRES_CONFIG['database']}"

# Настройки парсинга
PARSING_DELAY = 2
HEADLESS_MODE = True

# Настройки логирования
LOG_FILE = BASE_DIR / "logs" / "parser_bot.log"
LOG_LEVEL = "INFO"

# Создаем необходимые директории
os.makedirs(BASE_DIR / "data", exist_ok=True)
os.makedirs(BASE_DIR / "logs", exist_ok=True)

# 🚀 Развертывание Places Bot на сервере

Подробная инструкция по развертыванию Telegram бота для парсинга Яндекс.Карт на Linux сервере.

## 📋 Требования

### Системные требования
- **ОС**: Ubuntu 20.04+ / Debian 11+ / CentOS 8+
- **RAM**: минимум 1GB, рекомендуется 2GB
- **Диск**: минимум 2GB свободного места
- **Сеть**: постоянное интернет-соединение

### Необходимые аккаунты
- 🤖 **Telegram Bot Token** (получить у [@BotFather](https://t.me/botfather))
- 📊 **Google Sheets API** (Google Cloud Console)
- 🔑 **JSON ключ** для сервисного аккаунта Google

## ⚡ Быстрая установка

### 1. Подключение к серверу
```bash
ssh user@your-server-ip
```

### 2. Загрузка и запуск установочного скрипта
```bash
# Клонирование репозитория
git clone https://github.com/ishelaev/for_places_bot.git
cd for_places_bot

# Запуск установки
sudo chmod +x deploy_server.sh
sudo ./deploy_server.sh
```

### 3. Настройка конфигурации
```bash
# Переход в директорию бота
cd /opt/places_bot

# Создание .env файла
sudo -u placesbot cp env.example .env
sudo -u placesbot nano .env
```

**Заполните в .env файле:**
```env
BOT_TOKEN=ваш_telegram_bot_token
SPREADSHEET_ID=ваш_google_spreadsheet_id
```

### 4. Настройка Google Sheets API
```bash
# Скопируйте JSON ключ в папку проекта
sudo -u placesbot nano /opt/places_bot/service-account-key.json
# Вставьте содержимое JSON файла
```

### 5. Установка и запуск сервиса
```bash
# Установка systemd сервиса
sudo ./manage_bot.sh install

# Запуск бота
sudo ./manage_bot.sh start

# Проверка статуса
sudo ./manage_bot.sh status
```

## 🔧 Ручная установка (детально)

### Шаг 1: Обновление системы
```bash
sudo apt update && sudo apt upgrade -y
```

### Шаг 2: Установка зависимостей
```bash
# Основные пакеты
sudo apt install -y python3 python3-pip python3-venv git wget curl unzip

# Google Chrome
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
sudo apt update
sudo apt install -y google-chrome-stable

# ChromeDriver
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%%.*}")
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
sudo unzip /tmp/chromedriver.zip -d /usr/local/bin/
sudo chmod +x /usr/local/bin/chromedriver
```

### Шаг 3: Создание пользователя
```bash
sudo useradd -m -s /bin/bash placesbot
sudo mkdir -p /opt/places_bot
sudo chown placesbot:placesbot /opt/places_bot
```

### Шаг 4: Клонирование и настройка проекта
```bash
cd /opt/places_bot
sudo -u placesbot git clone https://github.com/ishelaev/for_places_bot.git .

# Создание виртуального окружения
sudo -u placesbot python3 -m venv venv
sudo -u placesbot ./venv/bin/pip install --upgrade pip
sudo -u placesbot ./venv/bin/pip install -r requirements.txt

# Создание директорий
sudo -u placesbot mkdir -p logs data backups/excel backups/json backups/csv
```

## 🎛️ Управление ботом

### Основные команды
```bash
# Статус бота
sudo ./manage_bot.sh status

# Запуск/остановка
sudo ./manage_bot.sh start
sudo ./manage_bot.sh stop
sudo ./manage_bot.sh restart

# Просмотр логов
sudo ./manage_bot.sh logs

# Обновление кода
sudo ./manage_bot.sh update
```

### Мониторинг
```bash
# Журнал systemd
sudo journalctl -u places-bot -f

# Логи приложения
tail -f /opt/places_bot/logs/bot.log
tail -f /opt/places_bot/logs/bot_error.log

# Использование ресурсов
htop
ps aux | grep python
```

## 🔐 Настройка Google Sheets API

### 1. Создание проекта в Google Cloud Console
1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Включите Google Sheets API

### 2. Создание сервисного аккаунта
1. Перейдите в "IAM & Admin" > "Service Accounts"
2. Нажмите "Create Service Account"
3. Заполните имя и описание
4. Нажмите "Create and Continue"

### 3. Создание ключа
1. Нажмите на созданный сервисный аккаунт
2. Перейдите в "Keys" > "Add Key" > "Create New Key"
3. Выберите JSON формат
4. Скачайте файл

### 4. Предоставление доступа к таблице
1. Откройте вашу Google Таблицу
2. Нажмите "Share" (Поделиться)
3. Добавьте email сервисного аккаунта как редактора

## 🔧 Конфигурация

### Файл .env
```env
# Обязательные параметры
BOT_TOKEN=your_telegram_bot_token_here
SPREADSHEET_ID=your_google_spreadsheet_id_here

# Опциональные параметры
LOG_LEVEL=INFO
BACKUP_ENABLED=true
MAX_BACKUPS=10
PARSING_TIMEOUT=30
```

### Расположение файлов
```
/opt/places_bot/
├── main.py                 # Главный файл бота
├── requirements.txt        # Python зависимости
├── .env                   # Конфигурация
├── service-account-key.json # Google API ключ
├── logs/                  # Логи
├── backups/              # Резервные копии
└── venv/                 # Виртуальное окружение
```

## 🚨 Устранение неполадок

### Бот не запускается
```bash
# Проверьте логи
sudo journalctl -u places-bot -n 50

# Проверьте конфигурацию
sudo -u placesbot /opt/places_bot/venv/bin/python -c "import main"

# Проверьте права доступа
ls -la /opt/places_bot/
```

### Ошибки парсинга
```bash
# Проверьте Chrome
google-chrome --version
chromedriver --version

# Тест парсинга
sudo -u placesbot /opt/places_bot/venv/bin/python -c "
from yandex_parser import parse_yandex
result = parse_yandex('https://yandex.ru/maps/org/test/123/')
print(result)
"
```

### Проблемы с Google Sheets
```bash
# Проверьте JSON ключ
sudo -u placesbot cat /opt/places_bot/service-account-key.json

# Тест подключения
sudo -u placesbot /opt/places_bot/venv/bin/python -c "
from google_sheets_manager import GoogleSheetsManager
gsm = GoogleSheetsManager()
print('Google Sheets подключение:', gsm.client is not None)
"
```

## 📊 Мониторинг и логи

### Структура логов
- `logs/bot.log` - основные логи приложения
- `logs/bot_error.log` - ошибки приложения
- `journalctl -u places-bot` - системные логи

### Автоматические резервные копии
- Создаются в `backups/excel/`
- Содержат все данные из Google Sheets
- Автоматическая ротация (сохраняются последние 10)

## 🔄 Обновление

### Автоматическое обновление
```bash
sudo ./manage_bot.sh update
```

### Ручное обновление
```bash
sudo systemctl stop places-bot
cd /opt/places_bot
sudo -u placesbot git pull origin main
sudo -u placesbot ./venv/bin/pip install -r requirements.txt --upgrade
sudo systemctl start places-bot
```

## 🛡️ Безопасность

### Рекомендации
- Используйте firewall (ufw/iptables)
- Регулярно обновляйте систему
- Ограничьте SSH доступ
- Используйте сильные пароли
- Настройте fail2ban

### Права доступа
```bash
# Проверка прав
ls -la /opt/places_bot/
# Владелец должен быть placesbot:placesbot

# Исправление прав при необходимости
sudo chown -R placesbot:placesbot /opt/places_bot/
sudo chmod 600 /opt/places_bot/.env
sudo chmod 600 /opt/places_bot/service-account-key.json
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `sudo ./manage_bot.sh logs`
2. Проверьте статус: `sudo ./manage_bot.sh status`
3. Перезапустите бота: `sudo ./manage_bot.sh restart`

Если проблема не решается, создайте issue в [GitHub репозитории](https://github.com/ishelaev/for_places_bot/issues).

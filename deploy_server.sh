#!/bin/bash

# Скрипт развертывания Places Bot на сервере
# Запускать с правами sudo

echo "🚀 Начинаем развертывание Places Bot на сервере..."

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Функция для вывода
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Проверка прав root
if [ "$EUID" -ne 0 ]; then
    print_error "Запустите скрипт с правами sudo"
    exit 1
fi

# Обновление системы
print_status "Обновление системы..."
apt update && apt upgrade -y

# Установка необходимых пакетов
print_status "Установка необходимых пакетов..."
apt install -y python3 python3-pip python3-venv git wget curl

# Установка Google Chrome для Selenium
print_status "Установка Google Chrome..."
wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add -
echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list
apt update
apt install -y google-chrome-stable

# Установка ChromeDriver
print_status "Установка ChromeDriver..."
CHROME_VERSION=$(google-chrome --version | grep -oP '\d+\.\d+\.\d+')
CHROMEDRIVER_VERSION=$(curl -s "https://chromedriver.storage.googleapis.com/LATEST_RELEASE_${CHROME_VERSION%%.*}")
wget -O /tmp/chromedriver.zip "https://chromedriver.storage.googleapis.com/${CHROMEDRIVER_VERSION}/chromedriver_linux64.zip"
unzip /tmp/chromedriver.zip -d /tmp/
mv /tmp/chromedriver /usr/local/bin/
chmod +x /usr/local/bin/chromedriver
rm /tmp/chromedriver.zip

# Создание пользователя для бота
print_status "Создание пользователя placesbot..."
if ! id "placesbot" &>/dev/null; then
    useradd -m -s /bin/bash placesbot
    print_status "Пользователь placesbot создан"
else
    print_warning "Пользователь placesbot уже существует"
fi

# Создание директории проекта
BOT_DIR="/opt/places_bot"
print_status "Создание директории проекта: $BOT_DIR"
mkdir -p $BOT_DIR
chown placesbot:placesbot $BOT_DIR

# Клонирование репозитория
print_status "Клонирование репозитория..."
cd $BOT_DIR
if [ -d ".git" ]; then
    print_warning "Репозиторий уже существует, обновляем..."
    sudo -u placesbot git pull origin main
else
    sudo -u placesbot git clone https://github.com/ishelaev/for_places_bot.git .
fi

# Создание виртуального окружения
print_status "Создание виртуального окружения Python..."
sudo -u placesbot python3 -m venv venv
sudo -u placesbot ./venv/bin/pip install --upgrade pip

# Установка зависимостей
print_status "Установка Python зависимостей..."
sudo -u placesbot ./venv/bin/pip install -r requirements.txt

# Создание директорий для логов и данных
print_status "Создание директорий..."
sudo -u placesbot mkdir -p logs data backups/excel backups/json backups/csv

# Создание .env файла (пользователь заполнит сам)
if [ ! -f ".env" ]; then
    print_status "Создание .env файла..."
    sudo -u placesbot cat > .env << 'EOF'
# Конфигурация Places Bot
BOT_TOKEN=your_telegram_bot_token_here
SPREADSHEET_ID=your_google_spreadsheet_id_here

# Опциональные настройки
LOG_LEVEL=INFO
BACKUP_ENABLED=true
EOF
    print_warning "ВАЖНО: Отредактируйте файл .env и укажите ваши токены!"
fi

print_status "✅ Установка завершена!"
print_warning "Следующие шаги:"
echo "1. Отредактируйте файл /opt/places_bot/.env"
echo "2. Добавьте учетные данные Google Sheets API"
echo "3. Запустите: sudo systemctl enable places-bot"
echo "4. Запустите: sudo systemctl start places-bot"
echo "5. Проверьте: sudo systemctl status places-bot"

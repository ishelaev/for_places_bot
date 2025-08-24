#!/bin/bash

# Скрипт установки Places Parser Bot на сервер

echo "🚀 Установка Places Parser Bot..."

# Проверяем, что мы в правильной директории
if [ ! -f "server_bot.py" ]; then
    echo "❌ Ошибка: файл server_bot.py не найден"
    echo "Запустите скрипт из директории с ботом"
    exit 1
fi

# Создаем необходимые директории
echo "📁 Создание директорий..."
mkdir -p data logs

# Устанавливаем зависимости
echo "📦 Установка Python зависимостей..."
pip3 install -r requirements.txt

# Проверяем установку Chrome
if ! command -v google-chrome &> /dev/null; then
    echo "🌐 Установка Chrome..."
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        # Linux
        sudo apt update
        sudo apt install -y chromium-browser chromium-chromedriver
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        # macOS
        echo "⚠️  Для macOS установите Chrome вручную: https://www.google.com/chrome/"
    fi
else
    echo "✅ Chrome уже установлен"
fi

# Настраиваем права доступа
echo "🔐 Настройка прав доступа..."
chmod +x server_bot.py
chmod 755 data logs

# Создаем systemd сервис (только для Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "🔧 Настройка systemd сервиса..."
    
    # Копируем сервис файл
    sudo cp parser-bot.service /etc/systemd/system/
    
    # Перезагружаем systemd
    sudo systemctl daemon-reload
    
    # Включаем автозапуск
    sudo systemctl enable parser-bot.service
    
    echo "✅ Сервис настроен и включен"
    echo "📋 Команды управления:"
    echo "   Запуск: sudo systemctl start parser-bot"
    echo "   Остановка: sudo systemctl stop parser-bot"
    echo "   Статус: sudo systemctl status parser-bot"
    echo "   Логи: sudo journalctl -u parser-bot -f"
else
    echo "⚠️  Для macOS используйте launchd или запускайте вручную"
fi

# Проверяем конфигурацию
echo "⚙️  Проверка конфигурации..."
if [ ! -f "config.py" ]; then
    echo "❌ Файл config.py не найден"
    exit 1
fi

echo ""
echo "🎉 Установка завершена!"
echo ""
echo "📋 Следующие шаги:"
echo "1. Отредактируйте config.py - добавьте ваш Telegram ID в ADMIN_IDS"
echo "2. Запустите бота: python3 server_bot.py"
echo "3. Протестируйте команду /start в Telegram"
echo ""
echo "📁 Структура проекта:"
echo "   data/ - папка с Excel файлами"
echo "   logs/ - папка с логами"
echo "   config.py - настройки бота"
echo ""
echo "🔧 Для запуска в фоновом режиме используйте screen:"
echo "   screen -S parser_bot"
echo "   python3 server_bot.py"
echo "   Ctrl+A, D - отключиться от screen"
echo "   screen -r parser_bot - подключиться обратно"

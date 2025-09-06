#!/bin/bash

# Скрипт управления Places Bot на сервере
# Использование: ./manage_bot.sh [install|start|stop|restart|status|logs|update]

SERVICE_NAME="places-bot"
BOT_DIR="/opt/places_bot"

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}=== $1 ===${NC}"
}

install_service() {
    print_header "Установка systemd сервиса"
    
    if [ ! -f "$BOT_DIR/places-bot.service" ]; then
        print_error "Файл places-bot.service не найден в $BOT_DIR"
        exit 1
    fi
    
    print_status "Копирование service файла..."
    sudo cp "$BOT_DIR/places-bot.service" /etc/systemd/system/
    
    print_status "Перезагрузка systemd..."
    sudo systemctl daemon-reload
    
    print_status "Включение автозапуска..."
    sudo systemctl enable $SERVICE_NAME
    
    print_status "✅ Сервис установлен и настроен для автозапуска"
}

start_bot() {
    print_header "Запуск бота"
    sudo systemctl start $SERVICE_NAME
    sleep 2
    sudo systemctl status $SERVICE_NAME --no-pager
}

stop_bot() {
    print_header "Остановка бота"
    sudo systemctl stop $SERVICE_NAME
    print_status "✅ Бот остановлен"
}

restart_bot() {
    print_header "Перезапуск бота"
    sudo systemctl restart $SERVICE_NAME
    sleep 2
    sudo systemctl status $SERVICE_NAME --no-pager
}

status_bot() {
    print_header "Статус бота"
    sudo systemctl status $SERVICE_NAME --no-pager
    echo ""
    print_status "Использование памяти:"
    ps aux | grep "[p]ython.*main.py" | awk '{print $2, $4, $6}' | head -1 | while read pid mem_percent mem_kb; do
        mem_mb=$((mem_kb / 1024))
        echo "PID: $pid, Memory: ${mem_percent}% (${mem_mb}MB)"
    done
}

show_logs() {
    print_header "Логи бота"
    echo "Основные логи:"
    tail -n 50 $BOT_DIR/logs/bot.log 2>/dev/null || echo "Лог файл не найден"
    echo ""
    echo "Ошибки:"
    tail -n 20 $BOT_DIR/logs/bot_error.log 2>/dev/null || echo "Лог ошибок не найден"
    echo ""
    echo "Systemd журнал (последние 20 строк):"
    sudo journalctl -u $SERVICE_NAME -n 20 --no-pager
}

update_bot() {
    print_header "Обновление бота"
    
    print_status "Остановка бота..."
    sudo systemctl stop $SERVICE_NAME
    
    print_status "Обновление кода..."
    cd $BOT_DIR
    sudo -u placesbot git pull origin main
    
    print_status "Обновление зависимостей..."
    sudo -u placesbot ./venv/bin/pip install -r requirements.txt --upgrade
    
    print_status "Запуск бота..."
    sudo systemctl start $SERVICE_NAME
    
    sleep 3
    sudo systemctl status $SERVICE_NAME --no-pager
    
    print_status "✅ Обновление завершено"
}

show_help() {
    echo "Использование: $0 [команда]"
    echo ""
    echo "Доступные команды:"
    echo "  install  - Установить systemd сервис"
    echo "  start    - Запустить бота"
    echo "  stop     - Остановить бота"
    echo "  restart  - Перезапустить бота"
    echo "  status   - Показать статус бота"
    echo "  logs     - Показать логи"
    echo "  update   - Обновить бота из Git"
    echo "  help     - Показать эту справку"
}

case "$1" in
    install)
        install_service
        ;;
    start)
        start_bot
        ;;
    stop)
        stop_bot
        ;;
    restart)
        restart_bot
        ;;
    status)
        status_bot
        ;;
    logs)
        show_logs
        ;;
    update)
        update_bot
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        print_error "Неизвестная команда: $1"
        show_help
        exit 1
        ;;
esac

#!/usr/bin/env python3
"""
Google Sheets Updater - обновление Google Sheets данными с Яндекс.Карт
"""

from google_sheets_manager import GoogleSheetsManager
from yandex_parser import parse_yandex

# ID вашей Google таблицы
SPREADSHEET_ID = "1w_jfZxc9yZS74-hRofIJfENd3ZqRUyE3Lh40TKVbLaI"

def update_google_sheets_with_yandex_data(url: str) -> dict:
    """
    Парсим данные с Яндекс.Карт по ссылке и обновляем Google Sheets.
    Если строки с такой ссылкой нет, создаём новую.
    Возвращает словарь с данными для отображения пользователю.
    """
    try:
        print(f"Начинаем обработку URL для Google Sheets: {url}")
        
        # Парсим данные
        print("Вызываем parse_yandex...")
        data = parse_yandex(url)
        print(f"Данные получены: {data}")
        
        # Создаем менеджер Google Sheets
        gsm = GoogleSheetsManager()
        
        # Открываем таблицу
        if not gsm.open_spreadsheet(SPREADSHEET_ID):
            raise Exception("Не удалось открыть таблицу")
        
        # Создаем лист если его нет
        gsm.create_worksheet_if_not_exists("places")
        
        # Открываем лист
        if not gsm.open_worksheet("places"):
            raise Exception("Не удалось открыть лист")
        
        # Обновляем данные
        success = gsm.update_place_data(url, data)
        
        if success:
            print(f"✅ Данные успешно обновлены в Google Sheets")
        else:
            print(f"❌ Ошибка обновления данных")
        
        return data
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return {}

if __name__ == "__main__":
    # Тест с примером ссылки
    test_url = "https://yandex.ru/maps/org/restoran/1234567890"
    print("Тестирование обновления Google Sheets...")
    result = update_google_sheets_with_yandex_data(test_url)
    print(f"Результат: {result}")

#!/usr/bin/env python3
"""
Google Sheets Manager - работа с Google Sheets через API
"""

import gspread
from google.oauth2.service_account import Credentials
from typing import Dict, List, Optional
import pandas as pd
from datetime import datetime

class GoogleSheetsManager:
    def __init__(self, credentials_path: str = "google_credentials.json"):
        """Инициализация подключения к Google Sheets"""
        self.credentials_path = credentials_path
        self.client = None
        self.spreadsheet = None
        self.worksheet = None
        
        # Области доступа для Google Sheets API
        self.scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]
        
        self._connect()
    
    def _connect(self):
        """Подключение к Google Sheets API"""
        try:
            # Загружаем учетные данные
            credentials = Credentials.from_service_account_file(
                self.credentials_path, 
                scopes=self.scope
            )
            
            # Создаем клиент
            self.client = gspread.authorize(credentials)
            print("✅ Подключение к Google Sheets API установлено")
            
        except Exception as e:
            print(f"❌ Ошибка подключения к Google Sheets: {e}")
            raise
    
    def open_spreadsheet(self, spreadsheet_id: str):
        """Открывает таблицу по ID"""
        try:
            self.spreadsheet = self.client.open_by_key(spreadsheet_id)
            print(f"✅ Таблица открыта: {self.spreadsheet.title}")
            return True
        except Exception as e:
            print(f"❌ Ошибка открытия таблицы: {e}")
            return False
    
    def open_worksheet(self, worksheet_name: str = "places"):
        """Открывает лист в таблице"""
        try:
            self.worksheet = self.spreadsheet.worksheet(worksheet_name)
            print(f"✅ Лист открыт: {self.worksheet.title}")
            return True
        except Exception as e:
            print(f"❌ Ошибка открытия листа: {e}")
            return False
    
    def get_all_data(self) -> List[List]:
        """Получает все данные из листа"""
        try:
            data = self.worksheet.get_all_values()
            print(f"✅ Получено {len(data)} строк данных")
            return data
        except Exception as e:
            print(f"❌ Ошибка получения данных: {e}")
            return []
    
    def get_data_as_dataframe(self) -> pd.DataFrame:
        """Получает данные в виде pandas DataFrame"""
        try:
            data = self.get_all_data()
            if not data:
                return pd.DataFrame()
            
            # Первая строка - заголовки
            headers = data[0]
            rows = data[1:]
            
            df = pd.DataFrame(rows, columns=headers)
            print(f"✅ DataFrame создан: {len(df)} строк, {len(df.columns)} колонок")
            return df
            
        except Exception as e:
            print(f"❌ Ошибка создания DataFrame: {e}")
            return pd.DataFrame()
    
    def update_place_data(self, url: str, data: Dict) -> bool:
        """
        Обновляет данные места в Google Sheets
        Возвращает True если успешно
        """
        try:
            # Получаем все данные
            all_data = self.get_all_data()
            if not all_data:
                return False
            
            headers = all_data[0]
            rows = all_data[1:]
            
            # Ищем строку с нужной ссылкой
            url_col_index = headers.index('Ссылка') if 'Ссылка' in headers else None
            if url_col_index is None:
                print("❌ Колонка 'Ссылка' не найдена")
                return False
            
            # Ищем существующую запись
            row_index = None
            for i, row in enumerate(rows):
                if len(row) > url_col_index and row[url_col_index] == url:
                    row_index = i + 2  # +2 потому что индексация с 1 и пропускаем заголовок
                    break
            
            # Подготавливаем данные для обновления
            update_data = []
            for header in headers:
                if header == 'Ссылка':
                    update_data.append(url)
                elif header == 'Название':
                    update_data.append(data.get('title', ''))
                elif header == 'Рейтинг':
                    update_data.append(data.get('rating', ''))
                elif header == 'Отзывы':
                    update_data.append(data.get('reviews', ''))
                elif header == 'Категории':
                    update_data.append(data.get('categories', ''))
                elif header == 'Широта':
                    coords = data.get('coordinates')
                    update_data.append(coords[0] if coords else '')
                elif header == 'Долгота':
                    coords = data.get('coordinates')
                    update_data.append(coords[1] if coords else '')
                elif header in ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс']:
                    hours = data.get('hours', {})
                    update_data.append(hours.get(header, ''))
                else:
                    update_data.append('')
            
            if row_index:
                # Обновляем существующую строку
                self.worksheet.update(f'A{row_index}:{chr(65 + len(headers) - 1)}{row_index}', [update_data])
                print(f"✅ Запись обновлена: {url}")
            else:
                # Добавляем новую строку
                self.worksheet.append_row(update_data)
                print(f"✅ Запись добавлена: {url}")
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка обновления данных: {e}")
            return False
    
    def create_worksheet_if_not_exists(self, worksheet_name: str = "places"):
        """Создает лист если его нет"""
        try:
            # Проверяем существование листа
            try:
                self.spreadsheet.worksheet(worksheet_name)
                print(f"✅ Лист '{worksheet_name}' уже существует")
                return True
            except gspread.WorksheetNotFound:
                pass
            
            # Создаем новый лист
            headers = [
                'Ссылка', 'Название', 'Рейтинг', 'Отзывы', 'Категории',
                'Широта', 'Долгота', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'
            ]
            
            worksheet = self.spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=len(headers))
            worksheet.append_row(headers)
            print(f"✅ Лист '{worksheet_name}' создан с заголовками")
            return True
            
        except Exception as e:
            print(f"❌ Ошибка создания листа: {e}")
            return False

# Пример использования
if __name__ == "__main__":
    # Создаем менеджер
    gsm = GoogleSheetsManager()
    
    # Здесь нужно будет указать ID вашей Google таблицы
    # spreadsheet_id = "YOUR_SPREADSHEET_ID"
    # gsm.open_spreadsheet(spreadsheet_id)
    # gsm.create_worksheet_if_not_exists()
    
    print("Google Sheets Manager готов к использованию")

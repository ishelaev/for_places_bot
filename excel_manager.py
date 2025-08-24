# excel_manager.py
import pandas as pd
from pathlib import Path
from typing import Dict, Optional, Tuple
from config import EXCEL_PATH
from logger import log_excel_update

class ExcelManager:
    def __init__(self):
        self.excel_path = EXCEL_PATH
        self._ensure_excel_exists()
    
    def _ensure_excel_exists(self):
        """Создает Excel файл с нужной структурой, если его нет"""
        if not self.excel_path.exists():
            # Создаем базовую структуру таблицы
            columns = [
                'Ссылка', 'Название', 'Рейтинг', 'Отзывы', 'Категории',
                'Широта', 'Долгота', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'
            ]
            df = pd.DataFrame(columns=columns)
            df.to_excel(self.excel_path, index=False)
            print(f"✅ Создан новый файл: {self.excel_path}")
    
    def load_data(self) -> pd.DataFrame:
        """Загружает данные из Excel"""
        try:
            return pd.read_excel(self.excel_path)
        except Exception as e:
            print(f"❌ Ошибка загрузки Excel: {e}")
            return pd.DataFrame()
    
    def save_data(self, df: pd.DataFrame):
        """Сохраняет данные в Excel"""
        try:
            df.to_excel(self.excel_path, index=False)
            print(f"✅ Данные сохранены в {self.excel_path}")
        except Exception as e:
            print(f"❌ Ошибка сохранения Excel: {e}")
    
    def update_place_data(self, url: str, data: Dict) -> Tuple[bool, str]:
        """
        Обновляет данные места в Excel
        Возвращает (успех, сообщение)
        """
        try:
            df = self.load_data()
            
            # Проверяем наличие ссылки
            if url in df['Ссылка'].values:
                row_idx = df[df['Ссылка'] == url].index[0]
                action = "обновлена"
                log_excel_update(url, "обновление существующей записи")
            else:
                # Создаем новую строку
                row_idx = len(df)
                df.loc[row_idx] = [None] * len(df.columns)
                df.at[row_idx, 'Ссылка'] = url
                action = "добавлена"
                log_excel_update(url, "создание новой записи")
            
            # Обновляем данные
            df.at[row_idx, 'Название'] = data.get('title', 'Название не найдено')
            df.at[row_idx, 'Рейтинг'] = data.get('rating', 'Рейтинг не найден')
            df.at[row_idx, 'Отзывы'] = data.get('reviews', 'Отзывы не найдены')
            df.at[row_idx, 'Категории'] = data.get('categories')
            
            # Координаты
            coordinates = data.get('coordinates')
            if coordinates and len(coordinates) == 2:
                latitude, longitude = coordinates
                df.at[row_idx, 'Широта'] = latitude
                df.at[row_idx, 'Долгота'] = longitude
            
            # Часы работы
            hours = data.get('hours', {})
            for day, time_range in hours.items():
                if day in df.columns:
                    df.at[row_idx, day] = time_range
            
            # Сохраняем
            self.save_data(df)
            
            return True, f"✅ Запись {action} в таблицу"
            
        except Exception as e:
            error_msg = f"❌ Ошибка обновления Excel: {e}"
            print(error_msg)
            return False, error_msg
    
    def get_places_count(self) -> int:
        """Возвращает количество мест в таблице"""
        try:
            df = self.load_data()
            return len(df)
        except:
            return 0
    
    def get_place_by_url(self, url: str) -> Optional[Dict]:
        """Получает данные места по URL"""
        try:
            df = self.load_data()
            if url in df['Ссылка'].values:
                row = df[df['Ссылка'] == url].iloc[0]
                return row.to_dict()
            return None
        except:
            return None
    
    def get_all_places(self) -> pd.DataFrame:
        """Возвращает все места"""
        return self.load_data()

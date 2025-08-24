# database_manager.py
import pandas as pd
from sqlalchemy import create_engine, text, inspect
from typing import Dict, Optional, Tuple, List
from config import POSTGRES_URL, EXCEL_PATH
from logger import log_excel_update
import logging
from pathlib import Path

logger = logging.getLogger('ParserBot')

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(POSTGRES_URL)
        self._ensure_table_exists()
        
        # Путь к локальному Excel файлу основного бота
        self.local_excel_path = Path("/Users/ivan/Desktop/EatSpot_Bot_git/data/places.xlsx")
    
    def _ensure_table_exists(self):
        """Проверяет существование таблицы places"""
        try:
            inspector = inspect(self.engine)
            if 'places' not in inspector.get_table_names():
                logger.error("❌ Таблица places не существует в базе данных")
            else:
                logger.info("✅ Таблица places существует")
        except Exception as e:
            logger.error(f"❌ Ошибка проверки таблицы: {e}")
    
    def update_place_data(self, url: str, data: Dict) -> Tuple[bool, str]:
        """
        Обновляет данные места в PostgreSQL
        Возвращает (успех, сообщение)
        """
        try:
            # Проверяем наличие записи (используем Ссылка вместо id)
            check_sql = text("SELECT \"Ссылка\" FROM places WHERE \"Ссылка\" = :url")
            
            with self.engine.connect() as conn:
                result = conn.execute(check_sql, {"url": url})
                existing_record = result.fetchone()
                
                if existing_record:
                    # Обновляем существующую запись
                    update_sql = text("""
                        UPDATE places SET 
                            "Название" = :title,
                            "Рейтинг" = :rating,
                            "Отзывы" = :reviews,
                            "Категории" = :categories,
                            "Широта" = :latitude,
                            "Долгота" = :longitude,
                            "Пн" = :monday,
                            "Вт" = :tuesday,
                            "Ср" = :wednesday,
                            "Чт" = :thursday,
                            "Пт" = :friday,
                            "Сб" = :saturday,
                            "Вс" = :sunday
                        WHERE "Ссылка" = :url
                    """)
                    action = "обновлена"
                    log_excel_update(url, "обновление существующей записи в PostgreSQL")
                else:
                    # Создаем новую запись
                    insert_sql = text("""
                        INSERT INTO places (
                            "Ссылка", "Название", "Рейтинг", "Отзывы", "Категории",
                            "Широта", "Долгота", "Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"
                        ) VALUES (
                            :url, :title, :rating, :reviews, :categories,
                            :latitude, :longitude, :monday, :tuesday, :wednesday,
                            :thursday, :friday, :saturday, :sunday
                        )
                    """)
                    action = "добавлена"
                    log_excel_update(url, "создание новой записи в PostgreSQL")
                
                # Подготавливаем данные
                coordinates = data.get('coordinates')
                latitude = longitude = None
                if coordinates and len(coordinates) == 2:
                    latitude, longitude = coordinates
                
                hours = data.get('hours', {})
                
                params = {
                    "url": url,
                    "title": data.get('title', 'Название не найдено'),
                    "rating": data.get('rating', 'Рейтинг не найден'),
                    "reviews": data.get('reviews', 'Отзывы не найдены'),
                    "categories": data.get('categories'),
                    "latitude": latitude,
                    "longitude": longitude,
                    "monday": hours.get('Пн'),
                    "tuesday": hours.get('Вт'),
                    "wednesday": hours.get('Ср'),
                    "thursday": hours.get('Чт'),
                    "friday": hours.get('Пт'),
                    "saturday": hours.get('Сб'),
                    "sunday": hours.get('Вс')
                }
                
                # Выполняем запрос
                if existing_record:
                    conn.execute(update_sql, params)
                else:
                    conn.execute(insert_sql, params)
                
                conn.commit()
            
            # Синхронизируем с локальным Excel файлом
            self._sync_with_local_excel()
            
            # Также сохраняем в Excel для бэкапа
            self._backup_to_excel(url, data)
            
            return True, f"✅ Запись {action} в PostgreSQL базу данных и синхронизирована с локальным Excel"
            
        except Exception as e:
            error_msg = f"❌ Ошибка обновления PostgreSQL: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def update_instagram_for_place(self, place_name: str, instagram_url: str) -> bool:
        """Обновляет Instagram ссылку для конкретного места"""
        try:
            update_sql = text("""
                UPDATE places SET "instagram" = :instagram_url
                WHERE "Название" = :place_name
            """)
            
            with self.engine.connect() as conn:
                result = conn.execute(update_sql, {
                    "instagram_url": instagram_url,
                    "place_name": place_name
                })
                conn.commit()
                
                if result.rowcount > 0:
                    logger.info(f"✅ Instagram обновлен для {place_name}: {instagram_url}")
                    # Синхронизируем с локальным Excel
                    self._sync_with_local_excel()
                    return True
                else:
                    logger.warning(f"⚠️ Место не найдено: {place_name}")
                    return False
                    
        except Exception as e:
            logger.error(f"❌ Ошибка обновления Instagram для {place_name}: {e}")
            return False
    
    def get_places_without_instagram(self, limit: int = 50) -> List[Dict]:
        """Возвращает места без Instagram"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT * FROM places 
                    WHERE "instagram" IS NULL OR "instagram" = '' OR "instagram" = 'nan'
                    ORDER BY "Название"
                    LIMIT :limit
                """), {"limit": limit})
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения мест без Instagram: {e}")
            return []
    
    def get_instagram_stats(self) -> Dict:
        """Возвращает статистику по Instagram"""
        try:
            with self.engine.connect() as conn:
                # Общее количество мест
                total_result = conn.execute(text("SELECT COUNT(*) FROM places"))
                total_count = total_result.scalar()
                
                # Места с Instagram
                with_insta_result = conn.execute(text("""
                    SELECT COUNT(*) FROM places 
                    WHERE "instagram" IS NOT NULL AND "instagram" != '' AND "instagram" != 'nan'
                """))
                with_instagram = with_insta_result.scalar()
                
                # Места без Instagram
                without_instagram = total_count - with_instagram
                
                return {
                    'total_places': total_count,
                    'with_instagram': with_instagram,
                    'without_instagram': without_instagram,
                    'percentage': round((with_instagram / total_count * 100) if total_count > 0 else 0, 1)
                }
        except Exception as e:
            logger.error(f"❌ Ошибка получения статистики Instagram: {e}")
            return {}
    
    def _sync_with_local_excel(self):
        """Синхронизирует данные из PostgreSQL с локальным Excel файлом"""
        try:
            # Получаем все данные из PostgreSQL
            all_places = self.get_all_places()
            
            if not all_places:
                logger.warning("⚠️ Нет данных для синхронизации с Excel")
                return
            
            # Создаем DataFrame
            df = pd.DataFrame(all_places)
            
            # Проверяем существование локального файла
            if self.local_excel_path.exists():
                logger.info(f"📊 Синхронизация с локальным Excel: {self.local_excel_path}")
            else:
                logger.info(f"📊 Создание нового локального Excel файла: {self.local_excel_path}")
            
            # Сохраняем в локальный Excel файл
            df.to_excel(self.local_excel_path, index=False)
            logger.info(f"✅ Локальный Excel файл обновлен: {len(all_places)} записей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка синхронизации с локальным Excel: {e}")
    
    def _backup_to_excel(self, url: str, data: Dict):
        """Создает резервную копию в Excel файле"""
        try:
            import pandas as pd
            
            # Загружаем существующий Excel или создаем новый
            if EXCEL_PATH.exists():
                df = pd.read_excel(EXCEL_PATH)
            else:
                columns = [
                    'Ссылка', 'Название', 'Рейтинг', 'Отзывы', 'Категории',
                    'Широта', 'Долгота', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'
                ]
                df = pd.DataFrame(columns=columns)
            
            # Обновляем или добавляем запись
            if url in df['Ссылка'].values:
                row_idx = df[df['Ссылка'] == url].index[0]
            else:
                row_idx = len(df)
                df.loc[row_idx] = [None] * len(df.columns)
                df.at[row_idx, 'Ссылка'] = url
            
            # Обновляем данные
            df.at[row_idx, 'Название'] = data.get('title', 'Название не найдено')
            df.at[row_idx, 'Рейтинг'] = data.get('rating', 'Рейтинг не найден')
            df.at[row_idx, 'Отзывы'] = data.get('reviews', 'Отзывы не найдены')
            df.at[row_idx, 'Категории'] = data.get('categories')
            
            coordinates = data.get('coordinates')
            if coordinates and len(coordinates) == 2:
                latitude, longitude = coordinates
                df.at[row_idx, 'Широта'] = latitude
                df.at[row_idx, 'Долгота'] = longitude
            
            hours = data.get('hours', {})
            for day, time_range in hours.items():
                if day in df.columns:
                    df.at[row_idx, day] = time_range
            
            df.to_excel(EXCEL_PATH, index=False)
            logger.info(f"📊 Резервная копия сохранена в Excel: {url}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка создания Excel бэкапа: {e}")
    
    def get_places_count(self) -> int:
        """Возвращает количество мест в базе данных"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT COUNT(*) FROM places"))
                return result.scalar()
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета записей: {e}")
            return 0
    
    def get_place_by_url(self, url: str) -> Optional[Dict]:
        """Получает данные места по URL"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM places WHERE \"Ссылка\" = :url"),
                    {"url": url}
                )
                row = result.fetchone()
                if row:
                    return dict(row._mapping)
                return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения записи: {e}")
            return None
    
    def get_all_places(self) -> List[Dict]:
        """Возвращает все места из базы данных"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT * FROM places ORDER BY \"Ссылка\""))
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех записей: {e}")
            return []
    
    def get_recent_places(self, limit: int = 10) -> List[Dict]:
        """Возвращает последние добавленные места (по Ссылке)"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT * FROM places ORDER BY \"Ссылка\" DESC LIMIT :limit"),
                    {"limit": limit}
                )
                return [dict(row._mapping) for row in result.fetchall()]
        except Exception as e:
            logger.error(f"❌ Ошибка получения последних записей: {e}")
            return []
    
    def force_sync_excel(self) -> bool:
        """Принудительная синхронизация с локальным Excel файлом"""
        try:
            self._sync_with_local_excel()
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка принудительной синхронизации: {e}")
            return False

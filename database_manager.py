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
        # Путь к Excel файлу основного бота (EatSpot_Bot_git)
        self.excel_path = Path("/Users/ivan/Desktop/EatSpot_Bot_git/data/places.xlsx")
        
        # Создаем директорию, если её нет
        self.excel_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Пытаемся подключиться к PostgreSQL
        self.use_db = False
        self.engine = None
        
        try:
            self.engine = create_engine(POSTGRES_URL)
            # Проверяем подключение
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            self.use_db = True
            self._ensure_table_exists()
            logger.info("✅ Подключение к PostgreSQL успешно, используем БД")
        except Exception as e:
            logger.warning(f"⚠️ Не удалось подключиться к PostgreSQL: {e}")
            logger.info("📁 Будем работать с локальным Excel файлом")
            self.use_db = False
            # Создаем файл с заголовками, если его нет
            if not self.excel_path.exists():
                self._create_empty_excel()
    
    def _create_empty_excel(self):
        """Создает пустой Excel файл с нужными колонками"""
        columns = [
            'Ссылка', 'Название', 'Рейтинг', 'Отзывы', 'Категории',
            'Широта', 'Долгота', 'Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'
        ]
        df = pd.DataFrame(columns=columns)
        df.to_excel(self.excel_path, index=False)
        logger.info(f"✅ Создан новый Excel файл: {self.excel_path}")
    
    def _ensure_table_exists(self):
        """Проверяет существование таблицы places"""
        if not self.use_db:
            return
        try:
            inspector = inspect(self.engine)
            if 'places' not in inspector.get_table_names():
                logger.error("❌ Таблица places не существует в базе данных")
            else:
                logger.info("✅ Таблица places существует")
        except Exception as e:
            logger.error(f"❌ Ошибка проверки таблицы: {e}")
    
    def update_place_data(self, url: str, data: Dict) -> Tuple[bool, str, str]:
        """
        Обновляет данные места в БД (если доступна) или в локальном Excel файле
        Возвращает (успех, сообщение, action) где action = "обновлена" или "добавлена"
        """
        try:
            if self.use_db:
                # Пытаемся обновить в PostgreSQL
                try:
                    return self._update_postgres(url, data)
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка обновления PostgreSQL, переключаемся на Excel: {e}")
                    self.use_db = False  # Переключаемся на Excel
            
            # Обновляем Excel файл основного бота
            action = self._update_excel(url, data)
            
            return True, f"✅ Запись {action} в базу данных", action
            
        except Exception as e:
            error_msg = f"❌ Ошибка обновления: {e}"
            logger.error(error_msg)
            import traceback
            logger.error(traceback.format_exc())
            return False, error_msg
    
    def _update_postgres(self, url: str, data: Dict) -> Tuple[bool, str, str]:
        """Обновляет данные в PostgreSQL"""
        # Проверяем наличие записи
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
        
        # Также синхронизируем с Excel файлом основного бота
        self._update_excel(url, data)
        
        return True, f"✅ Запись {action} в базу данных", action
    
    def update_instagram_for_place(self, place_name: str, instagram_url: str) -> bool:
        """Обновляет Instagram ссылку для конкретного места"""
        try:
            if not self.excel_path.exists():
                logger.warning("⚠️ Excel файл не существует")
                return False
            
            df = pd.read_excel(self.excel_path)
            
            if 'Название' not in df.columns:
                logger.warning("⚠️ В Excel файле нет колонки 'Название'")
                return False
            
            # Ищем место по названию
            mask = df['Название'].astype(str).str.strip() == str(place_name).strip()
            
            if mask.any():
                # Добавляем колонку Instagram, если её нет
                if 'instagram' not in df.columns:
                    df['instagram'] = None
                
                idx = df[mask].index[0]
                df.at[idx, 'instagram'] = instagram_url
                
                df.to_excel(self.excel_path, index=False)
                logger.info(f"✅ Instagram обновлен для {place_name}: {instagram_url}")
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
            if not self.excel_path.exists():
                return []
            
            df = pd.read_excel(self.excel_path)
            
            if 'instagram' not in df.columns or 'Название' not in df.columns:
                return []
            
            # Фильтруем места без Instagram
            mask = df['instagram'].isna() | (df['instagram'].astype(str).str.strip() == '') | (df['instagram'].astype(str).str.strip() == 'nan')
            filtered_df = df[mask].head(limit)
            
            return filtered_df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"❌ Ошибка получения мест без Instagram: {e}")
            return []
    
    def get_instagram_stats(self) -> Dict:
        """Возвращает статистику по Instagram"""
        try:
            if not self.excel_path.exists():
                return {'total_places': 0, 'with_instagram': 0, 'without_instagram': 0, 'percentage': 0}
            
            df = pd.read_excel(self.excel_path)
            
            total_count = len(df)
            
            if 'instagram' not in df.columns:
                return {
                    'total_places': total_count,
                    'with_instagram': 0,
                    'without_instagram': total_count,
                    'percentage': 0
                }
            
            # Места с Instagram
            mask = df['instagram'].notna() & (df['instagram'].astype(str).str.strip() != '') & (df['instagram'].astype(str).str.strip() != 'nan')
            with_instagram = mask.sum()
            
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
    
    def _update_excel(self, url: str, data: Dict) -> str:
        """Добавляет или обновляет запись в локальном Excel файле"""
        try:
            # Подготавливаем данные для Excel
            coordinates = data.get('coordinates')
            latitude = longitude = None
            if coordinates and len(coordinates) == 2:
                latitude, longitude = coordinates
            
            hours = data.get('hours', {})
            
            # Создаем новую строку данных
            new_row = {
                'Ссылка': url,
                'Название': data.get('title', 'Название не найдено'),
                'Рейтинг': data.get('rating', 'Рейтинг не найден'),
                'Отзывы': data.get('reviews', 'Отзывы не найдены'),
                'Категории': data.get('categories'),
                'Широта': latitude,
                'Долгота': longitude,
                'instagram': data.get('instagram'),
                'Пн': hours.get('Пн'),
                'Вт': hours.get('Вт'),
                'Ср': hours.get('Ср'),
                'Чт': hours.get('Чт'),
                'Пт': hours.get('Пт'),
                'Сб': hours.get('Сб'),
                'Вс': hours.get('Вс')
            }
            
            # Проверяем существование файла
            if self.excel_path.exists():
                logger.info(f"📊 Обновление Excel: {self.excel_path}")
                
                # Загружаем существующий Excel файл
                try:
                    df = pd.read_excel(self.excel_path)
                    
                    # Проверяем, есть ли уже запись с такой ссылкой
                    if 'Ссылка' in df.columns:
                        mask = df['Ссылка'].astype(str).str.strip() == str(url).strip()
                        if mask.any():
                            # Обновляем существующую запись
                            idx = df[mask].index[0]
                            for key, value in new_row.items():
                                if key in df.columns:
                                    df.at[idx, key] = value
                            action = "обновлена"
                            logger.info(f"✅ Обновлена запись в Excel: {url}")
                        else:
                            # Добавляем новую запись
                            # Убеждаемся, что все колонки присутствуют
                            for key in new_row.keys():
                                if key not in df.columns:
                                    df[key] = None
                            
                            # Добавляем новую строку
                            new_df = pd.DataFrame([new_row])
                            df = pd.concat([df, new_df], ignore_index=True)
                            action = "добавлена"
                            logger.info(f"✅ Добавлена новая запись в Excel: {url}")
                    else:
                        # Если нет колонки 'Ссылка', создаем новый DataFrame
                        logger.warning("⚠️ В Excel файле нет колонки 'Ссылка', создаю новую структуру")
                        df = pd.DataFrame([new_row])
                        action = "добавлена"
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка чтения Excel, создаю новый файл: {e}")
                    df = pd.DataFrame([new_row])
                    action = "добавлена"
            else:
                logger.info(f"📊 Создание нового Excel файла: {self.excel_path}")
                df = pd.DataFrame([new_row])
                action = "добавлена"
            
            # Сохраняем в локальный Excel файл
            df.to_excel(self.excel_path, index=False)
            logger.info(f"✅ Excel файл сохранен: {len(df)} записей")
            log_excel_update(url, f"{action} в локальный Excel файл")
            
            return action
            
        except Exception as e:
            logger.error(f"❌ Ошибка обновления Excel: {e}")
            import traceback
            logger.error(traceback.format_exc())
            raise
    
    def _sync_with_local_excel(self):
        """Полная синхронизация всех данных из PostgreSQL с локальным Excel файлом"""
        if not self.use_db:
            logger.info("📁 Используем только Excel, синхронизация не требуется")
            return
        try:
            # Получаем все данные из PostgreSQL
            all_places = self.get_all_places()
            
            if not all_places:
                logger.warning("⚠️ Нет данных для синхронизации с Excel")
                return
            
            # Создаем DataFrame из данных PostgreSQL
            df = pd.DataFrame(all_places)
            
            # Сохраняем в локальный Excel файл
            df.to_excel(self.excel_path, index=False)
            logger.info(f"✅ Полная синхронизация локального Excel: {len(df)} записей")
            log_excel_update(self.excel_path, f"полная синхронизация: {len(df)} записей")
            
        except Exception as e:
            logger.error(f"❌ Ошибка полной синхронизации с локальным Excel: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    
    def get_places_count(self) -> int:
        """Возвращает количество мест в базе данных или Excel"""
        try:
            if self.use_db:
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(text("SELECT COUNT(*) FROM places"))
                        return result.scalar()
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка подсчета в БД, переключаемся на Excel: {e}")
                    self.use_db = False
            
            # Работаем с Excel
            if not self.excel_path.exists():
                return 0
            df = pd.read_excel(self.excel_path)
            return len(df)
        except Exception as e:
            logger.error(f"❌ Ошибка подсчета записей: {e}")
            return 0
    
    def get_place_by_url(self, url: str) -> Optional[Dict]:
        """Получает данные места по URL"""
        try:
            if self.use_db:
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
                    logger.warning(f"⚠️ Ошибка получения из БД, переключаемся на Excel: {e}")
                    self.use_db = False
            
            # Работаем с Excel
            if not self.excel_path.exists():
                return None
            df = pd.read_excel(self.excel_path)
            if 'Ссылка' not in df.columns:
                return None
            mask = df['Ссылка'].astype(str).str.strip() == str(url).strip()
            if mask.any():
                row = df[mask].iloc[0]
                return row.to_dict()
            return None
        except Exception as e:
            logger.error(f"❌ Ошибка получения записи: {e}")
            return None
    
    def get_all_places(self) -> List[Dict]:
        """Возвращает все места из базы данных или Excel"""
        try:
            if self.use_db:
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(text("SELECT * FROM places ORDER BY \"Ссылка\""))
                        return [dict(row._mapping) for row in result.fetchall()]
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка получения из БД, переключаемся на Excel: {e}")
                    self.use_db = False
            
            # Работаем с Excel
            if not self.excel_path.exists():
                return []
            df = pd.read_excel(self.excel_path)
            if 'Ссылка' in df.columns:
                df = df.sort_values('Ссылка')
            return df.to_dict(orient='records')
        except Exception as e:
            logger.error(f"❌ Ошибка получения всех записей: {e}")
            return []
    
    def get_recent_places(self, limit: int = 10) -> List[Dict]:
        """Возвращает последние добавленные места (по Ссылке)"""
        try:
            if self.use_db:
                try:
                    with self.engine.connect() as conn:
                        result = conn.execute(
                            text("SELECT * FROM places ORDER BY \"Ссылка\" DESC LIMIT :limit"),
                            {"limit": limit}
                        )
                        return [dict(row._mapping) for row in result.fetchall()]
                except Exception as e:
                    logger.warning(f"⚠️ Ошибка получения из БД, переключаемся на Excel: {e}")
                    self.use_db = False
            
            # Работаем с Excel
            if not self.excel_path.exists():
                return []
            df = pd.read_excel(self.excel_path)
            if 'Ссылка' in df.columns:
                df = df.sort_values('Ссылка', ascending=False)
            return df.head(limit).to_dict(orient='records')
        except Exception as e:
            logger.error(f"❌ Ошибка получения последних записей: {e}")
            return []
    
    def force_sync_excel(self) -> bool:
        """Принудительная синхронизация с локальным Excel файлом"""
        try:
            if self.use_db:
                self._sync_with_local_excel()
            else:
                logger.info("📁 Используем только Excel, синхронизация не требуется")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка принудительной синхронизации: {e}")
            return False

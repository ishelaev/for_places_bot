# instagram_parser.py
import os
import re
import time
import pandas as pd
from googlesearch import search
from typing import Optional, Set
from pathlib import Path
from logger import setup_logger

logger = setup_logger()

class InstagramParser:
    def __init__(self, data_dir: str = "/Users/ivan/Desktop/EatSpot_Bot_git/data"):
        self.data_dir = Path(data_dir)
        self.blacklist_file = self.data_dir / "instagram_blacklist.txt"
        self.city_default = "Москва"
        self.sleep_between_queries = 2  # секунд
        
        # Базовый чёрный список
        self.base_blacklist = {"13 Градусов", "Цирк", "The Waterfront", "Стая"}
        
        # Загружаем чёрный список
        self.blacklist = self.load_blacklist()
    
    def _transliterate(self, text: str) -> str:
        """Простая транслитерация кириллицы в латиницу"""
        translit_map = {
            'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'е': 'e', 'ё': 'yo',
            'ж': 'zh', 'з': 'z', 'и': 'i', 'й': 'y', 'к': 'k', 'л': 'l', 'м': 'm',
            'н': 'n', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'у': 'u',
            'ф': 'f', 'х': 'h', 'ц': 'ts', 'ч': 'ch', 'ш': 'sh', 'щ': 'sch',
            'ъ': '', 'ы': 'y', 'ь': '', 'э': 'e', 'ю': 'yu', 'я': 'ya',
            'А': 'A', 'Б': 'B', 'В': 'V', 'Г': 'G', 'Д': 'D', 'Е': 'E', 'Ё': 'Yo',
            'Ж': 'Zh', 'З': 'Z', 'И': 'I', 'Й': 'Y', 'К': 'K', 'Л': 'L', 'М': 'M',
            'Н': 'N', 'О': 'O', 'П': 'P', 'Р': 'R', 'С': 'S', 'Т': 'T', 'У': 'U',
            'Ф': 'F', 'Х': 'H', 'Ц': 'Ts', 'Ч': 'Ch', 'Ш': 'Sh', 'Щ': 'Sch',
            'Ъ': '', 'Ы': 'Y', 'Ь': '', 'Э': 'E', 'Ю': 'Yu', 'Я': 'Ya',
        }
        result = ''
        for char in text:
            result += translit_map.get(char, char)
        return result
    
    def normalize_name(self, name: str) -> str:
        """Нормализует название для сравнения"""
        if not isinstance(name, str):
            name = "" if pd.isna(name) else str(name)
        s = name.strip().lower()
        s = s.replace("ё", "е")
        # унифицируем кавычки/дефисы/многопробелье
        s = s.replace("'", "'").replace("'", "'").replace(""", '"').replace(""", '"')
        s = re.sub(r"[-–—]+", "-", s)
        s = re.sub(r"\s+", " ", s)
        return s
    
    def load_blacklist(self) -> Set[str]:
        """Загружает чёрный список из файла"""
        names = set()
        if self.blacklist_file.exists():
            with open(self.blacklist_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        names.add(line)
        # добавим базовые элементы
        names |= self.base_blacklist
        return names
    
    def save_blacklist(self) -> None:
        """Сохраняет чёрный список в файл"""
        with open(self.blacklist_file, "w", encoding="utf-8") as f:
            for n in sorted(self.blacklist, key=lambda x: self.normalize_name(x)):
                f.write(n + "\n")
    
    def is_in_blacklist(self, name: str) -> bool:
        """Проверяет, есть ли название в чёрном списке"""
        norm = self.normalize_name(name)
        norm_set = {self.normalize_name(x) for x in self.blacklist}
        return norm in norm_set
    
    def add_to_blacklist(self, name: str) -> bool:
        """Добавляет название в чёрный список"""
        if not self.is_in_blacklist(name):
            self.blacklist.add(name)
            return True
        return False
    
    def find_instagram(self, name: str, city: str = None) -> Optional[str]:
        """Ищет Instagram аккаунт для заведения через несколько методов"""
        if city is None:
            city = self.city_default
        
        # Пробуем разные варианты запроса
        # Также пробуем транслитерацию названия
        name_translit = self._transliterate(name)
        query_variants = [
            f"site:instagram.com {name} {city}",  # С городом
            f"site:instagram.com {name}",  # Без города
            f"site:instagram.com {name_translit} {city}",  # Транслитерация с городом
            f"site:instagram.com {name_translit}",  # Транслитерация без города
            f"{name} instagram {city}",  # Без site:
            f"{name} instagram",  # Без города и site:
        ]
        import requests
        from urllib.parse import quote_plus
        import re
        
        # Пробуем каждый вариант запроса
        for query in query_variants:
            # Метод 1: Bing Search (менее строгий чем Google)
            try:
                bing_url = f"https://www.bing.com/search?q={quote_plus(query)}&count=10"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
                }
                
                response = requests.get(bing_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # Ищем ссылки в разных форматах
                    instagram_patterns = [
                        r'https?://(?:www\.)?instagram\.com/[^\s"<>\)]+',  # Обычный формат
                        r'instagram\.com/[^\s"<>\)]+',  # Без протокола
                        r'href=["\']([^"\']*instagram\.com/[^"\']+)["\']',  # В атрибуте href
                    ]
                    for pattern in instagram_patterns:
                        matches = re.findall(pattern, response.text)
                        for match in matches:
                            # Если это группа из regex, берем первую
                            if isinstance(match, tuple):
                                match = match[0] if match[0] else match[1] if len(match) > 1 else ''
                            if not match:
                                continue
                            # Добавляем протокол, если его нет
                            if match.startswith('instagram.com'):
                                match = 'https://www.' + match
                            elif match.startswith('//'):
                                match = 'https:' + match
                            if '/p/' not in match and '/reel/' not in match and '/stories/' not in match:
                                logger.info(f"✅ Найден Instagram через Bing для {name}: {match}")
                                return match
            except Exception as e:
                logger.debug(f"Bing не сработал для {name} (запрос: {query}): {e}")
            
            # Метод 2: Yandex Search
            try:
                yandex_url = f"https://yandex.ru/search/?text={quote_plus(query)}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Accept-Language': 'ru-RU,ru;q=0.9',
                }
                
                response = requests.get(yandex_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    # Ищем ссылки в разных форматах
                    instagram_patterns = [
                        r'https?://(?:www\.)?instagram\.com/[^\s"<>\)]+',
                        r'instagram\.com/[^\s"<>\)]+',
                        r'href=["\']([^"\']*instagram\.com/[^"\']+)["\']',
                    ]
                    for pattern in instagram_patterns:
                        matches = re.findall(pattern, response.text)
                        for match in matches:
                            if isinstance(match, tuple):
                                match = match[0] if match[0] else match[1] if len(match) > 1 else ''
                            if not match:
                                continue
                            if match.startswith('instagram.com'):
                                match = 'https://www.' + match
                            elif match.startswith('//'):
                                match = 'https:' + match
                            if '/p/' not in match and '/reel/' not in match and '/stories/' not in match:
                                logger.info(f"✅ Найден Instagram через Yandex для {name}: {match}")
                                return match
            except Exception as e:
                logger.debug(f"Yandex не сработал для {name} (запрос: {query}): {e}")
            
            # Метод 3: DuckDuckGo (менее строгий к автоматизации)
            try:
                ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
                headers = {
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                }
                
                response = requests.get(ddg_url, headers=headers, timeout=10)
                if response.status_code == 200:
                    instagram_pattern = r'https?://(?:www\.)?instagram\.com/[^\s"<>]+'
                    matches = re.findall(instagram_pattern, response.text)
                    for match in matches:
                        if '/p/' not in match and '/reel/' not in match and '/stories/' not in match:
                            logger.info(f"✅ Найден Instagram через DuckDuckGo для {name}: {match}")
                            return match
            except Exception as e:
                logger.debug(f"DuckDuckGo не сработал для {name} (запрос: {query}): {e}")
            
            # Метод 4: Google Search (основной метод, как в оригинале) - только для первого варианта запроса
            if query == query_variants[0]:  # Только для основного запроса
                try:
                    # Простой поиск как в оригинальной рабочей версии
                    for result in search(query, num_results=5, lang='ru'):
                        if "instagram.com" in result:
                            if '/p/' not in result and '/reel/' not in result:
                                logger.info(f"✅ Найден Instagram через Google для {name}: {result}")
                                return result
                except Exception as e:
                    error_str = str(e)
                    # Если это блокировка Google, логируем предупреждение
                    if "429" in error_str or "Too Many Requests" in error_str:
                        logger.warning(f"⚠️ Google временно блокирует запросы для {name}")
                    else:
                        logger.error(f"❌ Ошибка поиска Instagram через Google для {name}: {e}")
            
            # Небольшая задержка между вариантами запросов
            time.sleep(0.5)
        
        return None
    
    def process_place(self, place_name: str) -> Optional[str]:
        """Обрабатывает одно место и возвращает Instagram ссылку"""
        if not place_name or pd.isna(place_name):
            return None
            
        name = str(place_name).strip()
        
        # Проверяем чёрный список
        if self.is_in_blacklist(name):
            logger.info(f"⏭ Пропущено (в чёрном списке): {name}")
            return None
        
        # Ищем Instagram
        insta_link = self.find_instagram(name)
        
        if insta_link:
            return insta_link
        else:
            logger.info(f"❌ Не найден Instagram для {name} — добавляю в чёрный список")
            if self.add_to_blacklist(name):
                self.save_blacklist()
            return None
    
    def batch_process_places(self, places_data: list, max_count: int = 10) -> dict:
        """Обрабатывает несколько мест и возвращает результаты"""
        results = {}
        processed = 0
        
        for place in places_data:
            if processed >= max_count:
                break
                
            name = place.get('Название', '')
            if not name or pd.isna(name):
                continue
                
            # Проверяем, есть ли уже Instagram
            if place.get('instagram') and str(place.get('instagram')).strip():
                continue
            
            logger.info(f"🔍 Обрабатываю: {name}")
            insta_link = self.process_place(name)
            
            if insta_link:
                results[name] = insta_link
                processed += 1
            
            # Пауза между запросами
            time.sleep(self.sleep_between_queries)
        
        return results
    
    def get_blacklist_stats(self) -> dict:
        """Возвращает статистику чёрного списка"""
        return {
            'total_count': len(self.blacklist),
            'base_count': len(self.base_blacklist),
            'custom_count': len(self.blacklist) - len(self.base_blacklist),
            'file_path': str(self.blacklist_file)
        }

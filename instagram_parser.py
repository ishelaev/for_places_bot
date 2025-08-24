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
        """Ищет Instagram аккаунт для заведения"""
        if city is None:
            city = self.city_default
            
        query = f"site:instagram.com {name} {city}"
        
        try:
            for result in search(query, num_results=5, lang="ru"):
                if "instagram.com" in result:
                    logger.info(f"✅ Найден Instagram для {name}: {result}")
                    return result
        except Exception as e:
            logger.error(f"❌ Ошибка поиска Instagram для {name}: {e}")
        
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

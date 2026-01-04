#!/usr/bin/env python3
"""
Простой поиск Instagram по названию заведения и городу
Использует поисковики: Bing, Yandex, DuckDuckGo
"""

import re
import time
import sys
import requests
from pathlib import Path
from urllib.parse import quote_plus
from bs4 import BeautifulSoup
from typing import Optional


def find_instagram_simple(name: str, city: str = "Москва") -> Optional[str]:
    """
    Ищет Instagram аккаунт для заведения через поисковики
    
    Args:
        name: Название заведения
        city: Город (по умолчанию "Москва")
    
    Returns:
        Ссылка на Instagram или None
    """
    print(f"🔍 Ищу Instagram для: {name} ({city})")
    print("=" * 60)
    
    # Варианты запросов
    queries = [
        f"{name} {city} instagram",
        f"{name} instagram {city}",
        f'site:instagram.com "{name}" {city}',
        f'site:instagram.com {name}',
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
    }
    
    # Метод 1: Bing Search
    print("\n📊 Метод 1: Поиск через Bing...")
    for query in queries:
        try:
            bing_url = f"https://www.bing.com/search?q={quote_plus(query)}&count=10"
            response = requests.get(bing_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Ищем ссылки на Instagram
                instagram_pattern = r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)'
                matches = re.findall(instagram_pattern, response.text)
                
                for username in matches:
                    if username not in ['p', 'reel', 'stories', 'explore', 'accounts', 'direct']:
                        instagram_url = f"https://www.instagram.com/{username}/"
                        print(f"✅ Найден через Bing: {instagram_url}")
                        return instagram_url
            
            time.sleep(1)  # Пауза между запросами
        except Exception as e:
            print(f"   Ошибка: {e}")
            continue
    
    # Метод 2: Yandex Search
    print("\n📊 Метод 2: Поиск через Yandex...")
    for query in queries[:2]:  # Только первые 2 запроса
        try:
            yandex_url = f"https://yandex.ru/search/?text={quote_plus(query)}"
            response = requests.get(yandex_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                instagram_pattern = r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)'
                matches = re.findall(instagram_pattern, response.text)
                
                for username in matches:
                    if username not in ['p', 'reel', 'stories', 'explore', 'accounts', 'direct']:
                        instagram_url = f"https://www.instagram.com/{username}/"
                        print(f"✅ Найден через Yandex: {instagram_url}")
                        return instagram_url
            
            time.sleep(1)
        except Exception as e:
            print(f"   Ошибка: {e}")
            continue
    
    # Метод 3: DuckDuckGo
    print("\n📊 Метод 3: Поиск через DuckDuckGo...")
    for query in queries[:2]:
        try:
            ddg_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            response = requests.get(ddg_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                instagram_pattern = r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)'
                matches = re.findall(instagram_pattern, response.text)
                
                for username in matches:
                    if username not in ['p', 'reel', 'stories', 'explore', 'accounts', 'direct']:
                        instagram_url = f"https://www.instagram.com/{username}/"
                        print(f"✅ Найден через DuckDuckGo: {instagram_url}")
                        return instagram_url
            
            time.sleep(1)
        except Exception as e:
            print(f"   Ошибка: {e}")
            continue
    
    print("\n❌ Instagram не найден через поисковики")
    return None


def find_instagram_from_yandex_url(yandex_url: str, city: str = "Москва") -> Optional[str]:
    """
    Ищет Instagram для заведения по ссылке Яндекс.Карт
    
    Args:
        yandex_url: Ссылка на Яндекс.Карты
        city: Город для поиска
    
    Returns:
        Ссылка на Instagram или None
    """
    print(f"🔍 Ищу Instagram для: {yandex_url}")
    print("=" * 60)
    
    # Парсим название заведения
    print("📄 Парсинг названия заведения...")
    try:
        # Импортируем из родительской директории
        parent_dir = Path(__file__).parent.parent
        if str(parent_dir) not in sys.path:
            sys.path.insert(0, str(parent_dir))
        from yandex_parser import parse_yandex
        
        place_data = parse_yandex(yandex_url)
        name = place_data.get('title')
        
        if not name or name == "Название не найдено":
            print("❌ Не удалось извлечь название")
            return None
        
        print(f"✅ Название: {name}")
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Ищем Instagram
    return find_instagram_simple(name, city)


def main():
    """Тестовая функция"""
    import sys
    
    test_url = "https://yandex.ru/maps/org/stim_coffee/54162905237/"
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    result = find_instagram_from_yandex_url(test_url)
    
    print("\n" + "=" * 60)
    if result:
        print(f"🎉 Результат: {result}")
    else:
        print("😞 Instagram не найден")
    
    return result


if __name__ == "__main__":
    main()

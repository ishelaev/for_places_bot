#!/usr/bin/env python3
"""
Поиск Instagram заведения по ссылке Яндекс.Карт
Использует Google поиск через Selenium для получения результатов
"""

import re
import time
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import quote_plus

# Добавляем родительскую директорию в путь для импорта
sys.path.insert(0, str(Path(__file__).parent.parent))

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


def get_venue_type_keyword(categories: Optional[str]) -> str:
    """
    Определяет тип заведения на основе категорий и возвращает ключевое слово для поиска
    
    Args:
        categories: Строка с категориями через запятую
    
    Returns:
        Ключевое слово: "бар", "ресторан", "кафе" и т.д.
    """
    if not categories:
        return ""
    
    categories_lower = categories.lower()
    
    # Приоритетный порядок проверки
    if any(word in categories_lower for word in ["бар", "bar", "паб", "pub"]):
        return "бар"
    elif any(word in categories_lower for word in ["ресторан", "restaurant"]):
        return "ресторан"
    elif any(word in categories_lower for word in ["кафе", "cafe", "кофейня", "coffee"]):
        return "кафе"
    elif any(word in categories_lower for word in ["пиццерия", "pizzeria"]):
        return "пиццерия"
    elif any(word in categories_lower for word in ["бистро", "bistro"]):
        return "бистро"
    
    return ""


def find_instagram_via_google(name: str, city: str = "Москва", categories: Optional[str] = None, verbose: bool = True) -> Optional[str]:
    """
    Ищет Instagram через Google поиск используя Selenium
    
    Args:
        name: Название заведения
        city: Город
        categories: Категории заведения (для улучшения поиска)
        verbose: Выводить ли подробную информацию (по умолчанию True)
    
    Returns:
        Ссылка на Instagram или None
    """
    if verbose:
        print(f"🔍 Ищу Instagram для: {name} ({city})")
        if categories:
            print(f"🏷️  Категории: {categories}")
        print("=" * 60)
    
    # Формируем запрос с учетом типа заведения
    venue_type = get_venue_type_keyword(categories)
    if venue_type:
        query = f'"{name}" {venue_type} {city} instagram'
        if verbose:
            print(f"📝 Запрос в Google: '{query}' (с учетом типа заведения: {venue_type})")
    else:
        query = f'"{name}" {city} instagram'
        if verbose:
            print(f"📝 Запрос в Google: '{query}'")
    
    driver = None
    try:
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
        
        driver = webdriver.Chrome(options=options)
        
        # Ищем в Google
        google_url = f"https://www.google.com/search?q={quote_plus(query)}&hl=ru"
        if verbose:
            print(f"🌐 Открываю Google: {google_url}")
        driver.get(google_url)
        time.sleep(3)  # Ждем загрузки результатов
        
        # Парсим результаты поиска
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        # Ищем все ссылки на Instagram в результатах поиска
        instagram_pattern = r'https?://(?:www\.)?instagram\.com/([a-zA-Z0-9_.]+)'
        matches = re.findall(instagram_pattern, page_source)
        
        if verbose:
            print(f"\n📊 Найдено упоминаний Instagram: {len(matches)}")
        
        # Фильтруем результаты и считаем частоту упоминаний
        username_counts = {}
        for username in matches:
            # Пропускаем служебные страницы
            if username not in ['p', 'reel', 'stories', 'explore', 'accounts', 'direct', 'www', 'about', 'blog']:
                username_counts[username] = username_counts.get(username, 0) + 1
        
        # Также ищем в ссылках результатов поиска
        try:
            # Ищем ссылки в результатах поиска Google
            search_results = driver.find_elements(By.CSS_SELECTOR, 'a[href*="instagram.com"]')
            for link in search_results:
                href = link.get_attribute('href')
                if href:
                    match = re.search(r'instagram\.com/([a-zA-Z0-9_.]+)', href)
                    if match:
                        username = match.group(1)
                        if username not in ['p', 'reel', 'stories', 'explore', 'accounts', 'direct', 'www']:
                            username_counts[username] = username_counts.get(username, 0) + 1
        except Exception as e:
            if verbose:
                print(f"   Ошибка при поиске в ссылках: {e}")
        
        driver.quit()
        
        if not username_counts:
            if verbose:
                print("\n❌ Instagram не найден в результатах поиска")
            return None
        
        # Сортируем по частоте упоминаний (самый частый первым)
        sorted_usernames = sorted(username_counts.items(), key=lambda x: x[1], reverse=True)
        
        if verbose:
            print(f"\n📊 Найдено {len(username_counts)} уникальных аккаунтов:")
            for username, count in sorted_usernames[:5]:  # Показываем топ-5
                print(f"   {username}: {count} упоминаний")
        
        # Выбираем наиболее релевантный аккаунт
        # Приоритет: аккаунт с названием города или наиболее частый
        best_username = None
        city_lower = city.lower()
        
        # Сначала ищем аккаунт с упоминанием города
        for username, count in sorted_usernames:
            if city_lower in username.lower() or 'msk' in username.lower() or 'moscow' in username.lower():
                best_username = username
                if verbose:
                    print(f"   ✅ Выбран аккаунт с упоминанием города: {username}")
                break
        
        # Если не нашли с городом, берем самый частый
        if not best_username:
            best_username = sorted_usernames[0][0]
            if verbose:
                print(f"   ✅ Выбран наиболее частый аккаунт: {best_username}")
        
        instagram_url = f"https://www.instagram.com/{best_username}/"
        if verbose:
            print(f"\n✅ Найден Instagram: {instagram_url}")
        return instagram_url
            
    except Exception as e:
        print(f"❌ Ошибка при поиске: {e}")
        if driver:
            try:
                driver.quit()
            except:
                pass
        return None


def find_instagram_from_yandex_url(yandex_url: str, city: str = "Москва") -> Optional[str]:
    """
    Ищет Instagram для заведения по ссылке Яндекс.Карт
    
    Алгоритм:
    1. Парсит название заведения из ссылки Яндекс.Карт
    2. Ищет Instagram через Google поиск по запросу: "название + город + instagram"
    
    Args:
        yandex_url: Ссылка на Яндекс.Карты
        city: Город для поиска (по умолчанию "Москва")
    
    Returns:
        Ссылка на Instagram или None
    """
    print(f"🔍 Ищу Instagram для: {yandex_url}")
    print("=" * 60)
    
    # Шаг 1: Парсим название заведения
    print("📄 Шаг 1: Парсинг названия заведения...")
    try:
        from yandex_parser import parse_yandex
        place_data = parse_yandex(yandex_url)
        name = place_data.get('title')
        
        if not name or name == "Название не найдено":
            print("❌ Не удалось извлечь название заведения")
            return None
        
        print(f"✅ Название: {name}")
        print(f"📍 Город: {city}")
        categories = place_data.get('categories')
        if categories:
            print(f"🏷️  Категории: {categories}")
        
    except Exception as e:
        print(f"❌ Ошибка при парсинге: {e}")
        import traceback
        traceback.print_exc()
        return None
    
    # Шаг 2: Ищем Instagram через Google
    print(f"\n🔎 Шаг 2: Поиск Instagram через Google...")
    instagram_url = find_instagram_via_google(name, city, categories)
    
    return instagram_url


def main():
    """Тестовая функция"""
    # Тестовая ссылка
    test_url = "https://yandex.ru/maps/org/stim_coffee/54162905237/"
    
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    
    result = find_instagram_from_yandex_url(test_url)
    
    print("\n" + "=" * 60)
    if result:
        print(f"🎉 Результат: {result}")
        return result
    else:
        print("😞 Instagram не найден")
        return None


if __name__ == "__main__":
    main()

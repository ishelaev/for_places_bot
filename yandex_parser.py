import re
import time
import random
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

day_map = {
    "Mo": "Пн",
    "Tu": "Вт",
    "We": "Ср",
    "Th": "Чт",
    "Fr": "Пт",
    "Sa": "Сб",
    "Su": "Вс"
}

def get_review_form(count):
    """Возвращает правильную форму слова 'отзыв' в зависимости от числа"""
    count = int(count)
    if count % 10 == 1 and count % 100 != 11:
        return f"{count} отзыв"
    elif 2 <= count % 10 <= 4 and (count % 100 < 10 or count % 100 >= 20):
        return f"{count} отзыва"
    else:
        return f"{count} отзывов"

def parse_yandex_requests(url: str) -> dict:
    """Парсинг через requests (быстро, но может не сработать)"""
    try:
        import requests
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Проверка на капчу
        title_tag = soup.find('h1')
        title = title_tag.text.strip() if title_tag else ""
        
        # Проверяем на капчу (более точная детекция)
        if "ð¾ð´ñð²ð" in title or "ñð¾ð±ð¾ñ" in title or len(title) > 50:
            return None  # Капча обнаружена
        
        # Если всё ок - парсим ВСЕ данные как в Selenium версии
        
        # ===== Рейтинг =====
        rating = None
        rating_tag = soup.select_one("span.business-rating-badge-view__rating-text")
        if rating_tag:
            rating = rating_tag.get_text(strip=True)
        
        # ===== Отзывы =====
        reviews = None
        reviews_tag = soup.select_one("meta[itemprop='reviewCount']")
        if reviews_tag:
            reviews = reviews_tag.get("content")
            if reviews:
                reviews = get_review_form(reviews)
        
        # ===== Координаты =====
        latitude = longitude = None
        
        # Метод 1: через атрибут data-coordinates
        el = soup.select_one('[data-coordinates]')
        if el and el.get('data-coordinates'):
            try:
                lon_str, lat_str = el['data-coordinates'].split(',', 1)
                longitude = float(lon_str.strip())
                latitude = float(lat_str.strip())
            except Exception:
                pass
        
        # Метод 2: через regex на странице (data-coordinates)
        if latitude is None or longitude is None:
            m = re.search(r'data-coordinates="([\-0-9\.]+),([\-0-9\.]+)"', response.text)
            if m:
                try:
                    longitude = float(m.group(1))
                    latitude = float(m.group(2))
                except Exception:
                    pass
        
        # Метод 3: через JSON данные на странице (координаты в структурированных данных)
        if latitude is None or longitude is None:
            # Ищем JSON с координатами в тексте страницы
            json_patterns = [
                r'"coordinates":\s*\[([\-0-9\.]+),\s*([\-0-9\.]+)\]',
                r'"lat":\s*([\-0-9\.]+).*?"lon":\s*([\-0-9\.]+)',
                r'"lon":\s*([\-0-9\.]+).*?"lat":\s*([\-0-9\.]+)',
                r'latitude["\']?\s*[:=]\s*([\-0-9\.]+).*?longitude["\']?\s*[:=]\s*([\-0-9\.]+)',
                r'longitude["\']?\s*[:=]\s*([\-0-9\.]+).*?latitude["\']?\s*[:=]\s*([\-0-9\.]+)',
            ]
            for pattern in json_patterns:
                m = re.search(pattern, response.text, re.IGNORECASE | re.DOTALL)
                if m:
                    try:
                        if 'lat' in pattern.lower() or 'latitude' in pattern.lower():
                            latitude = float(m.group(1))
                            longitude = float(m.group(2))
                        else:
                            longitude = float(m.group(1))
                            latitude = float(m.group(2))
                        break
                    except Exception:
                        continue
        
        # Метод 4: через URL параметры (если есть в URL)
        if latitude is None or longitude is None:
            m = re.search(r'[?&]ll=([\-0-9\.]+),([\-0-9\.]+)', url)
            if m:
                try:
                    longitude = float(m.group(1))
                    latitude = float(m.group(2))
                except Exception:
                    pass
        
        # Метод 5: через meta теги с геокоординатами
        if latitude is None or longitude is None:
            geo_lat = soup.select_one('meta[property="place:location:latitude"]')
            geo_lon = soup.select_one('meta[property="place:location:longitude"]')
            if geo_lat and geo_lon:
                try:
                    latitude = float(geo_lat.get('content', ''))
                    longitude = float(geo_lon.get('content', ''))
                except Exception:
                    pass
        
        # ===== Часы работы =====
        hours = {}
        hours_tags = soup.select("meta[itemprop='openingHours']")
        for tag in hours_tags:
            content = tag.get("content")
            if not content:
                continue
            match = re.match(r"([A-Za-z]{2}) (.+)", content)
            if match:
                eng_day, time_range = match.groups()
                ru_day = day_map.get(eng_day, eng_day)
                hours[ru_day] = time_range
        
        # ===== Категории =====
        categories = None
        categories_tags = soup.select("a.orgpage-categories-info-view__link span.button__text")
        if categories_tags:
            parts = [tag.get_text(strip=True) for tag in categories_tags if tag.get_text(strip=True)]
            if parts:
                categories = ", ".join(parts)
        
        result = {
            "title": title or "Название не найдено",
            "rating": rating or "Рейтинг не найден",
            "reviews": reviews or "Отзывы не найдены",
            "coordinates": (latitude, longitude) if latitude is not None and longitude is not None else None,
            "hours": hours,
            "categories": categories
        }
        return result
        
    except Exception:
        return None

def parse_yandex_selenium(url: str) -> dict:
    # --- Настройка Selenium ---
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    
    # Маскировка под обычный браузер
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    options.add_argument(f"--remote-debugging-port={random.randint(9000, 9999)}")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-plugins")
    
    # Отключаем webdriver режим
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    driver = webdriver.Chrome(options=options)
    driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
    
    # Имитируем человеческое поведение
    driver.get(url)
    time.sleep(2)  # Минимальная задержка для загрузки страницы

    # ===== Название =====
    title = None
    try:
        title = driver.find_element(By.TAG_NAME, "h1").text.strip()
    except:
        pass

    # Получаем страницу для BeautifulSoup
    soup = BeautifulSoup(driver.page_source, "html.parser")

    # ===== Рейтинг =====
    rating = None
    rating_tag = soup.select_one("span.business-rating-badge-view__rating-text")
    if rating_tag:
        rating = rating_tag.get_text(strip=True)

    # ===== Отзывы =====
    reviews = None
    reviews_tag = soup.select_one("meta[itemprop='reviewCount']")
    if reviews_tag:
        reviews = reviews_tag.get("content")
        if reviews:
            reviews = get_review_form(reviews)

    # ===== Координаты (lon,lat → lat,lon float) =====
    latitude = longitude = None
    el = soup.select_one('[data-coordinates]')
    if el and el.get('data-coordinates'):
        try:
            lon_str, lat_str = el['data-coordinates'].split(',', 1)
            longitude = float(lon_str.strip())
            latitude = float(lat_str.strip())
        except Exception:
            pass

    # fallback через regex на странице
    if latitude is None or longitude is None:
        m = re.search(r'data-coordinates="([\-0-9\.]+),([\-0-9\.]+)"', driver.page_source)
        if m:
            try:
                longitude = float(m.group(1))
                latitude = float(m.group(2))
            except Exception:
                pass

    # fallback через URL
    if latitude is None or longitude is None:
        m = re.search(r'[?&]ll=([\-0-9\.]+),([\-0-9\.]+)', driver.current_url)
        if m:
            try:
                longitude = float(m.group(1))
                latitude = float(m.group(2))
            except Exception:
                pass

    # ===== Часы работы =====
    hours = {}
    hours_tags = soup.select("meta[itemprop='openingHours']")
    for tag in hours_tags:
        content = tag.get("content")
        if not content:
            continue
        match = re.match(r"([A-Za-z]{2}) (.+)", content)
        if match:
            eng_day, time_range = match.groups()
            ru_day = day_map.get(eng_day, eng_day)
            hours[ru_day] = time_range

    # ===== Категории =====
    categories = None
    categories_tags = soup.select("a.orgpage-categories-info-view__link span.button__text")
    if categories_tags:
        parts = [tag.get_text(strip=True) for tag in categories_tags if tag.get_text(strip=True)]
        if parts:
            categories = ", ".join(parts)


    driver.quit()
    
    result = {
        "title": title or "Название не найдено",
        "rating": rating or "Рейтинг не найден",
        "reviews": reviews or "Отзывы не найдены",
        "coordinates": (latitude, longitude) if latitude is not None and longitude is not None else None,
        "hours": hours,
        "categories": categories
    }
    
    return result

def parse_yandex(url: str) -> dict:
    """
    Умный парсер с fallback методами
    1. Сначала пробует быстрый requests
    2. Если не работает - использует Selenium
    """
    print("🔄 Пробую быстрый метод (requests)...")
    result = parse_yandex_requests(url)
    
    if result is not None:
        print("✅ Requests сработал!")
        # Не парсим тексты отзывов - они не нужны для основной информации
        return result
    
    print("🔄 Requests не сработал, пробую Selenium...")
    return parse_yandex_selenium(url)

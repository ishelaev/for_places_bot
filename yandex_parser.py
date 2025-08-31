import re
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

day_map = {
    "Mo": "Пн",
    "Tu": "Вт",
    "We": "Ср",
    "Th": "Чт",
    "Fr": "Пт",
    "Sa": "Сб",
    "Su": "Вс"
}

def parse_yandex(url: str) -> dict:
    # --- Настройка Selenium ---
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(2)  # ждём загрузки

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
            reviews = f"{reviews} отзывов"

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

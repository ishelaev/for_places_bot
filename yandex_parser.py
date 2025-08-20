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
    driver.quit()

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

    # ===== Координаты =====
    coordinates = None
    coords_tag = soup.select_one("div.search-placemark-view")
    if coords_tag:
        coords = coords_tag.get("data-coordinates")
        if coords:
            lon, lat = coords.split(",")
            coordinates = f"{lat.strip()}, {lon.strip()}"

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

    return {
        "title": title or "Название не найдено",
        "rating": rating or "Рейтинг не найден",
        "reviews": reviews or "Отзывы не найдены",
        "coordinates": coordinates or "Координаты не найдены",
        "hours": hours
    }

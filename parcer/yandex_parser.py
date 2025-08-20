# parser/yandex_parser.py
import re
import time
from typing import Optional, Dict, List

from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By

# Соответствие кодов дней в meta openingHours → русским аббревиатурам
day_map = {
    "Mo": "Пн",
    "Tu": "Вт",
    "We": "Ср",
    "Th": "Чт",
    "Fr": "Пт",
    "Sa": "Сб",
    "Su": "Вс",
}
weekday_columns = list(day_map.values())

def russian_plural_reviews(n: int) -> str:
    n_abs = abs(n) % 100
    last = n_abs % 10
    if 11 <= n_abs <= 14:
        form = "отзывов"
    elif last == 1:
        form = "отзыв"
    elif 2 <= last <= 4:
        form = "отзыва"
    else:
        form = "отзывов"
    return f"{n} {form}"

def expand_day_codes(code: str) -> List[str]:
    order = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
    if "-" in code:
        start, end = code.split("-", 1)
        try:
            i, j = order.index(start), order.index(end)
        except ValueError:
            return []
        if i <= j:
            return order[i:j + 1]
        return order[i:] + order[:j + 1]
    return [code]

def clean_place_name(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    txt = raw.strip()
    # Срезаем хвост "— Яндекс Карты" (учитываем неразрывный пробел)
    txt = re.sub(r"\s+—\s+Яндекс(?:\xa0| )?Карты.*$", "", txt)
    # В title часто "Brand, ресторан, адрес" — берём бренд до первой запятой
    head, *_ = [p.strip() for p in txt.split(",")]
    return head or txt

def parse_yandex_place(url: str, driver, wait: WebDriverWait) -> Dict[str, Optional[str]]:
    """Открывает карточку Яндекса и вытаскивает основные поля."""
    driver.set_window_size(1200, 1000)
    driver.get(url)
    time.sleep(4)  # даём странице догрузиться

    # ждём появления рейтинга как сигнала загрузки карточки
    wait.until(EC.presence_of_element_located((By.CLASS_NAME, "business-rating-badge-view__rating-text")))
    page_html = driver.page_source
    soup = BeautifulSoup(page_html, "html.parser")

    # ===== Название =====
    name = None
    meta_title = soup.find("meta", {"property": "og:title"})
    if meta_title and meta_title.get("content"):
        name = clean_place_name(meta_title["content"])
    if not name:
        title_tag = soup.find("title")
        if title_tag and title_tag.get_text(strip=True):
            name = clean_place_name(title_tag.get_text(strip=True))
    if not name:
        h1 = soup.select_one("h1.orgpage-header-view__header, h1.business-card-title-view__header, h1 span")
        if h1:
            name = h1.get_text(strip=True)

    # ===== Рейтинг =====
    rating = None
    rating_tag = soup.select_one("span.business-rating-badge-view__rating-text")
    if rating_tag:
        rating = rating_tag.get_text(strip=True) or None

    # ===== Отзывы =====
    reviews = None
    meta_desc = soup.find("meta", {"property": "og:description"})
    if meta_desc and meta_desc.get("content"):
        text = meta_desc["content"]
        m = re.search(r"(\d+)\s+отзыв", text, flags=re.IGNORECASE)
        if m:
            try:
                num = int(m.group(1))
                reviews = russian_plural_reviews(num)
            except ValueError:
                pass
    if reviews is None:
        reviews_tag = soup.select_one("div.business-header-rating-view__text._clickable")
        if reviews_tag:
            raw = reviews_tag.get_text(strip=True)
            digits = re.findall(r"\d+", raw)
            if digits:
                try:
                    num = int(digits[0])
                    reviews = russian_plural_reviews(num)
                except ValueError:
                    pass

    # ===== Категории =====
    categories = None
    categories_tags = soup.select("a.orgpage-categories-info-view__link span.button__text")
    if categories_tags:
        parts = [tag.get_text(strip=True) for tag in categories_tags if tag.get_text(strip=True)]
        if parts:
            categories = ", ".join(parts)

    # ===== Координаты (lon,lat в data-coordinates) → (lat, lon) =====
    latitude = longitude = None
    el = soup.select_one('[data-coordinates]')
    if el and el.get('data-coordinates'):
        try:
            lon_str, lat_str = el['data-coordinates'].split(',', 1)
            longitude = float(lon_str.strip())
            latitude = float(lat_str.strip())
        except Exception:
            pass
    if latitude is None or longitude is None:
        m = re.search(r'data-coordinates="([\-0-9\.]+),([\-0-9\.]+)"', page_html)
        if m:
            try:
                longitude = float(m.group(1))
                latitude = float(m.group(2))
            except Exception:
                pass
    if latitude is None or longitude is None:
        m = re.search(r'[?&]ll=([\-0-9\.]+),([\-0-9\.]+)', driver.current_url)
        if m:
            try:
                longitude = float(m.group(1))
                latitude = float(m.group(2))
            except Exception:
                pass

    # ===== График работы =====
    schedule = {ru_day: "Не работает" for ru_day in day_map.values()}
    opening_tags = soup.select('meta[itemprop="openingHours"]')
    for tag in opening_tags:
        content = tag.get('content')
        if not content:
            continue
        parts = content.split()
        if len(parts) != 2:
            continue
        day_code_raw, hours = parts
        day_chunks = [c.strip() for c in re.split(r"[,\s]+", day_code_raw) if c.strip()]
        all_day_codes: List[str] = []
        for chunk in day_chunks:
            all_day_codes.extend(expand_day_codes(chunk))
        for code in all_day_codes:
            ru_day = day_map.get(code)
            if ru_day:
                schedule[ru_day] = hours or "Не работает"

    return {
        "Название": name,
        "Рейтинг": rating,
        "Отзывы": reviews,
        "Категории": categories,
        "Широта": latitude,
        "Долгота": longitude,
        **schedule
    }

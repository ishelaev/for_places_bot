import time
import re
import asyncio
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# ------------------- Функция для склонения слова "отзыв" -------------------
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

# ------------------- Функция для парсинга Яндекс.Карт -------------------
def get_yandex_place_info(url):
    options = Options()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    print(f"Загружаем страницу: {url}")
    driver.get(url)
    time.sleep(3)  # Ждём, пока загрузится страница

    info = {
        "title": "Название не найдено",
        "rating": "Рейтинг не найден",
        "address": "Адрес не найден",
        "reviews": "Отзывы не найдены"
    }

    # Название
    try:
        info["title"] = driver.find_element(By.XPATH, "//h1").text
        print("Название:", info["title"])
    except:
        pass

    # Рейтинг
    try:
        meta_desc = driver.find_element(By.XPATH, "//meta[@property='og:description']").get_attribute("content")
        rating_match = re.search(r"Рейтинг ([\d,.]+)", meta_desc)
        if rating_match:
            info["rating"] = rating_match.group(1)
        print("Рейтинг:", info["rating"])
    except:
        pass

    # Адрес
    try:
        info["address"] = driver.find_element(By.XPATH, "//div[contains(@class,'business-contacts-view__address')]").text
        print("Адрес:", info["address"])
    except:
        pass

    # Количество отзывов
    try:
        review_meta = driver.find_element(By.XPATH, "//meta[@itemprop='reviewCount']")
        count = int(review_meta.get_attribute("content"))
        info["reviews"] = russian_plural_reviews(count)
        print("Отзывы:", info["reviews"])
    except:
        pass

    driver.quit()
    return info

# ------------------- Телеграм-бот -------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли ссылку на Яндекс.Карты, и я покажу информацию о месте."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    match = re.search(r"https?://yandex\.ru/maps/[^\s]+", text)
    if not match:
        await update.message.reply_text("Пожалуйста, пришли ссылку на Яндекс.Карты.")
        return

    url = match.group(0)
    await update.message.reply_text("Ищу информацию, подождите... ⏳")
    info = get_yandex_place_info(url)

    reply_text = (
        f"Название: {info['title']}\n"
        f"Рейтинг: {info['rating']}\n"
        f"Адрес: {info['address']}\n"
        f"Отзывы: {info['reviews']}"
    )
    await update.message.reply_text(reply_text)

# ------------------- Тестовая функция для терминала -------------------
async def test_terminal(url):
    print("=== Тестируем парсер ===")
    info = get_yandex_place_info(url)
    print("Результаты:")
    for k, v in info.items():
        print(f"{k}: {v}")

# ------------------- Запуск бота или теста -------------------
if __name__ == "__main__":
    TEST_MODE = False# True = тест в терминале, False = запуск бота

    if TEST_MODE:
        test_url = "https://yandex.ru/maps/org/nostalgia/69611047747/"
        asyncio.run(test_terminal(test_url))
    else:
        TOKEN = "8478245526:AAHAua7Xnr2CIt2xg_zjfaqk7HVPOCt2Nxw"
        app = ApplicationBuilder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

        print("Бот запущен...")
        app.run_polling()

import time
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes
import re


# --------- Функция для парсинга Яндекс.Карт ---------
def get_yandex_place_info(url):
    options = Options()
    options.headless = True  # Браузер не открывается
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=options)
    driver.get(url)
    time.sleep(3)  # Ждем, пока загрузится страница

    info = {
        "title": "Название не найдено",
        "rating": "Рейтинг не найден",
        "address": "Адрес не найден",
        "phone": "Телефон не найден",
    }

    try:
        info["title"] = driver.find_element(By.XPATH, "//h1").text
    except:
        pass

    try:
        info["rating"] = driver.find_element(By.XPATH, "//span[contains(@class,'rating__value')]").text
    except:
        pass

    try:
        info["address"] = driver.find_element(By.XPATH, "//div[contains(@class,'business-contacts-view__address')]").text
    except:
        pass

    try:
        info["phone"] = driver.find_element(By.XPATH, "//a[contains(@href,'tel:')]").text
    except:
        pass

    driver.quit()
    return info

# --------- Телеграм-бот ---------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Пришли ссылку на Яндекс.Карты, и я покажу информацию о месте."
    )

async def handle_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    # Ищем ссылку на Яндекс.Карты в тексте
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
        f"Телефон: {info['phone']}\n"
    )
    await update.message.reply_text(reply_text)

# --------- Запуск бота ---------
if __name__ == "__main__":
    TOKEN = "8478245526:AAHAua7Xnr2CIt2xg_zjfaqk7HVPOCt2Nxw"
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_link))

    print("Бот запущен...")
    app.run_polling()

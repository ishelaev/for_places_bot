from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters
from text_input import handle_text  # наш обработчик ссылок

# Стартовое сообщение
async def start(update, context):
    await update.message.reply_text(
        "Привет! Пришли ссылку на Яндекс.Карты 📍, "
        "и я верну всю информацию о месте: название, рейтинг, отзывы, координаты и часы работы."
    )

if __name__ == "__main__":
    TOKEN = "8478245526:AAHAua7Xnr2CIt2xg_zjfaqk7HVPOCt2Nxw"  # сюда вставь токен своего бота
    app = ApplicationBuilder().token(TOKEN).build()

    # Обработчики
    app.add_handler(CommandHandler("start", start))  # команда /start
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text)
    )  # ловим ссылки и текст

    print("Бот запущен...")
    app.run_polling()

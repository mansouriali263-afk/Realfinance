# ملف simple_bot.py
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get('BOT_TOKEN')  # أو ضع التوكن هنا مباشرة

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت يعمل!")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ البوت بدأ العمل...")
    app.run_polling()

if __name__ == '__main__':
    main()

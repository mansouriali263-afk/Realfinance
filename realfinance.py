#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
نسخة تجريبية مبسطة للبوت - للتحقق من الاستجابة
"""

import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# تفعيل التسجيل
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# توكن البوت - وضعته مباشرة هنا للتجربة
BOT_TOKEN = "8720874613:AAF1tACw5nzGS6qg7NMLD3avIDQxjeA0UMU"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    await update.message.reply_text(
        f"✅ *مرحباً {user.first_name}!*\n\n"
        f"البوت يعمل بنجاح!\n"
        f"معرفك: `{user.id}`",
        parse_mode='Markdown'
    )
    print(f"👤 مستخدم جديد: {user.first_name} (@{user.username}) - ID: {user.id}")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    await update.message.reply_text(
        "📋 *الأوامر المتاحة:*\n"
        "/start - بدء البوت\n"
        "/help - عرض المساعدة",
        parse_mode='Markdown'
    )

def main():
    """تشغيل البوت"""
    print("🤖 جاري تشغيل البوت التجريبي...")
    print(f"📱 التوكن: {BOT_TOKEN[:15]}...")
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    
    print("✅ البوت جاهز! اضغط Ctrl+C للإيقاف")
    print("🚀 انتظر البدء...")
    
    # بدء البوت
    application.run_polling()

if __name__ == '__main__':
    main()

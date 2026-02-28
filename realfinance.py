#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
بوت REFi للإحالة والأرباح - نسخة مبسطة
التوكن: 8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs
"""

import os
import logging
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler
)

# ==================== إعدادات التسجيل ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== إعدادات البوت ====================
BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"  # التوكن الجديد

# إعدادات المشرفين
ADMIN_IDS = [1653918641]  # معرف المشرف
ADMIN_PASSWORD = "Ali97$"  # كلمة سر المشرف

# ==================== إعدادات العملة ====================
COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000  # 1 مليون REFi
REFERRAL_BONUS = 1_000_000  # 1 مليون REFi لكل إحالة
MIN_WITHDRAW = 5_000_000  # 5 مليون REFi كحد أدنى للسحب

# ==================== إعدادات القنوات المطلوبة ====================
REQUIRED_CHANNELS = [
    {
        "name": "Realfinance_REFI",
        "link": "https://t.me/Realfinance_REFI",
        "username": "@Realfinance_REFI"
    },
    {
        "name": "Airdrop_MasterVIP",
        "link": "https://t.me/Airdrop_MasterVIP",
        "username": "@Airdrop_MasterVIP"
    },
    {
        "name": "Daily_AirdropX",
        "link": "https://t.me/Daily_AirdropX",
        "username": "@Daily_AirdropX"
    }
]

# ==================== دوال مساعدة ====================

def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}"

def refi_to_usd(refi_amount: int) -> float:
    """تحويل REFi إلى دولار (1 مليون = $2)"""
    return (refi_amount / 1_000_000) * 2.00

def generate_referral_code(user_id: int) -> str:
    """توليد كود إحالة فريد"""
    code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
    return code.upper()

# ==================== تخزين مؤقت (بدون Firebase) ====================
users_db = {}  # قاموس مؤقت بدلاً من Firebase
admin_sessions = {}  # جلسات المشرفين
user_states = {}  # حالات المستخدمين

def get_user_data(user_id: int) -> Dict:
    """جلب بيانات مستخدم من الذاكرة المؤقتة"""
    return users_db.get(str(user_id), {})

def save_user_data(user_id: int, data: Dict) -> bool:
    """حفظ بيانات مستخدم في الذاكرة المؤقتة"""
    users_db[str(user_id)] = data
    return True

# ==================== لوحات المفاتيح ====================

def get_channels_keyboard() -> InlineKeyboardMarkup:
    """أزرار القنوات للانضمام"""
    keyboard = []
    for channel in REQUIRED_CHANNELS:
        keyboard.append([InlineKeyboardButton(
            text=f"📢 انضم إلى {channel['name']}",
            url=channel['link']
        )])
    keyboard.append([InlineKeyboardButton(
        text="✅ تحقق من الانضمام",
        callback_data="verify"
    )])
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard() -> InlineKeyboardMarkup:
    """القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
            InlineKeyboardButton("🔗 الإحالة", callback_data="referral")
        ],
        [
            InlineKeyboardButton("💸 السحب", callback_data="withdraw"),
            InlineKeyboardButton("📊 الإحصائيات", callback_data="stats")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== معالجات الأوامر ====================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    user = update.effective_user
    args = context.args
    
    # رسالة ترحيب فورية للتأكد من استجابة البوت
    await update.message.reply_text(
        f"✅ مرحباً {user.first_name}! البوت يعمل.\n"
        f"معرفك: `{user.id}`",
        parse_mode='Markdown'
    )
    
    # التحقق من وجود كود إحالة
    referral_code = args[0] if args else None
    
    # بيانات المستخدم
    user_data = get_user_data(user.id)
    
    if not user_data:
        # مستخدم جديد
        user_data = {
            'user_id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'joined_at': time.time(),
            'balance': 0,
            'total_earned': 0,
            'referral_code': generate_referral_code(user.id),
            'referred_by': None,
            'referrals_count': 0,
            'is_verified': False
        }
        
        # معالجة الإحالة
        if referral_code:
            # البحث عن صاحب الكود
            for uid, data in users_db.items():
                if data.get('referral_code') == referral_code and int(uid) != user.id:
                    user_data['referred_by'] = int(uid)
                    break
        
        save_user_data(user.id, user_data)
    
    # عرض القنوات المطلوبة
    channels_text = "\n".join([f"• {ch['name']}: {ch['link']}" for ch in REQUIRED_CHANNELS])
    
    await update.message.reply_text(
        f"🎉 *مرحباً بك في بوت {COIN_NAME}!*\n\n"
        f"💰 مكافأة الترحيب: {format_number(WELCOME_BONUS)} {COIN_NAME}\n"
        f"👥 مكافأة الإحالة: {format_number(REFERRAL_BONUS)} {COIN_NAME} لكل صديق\n\n"
        f"📢 للبدء، اشترك في هذه القنوات:\n{channels_text}",
        reply_markup=get_channels_keyboard(),
        parse_mode='Markdown'
    )

async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دخول المشرف"""
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ غير مصرح")
        return
    
    # تسجيل دخول بسيط (بدون كلمة سر للتجربة)
    admin_sessions[user.id] = time.time() + 3600
    await update.message.reply_text("✅ مرحباً بك في لوحة المشرف")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)
    
    if data == "verify":
        # تحقق بسيط (دون التحقق الفعلي من القنوات للتجربة)
        if not user_data.get('is_verified', False):
            user_data['balance'] = user_data.get('balance', 0) + WELCOME_BONUS
            user_data['total_earned'] = user_data.get('total_earned', 0) + WELCOME_BONUS
            user_data['is_verified'] = True
            save_user_data(user_id, user_data)
            
            # معالجة إحالة المحيل
            referred_by = user_data.get('referred_by')
            if referred_by:
                referrer_data = get_user_data(referred_by)
                if referrer_data:
                    referrer_data['balance'] = referrer_data.get('balance', 0) + REFERRAL_BONUS
                    referrer_data['total_earned'] = referrer_data.get('total_earned', 0) + REFERRAL_BONUS
                    referrer_data['referrals_count'] = referrer_data.get('referrals_count', 0) + 1
                    save_user_data(referred_by, referrer_data)
        
        await query.edit_message_text(
            f"✅ *تم التحقق بنجاح!*\n\n"
            f"💰 رصيدك: {format_number(user_data['balance'])} {COIN_NAME}\n"
            f"💵 القيمة: ${refi_to_usd(user_data['balance']):.2f}",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )
    
    elif data == "balance":
        balance = user_data.get('balance', 0)
        await query.edit_message_text(
            f"💰 *رصيدك*\n\n"
            f"{format_number(balance)} {COIN_NAME}\n"
            f"${refi_to_usd(balance):.2f}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
    
    elif data == "referral":
        referral_code = user_data.get('referral_code', generate_referral_code(user_id))
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={referral_code}"
        
        await query.edit_message_text(
            f"🔗 *رابط الإحالة*\n\n"
            f"`{link}`\n\n"
            f"لكل صديق يسجل، تكسب {format_number(REFERRAL_BONUS)} {COIN_NAME}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
    
    elif data == "withdraw":
        balance = user_data.get('balance', 0)
        
        if balance < MIN_WITHDRAW:
            await query.edit_message_text(
                f"⚠️ الحد الأدنى للسحب: {format_number(MIN_WITHDRAW)} {COIN_NAME}\n"
                f"رصيدك الحالي: {format_number(balance)} {COIN_NAME}",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="back")
                ]]),
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"💰 رصيدك: {format_number(balance)} {COIN_NAME}\n\n"
                f"للسحب، أرسل المبلغ الذي تريده",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("🔙 رجوع", callback_data="back")
                ]])
            )
            context.user_data['waiting_withdraw'] = True
    
    elif data == "stats":
        await query.edit_message_text(
            f"📊 *إحصائياتك*\n\n"
            f"• الرصيد: {format_number(user_data.get('balance', 0))} {COIN_NAME}\n"
            f"• الإجمالي: {format_number(user_data.get('total_earned', 0))} {COIN_NAME}\n"
            f"• الإحالات: {user_data.get('referrals_count', 0)}\n"
            f"• موثق: {'✅' if user_data.get('is_verified') else '❌'}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("🔙 رجوع", callback_data="back")
            ]]),
            parse_mode='Markdown'
        )
    
    elif data == "back":
        await query.edit_message_text(
            f"💰 رصيدك: {format_number(user_data.get('balance', 0))} {COIN_NAME}\n"
            f"💵 القيمة: ${refi_to_usd(user_data.get('balance', 0)):.2f}",
            reply_markup=get_main_keyboard(),
            parse_mode='Markdown'
        )

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج الرسائل النصية"""
    user_id = update.effective_user.id
    
    if context.user_data.get('waiting_withdraw'):
        try:
            amount = int(update.message.text)
            user_data = get_user_data(user_id)
            
            if amount < MIN_WITHDRAW:
                await update.message.reply_text(f"الحد الأدنى {format_number(MIN_WITHDRAW)} {COIN_NAME}")
            elif amount > user_data.get('balance', 0):
                await update.message.reply_text("رصيد غير كاف")
            else:
                # خصم الرصيد
                user_data['balance'] -= amount
                save_user_data(user_id, user_data)
                
                await update.message.reply_text(
                    f"✅ تم تقديم طلب سحب {format_number(amount)} {COIN_NAME}"
                )
                
                # إشعار المشرف
                for admin_id in ADMIN_IDS:
                    try:
                        await context.bot.send_message(
                            admin_id,
                            f"💰 طلب سحب جديد\n"
                            f"المستخدم: {user_id}\n"
                            f"المبلغ: {format_number(amount)} {COIN_NAME}"
                        )
                    except:
                        pass
            
            context.user_data['waiting_withdraw'] = False
            
        except ValueError:
            await update.message.reply_text("الرجاء إدخال رقم صحيح")

# ==================== تشغيل البوت ====================

def main():
    """الدالة الرئيسية"""
    print("=" * 50)
    print("🤖 بوت REFi - نسخة مبسطة")
    print("=" * 50)
    print(f"📱 التوكن: {BOT_TOKEN[:15]}...")
    print(f"👤 المشرف: {ADMIN_IDS[0]}")
    print(f"💰 مكافأة الترحيب: {format_number(WELCOME_BONUS)} {COIN_NAME}")
    print(f"👥 مكافأة الإحالة: {format_number(REFERRAL_BONUS)} {COIN_NAME}")
    print(f"💸 الحد الأدنى للسحب: {format_number(MIN_WITHDRAW)} {COIN_NAME}")
    print("=" * 50)
    print("🚀 جاري تشغيل البوت...")
    
    # إنشاء التطبيق
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", admin))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    print("✅ البوت جاهز! اضغط Ctrl+C للإيقاف")
    print("=" * 50)
    
    # بدء البوت
    app.run_polling()

if __name__ == '__main__':
    main()

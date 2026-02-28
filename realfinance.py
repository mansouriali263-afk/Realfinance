#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
بوت تيليجرام للإحالة والأرباح - عملة REFi
الإصدار: 1.0.0
المطور: بناءً على متطلبات المشرف
"""

import os
import logging
import time
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional, Tuple, List, Any
from functools import wraps

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

import firebase_admin
from firebase_admin import credentials, db

# ==================== إعدادات التسجيل ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== إعدادات البوت ====================

# التوكن - من متغيرات البيئة فقط (GitHub Secrets)
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("❌ BOT_TOKEN غير موجود! أضفه في GitHub Secrets")

# إعدادات المشرفين (مكشوفة في الكود)
ADMIN_IDS = [1653918641]  # معرف المشرف
ADMIN_PASSWORD = "Ali97$"  # كلمة سر المشرف

# ==================== إعدادات Firebase (مكشوفة) ====================
FIREBASE_CONFIG = {
    "apiKey": "AIzaSyAo1zUpkMiaB3HmIDQkirqcTxhxIUF0tF0",
    "authDomain": "realfinance-9af90.firebaseapp.com",
    "databaseURL": "https://realfinance-9af90-default-rtdb.firebaseio.com/",
    "projectId": "realfinance-9af90",
    "storageBucket": "realfinance-9af90.firebasestorage.app",
    "messagingSenderId": "921539332721",
    "appId": "1:921539332721:web:24fa696c7b0f035878e9d0"
}

# ==================== إعدادات العملة ====================
COIN_NAME = "REFi"
COIN_PRICE = 0.000002  # 1 REFi = $0.000002 (1 مليون = $2)
WELCOME_BONUS = 1_000_000  # 1 مليون REFi
REFERRAL_BONUS = 1_000_000  # 1 مليون REFi لكل إحالة
MIN_WITHDRAW = 5_000_000  # 5 مليون REFi كحد أدنى للسحب

# ==================== إعدادات القنوات المطلوبة ====================
REQUIRED_CHANNELS = [
    {
        "name": "Realfinance_REFI",
        "username": "@Realfinance_REFI",
        "link": "https://t.me/Realfinance_REFI",
        "id": "@Realfinance_REFI"  # يمكن تحديثه بالـ chat_id لاحقاً
    },
    {
        "name": "Airdrop_MasterVIP",
        "username": "@Airdrop_MasterVIP", 
        "link": "https://t.me/Airdrop_MasterVIP",
        "id": "@Airdrop_MasterVIP"
    },
    {
        "name": "Daily_AirdropX",
        "username": "@Daily_AirdropX",
        "link": "https://t.me/Daily_AirdropX", 
        "id": "@Daily_AirdropX"
    }
]

# ==================== ثوابت المحادثة ====================
(
    WAITING_FOR_ADMIN_PASS,
    WAITING_WITHDRAW_AMOUNT,
    WAITING_WALLET_ADDRESS
) = range(3)

# ==================== تهيئة Firebase ====================
try:
    # محاولة الاتصال بقاعدة البيانات
    firebase_admin.get_app()
except ValueError:
    # إذا لم يكن متصلاً، نقوم بالاتصال
    try:
        # محاولة قراءة ملف الخدمة (للتطوير المحلي)
        cred = credentials.Certificate("serviceAccountKey.json")
        firebase_admin.initialize_app(cred, {
            'databaseURL': FIREBASE_CONFIG['databaseURL']
        })
        logger.info("✅ تم الاتصال بـ Firebase باستخدام ملف الخدمة")
    except Exception as e:
        logger.warning(f"لم يتم العثور على ملف الخدمة: {e}")
        # تهيئة بدون مصادقة (للاستخدام المحدود)
        firebase_admin.initialize_app(options={
            'databaseURL': FIREBASE_CONFIG['databaseURL']
        })
        logger.info("✅ تم الاتصال بـ Firebase بدون مصادقة")

# مرجع قاعدة البيانات
db_ref = db.reference('/')

# ==================== تخزين مؤقت للجلسات ====================
admin_sessions = {}  # للمشرفين: {user_id: expiry_timestamp}
user_states = {}  # لحالات المستخدمين: {chat_id: {'state': state, 'data': {}}}

# ==================== دوال مساعدة ====================

def format_number(num: int) -> str:
    """تنسيق الأرقام بفواصل"""
    return f"{num:,}"

def refi_to_usd(refi_amount: int) -> float:
    """تحويل REFi إلى دولار (1 مليون = $2)"""
    return (refi_amount / 1_000_000) * 2.00

def usd_to_refi(usd_amount: float) -> int:
    """تحويل دولار إلى REFi"""
    return int((usd_amount / 2.00) * 1_000_000)

def generate_referral_code(user_id: int) -> str:
    """توليد كود إحالة فريد من معرف المستخدم"""
    code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
    return code.upper()

def get_user_data(user_id: int) -> Dict:
    """جلب بيانات مستخدم من Firebase"""
    try:
        user_ref = db_ref.child(f'users/{user_id}')
        return user_ref.get() or {}
    except Exception as e:
        logger.error(f"خطأ في جلب بيانات المستخدم {user_id}: {e}")
        return {}

def save_user_data(user_id: int, data: Dict) -> bool:
    """حفظ بيانات مستخدم في Firebase"""
    try:
        db_ref.child(f'users/{user_id}').set(data)
        return True
    except Exception as e:
        logger.error(f"خطأ في حفظ بيانات المستخدم {user_id}: {e}")
        return False

def update_user_balance(user_id: int, amount: int, operation: str = 'add') -> Optional[int]:
    """تحديث رصيد المستخدم (إضافة أو خصم)"""
    user_data = get_user_data(user_id)
    current_balance = user_data.get('balance', 0)
    
    if operation == 'add':
        new_balance = current_balance + amount
    elif operation == 'subtract':
        if current_balance < amount:
            return None  # رصيد غير كاف
        new_balance = current_balance - amount
    else:
        return None
    
    user_data['balance'] = new_balance
    if save_user_data(user_id, user_data):
        return new_balance
    return None

def is_admin_user(user_id: int) -> bool:
    """التحقق من أن المستخدم مشرف"""
    return user_id in ADMIN_IDS

def has_admin_session(user_id: int) -> bool:
    """التحقق من وجود جلسة مشرف نشطة"""
    if user_id in admin_sessions:
        if admin_sessions[user_id] > time.time():
            return True
        else:
            del admin_sessions[user_id]
    return False

def create_admin_session(user_id: int, duration_hours: int = 1):
    """إنشاء جلسة مشرف جديدة"""
    admin_sessions[user_id] = time.time() + (duration_hours * 3600)

def end_admin_session(user_id: int):
    """إنهاء جلسة المشرف"""
    if user_id in admin_sessions:
        del admin_sessions[user_id]

# ==================== دوال التحقق من القنوات ====================

async def check_channel_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
    """التحقق من عضوية المستخدم في جميع القنوات المطلوبة"""
    not_joined = []
    
    for channel in REQUIRED_CHANNELS:
        try:
            # محاولة الحصول على معلومات العضوية
            chat_id = channel.get('id')
            if isinstance(chat_id, str) and chat_id.startswith('@'):
                chat_id = chat_id  # يترك كما هو للأسماء المستعارة
            
            member = await context.bot.get_chat_member(chat_id=chat_id, user_id=user_id)
            
            if member.status in ['left', 'kicked']:
                not_joined.append(channel['name'])
        except Exception as e:
            logger.error(f"خطأ في التحقق من القناة {channel['name']}: {e}")
            # في حالة الخطأ، نعتبر المستخدم غير عضو (للأمان)
            not_joined.append(channel['name'])
    
    return len(not_joined) == 0, not_joined

def get_channels_keyboard() -> InlineKeyboardMarkup:
    """إنشاء أزرار القنوات للانضمام"""
    keyboard = []
    for channel in REQUIRED_CHANNELS:
        keyboard.append([InlineKeyboardButton(
            text=f"📢 انضم إلى {channel['name']}",
            url=channel['link']
        )])
    keyboard.append([InlineKeyboardButton(
        text="✅ تحقق من الانضمام",
        callback_data="verify_membership"
    )])
    return InlineKeyboardMarkup(keyboard)

def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """إنشاء أزرار القائمة الرئيسية"""
    keyboard = [
        [
            InlineKeyboardButton("💰 الرصيد", callback_data="balance"),
            InlineKeyboardButton("🔗 الإحالة", callback_data="referral")
        ],
        [
            InlineKeyboardButton("💸 السحب", callback_data="withdraw"),
            InlineKeyboardButton("🔄 تحديث", callback_data="refresh")
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_withdraw_keyboard() -> InlineKeyboardMarkup:
    """إنشاء أزرار السحب"""
    keyboard = [
        [InlineKeyboardButton("🔙 العودة للقائمة", callback_data="main_menu")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_panel_keyboard() -> InlineKeyboardMarkup:
    """إنشاء أزرار لوحة المشرف"""
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 طلبات السحب", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="admin_search")],
        [InlineKeyboardButton("📢 رسالة للجميع", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔒 تسجيل الخروج", callback_data="admin_logout")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== Decorators للأمان ====================

def admin_required(func):
    """Decorator للتحقق من أن المستخدم مشرف ولديه جلسة نشطة"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        if not is_admin_user(user.id):
            await update.message.reply_text("⛔ هذا الأمر مخصص للمشرفين فقط.")
            return
        
        if not has_admin_session(user.id):
            await update.message.reply_text(
                "🔐 الرجاء تسجيل الدخول أولاً باستخدام /admin"
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

# ==================== معالجات الأوامر ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج أمر /start"""
    user = update.effective_user
    args = context.args
    
    # التحقق من وجود كود إحالة
    referral_code = args[0] if args else None
    
    # جلب بيانات المستخدم
    user_data = get_user_data(user.id)
    
    # إذا كان المستخدم جديد
    if not user_data:
        # إنشاء بيانات جديدة للمستخدم
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
            'referrals': {},
            'is_verified': False,
            'verified_at': None
        }
        
        # معالجة كود الإحالة إذا وجد
        if referral_code and referral_code != user_data['referral_code']:
            # البحث عن صاحب الكود
            users_ref = db_ref.child('users').order_by_child('referral_code').equal_to(referral_code).get()
            if users_ref:
                for referrer_id, referrer_data in users_ref.items():
                    # التأكد أن المحيل ليس المستخدم نفسه
                    if int(referrer_id) != user.id:
                        user_data['referred_by'] = int(referrer_id)
                        break
        
        save_user_data(user.id, user_data)
        
        # رسالة ترحيب مع أزرار القنوات
        channels_text = "\n".join([f"• {ch['name']}: {ch['link']}" for ch in REQUIRED_CHANNELS])
        
        await update.message.reply_text(
            f"🎉 *مرحباً بك في بوت {COIN_NAME}!*\n\n"
            f"💰 *مكافأة الترحيب:* {format_number(WELCOME_BONUS)} {COIN_NAME} (${refi_to_usd(WELCOME_BONUS):.2f})\n"
            f"👥 *مكافأة الإحالة:* {format_number(REFERRAL_BONUS)} {COIN_NAME} (${refi_to_usd(REFERRAL_BONUS):.2f}) لكل صديق\n\n"
            f"📢 *للبدء، يجب الاشتراك في هذه القنوات:*\n{channels_text}\n\n"
            f"👇 اضغط على 'تحقق' بعد الاشتراك",
            reply_markup=get_channels_keyboard(),
            parse_mode='Markdown'
        )
    else:
        # مستخدم قديم
        if user_data.get('is_verified', False):
            await show_main_menu(update, user.id)
        else:
            # لم يتحقق بعد
            channels_text = "\n".join([f"• {ch['name']}: {ch['link']}" for ch in REQUIRED_CHANNELS])
            await update.message.reply_text(
                f"🔔 *مرحباً من جديد!*\n\n"
                f"لم تقم بالتحقق من القنوات بعد:\n{channels_text}",
                reply_markup=get_channels_keyboard(),
                parse_mode='Markdown'
            )

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج أمر /admin (تسجيل دخول المشرف)"""
    user = update.effective_user
    
    if not is_admin_user(user.id):
        await update.message.reply_text("⛔ هذا الأمر مخصص للمشرفين فقط.")
        return ConversationHandler.END
    
    if has_admin_session(user.id):
        # إذا كانت لديه جلسة نشطة، نعرض لوحة التحكم مباشرة
        await show_admin_panel(update)
        return ConversationHandler.END
    
    await update.message.reply_text(
        "🔐 *تسجيل دخول المشرف*\n\n"
        "الرجاء إدخال كلمة السر:",
        parse_mode='Markdown'
    )
    return WAITING_FOR_ADMIN_PASS

async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """معالج إدخال كلمة سر المشرف"""
    user = update.effective_user
    entered_password = update.message.text
    
    if entered_password == ADMIN_PASSWORD:
        create_admin_session(user.id)
        await update.message.reply_text("✅ تم تسجيل الدخول بنجاح!")
        await show_admin_panel(update)
    else:
        await update.message.reply_text("❌ كلمة سر خاطئة!")
    
    return ConversationHandler.END

@admin_required
async def admin_logout_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """تسجيل خروج المشرف"""
    user = update.effective_user
    end_admin_session(user.id)
    await update.message.reply_text("🔒 تم تسجيل الخروج بنجاح.")

# ==================== معالجات الاستعلام (Callback) ====================

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الضغط على الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    data = query.data
    
    if data == "verify_membership":
        await verify_membership(update, context)
    
    elif data == "main_menu":
        await show_main_menu(update, user_id)
    
    elif data == "balance":
        await show_balance(update, user_id)
    
    elif data == "referral":
        await show_referral(update, user_id, context)
    
    elif data == "withdraw":
        await start_withdrawal(update, context, user_id)
    
    elif data == "refresh":
        await refresh_data(update, user_id)
    
    # أوامر المشرف
    elif data.startswith("admin_"):
        if not is_admin_user(user_id) or not has_admin_session(user_id):
            await query.edit_message_text("⛔ غير مصرح بهذا الإجراء.")
            return
        
        if data == "admin_stats":
            await show_admin_stats(update)
        elif data == "admin_withdrawals":
            await show_admin_withdrawals(update)
        elif data == "admin_search":
            await query.edit_message_text(
                "🔍 أرسل معرف المستخدم (User ID) للبحث:\n"
                "مثال: 123456789"
            )
            context.user_data['waiting_for_search'] = True
        elif data == "admin_broadcast":
            await query.edit_message_text(
                "📢 أرسل الرسالة التي تريد بثها لجميع المستخدمين:"
            )
            context.user_data['waiting_for_broadcast'] = True
        elif data == "admin_logout":
            end_admin_session(user_id)
            await query.edit_message_text("🔒 تم تسجيل الخروج بنجاح.")

async def verify_membership(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """التحقق من عضوية المستخدم في القنوات"""
    query = update.callback_query
    user_id = update.effective_user.id
    
    # التحقق من العضوية
    is_member, not_joined = await check_channel_membership(user_id, context)
    
    if is_member:
        # جلب بيانات المستخدم
        user_data = get_user_data(user_id)
        
        # إذا كان المستخدم لم يتحقق بعد
        if not user_data.get('is_verified', False):
            # إضافة مكافأة الترحيب
            new_balance = user_data.get('balance', 0) + WELCOME_BONUS
            user_data['balance'] = new_balance
            user_data['total_earned'] = user_data.get('total_earned', 0) + WELCOME_BONUS
            user_data['is_verified'] = True
            user_data['verified_at'] = time.time()
            
            save_user_data(user_id, user_data)
            
            # معالجة مكافأة الإحالة للمحيل
            referred_by = user_data.get('referred_by')
            if referred_by:
                referrer_data = get_user_data(referred_by)
                if referrer_data:
                    # إضافة مكافأة للمحيل
                    referrer_balance = referrer_data.get('balance', 0) + REFERRAL_BONUS
                    referrer_data['balance'] = referrer_balance
                    referrer_data['total_earned'] = referrer_data.get('total_earned', 0) + REFERRAL_BONUS
                    referrer_data['referrals_count'] = referrer_data.get('referrals_count', 0) + 1
                    
                    # تسجيل الإحالة
                    if 'referrals' not in referrer_data:
                        referrer_data['referrals'] = {}
                    referrer_data['referrals'][str(user_id)] = {
                        'joined_at': time.time(),
                        'bonus': REFERRAL_BONUS
                    }
                    
                    save_user_data(referred_by, referrer_data)
                    
                    # إشعار المحيل
                    try:
                        await context.bot.send_message(
                            chat_id=referred_by,
                            text=f"🎉 *مبروك!*\n\n"
                                 f"صديقك {user_data.get('first_name', '')} انضم عبر رابطك!\n"
                                 f"✨ تم إضافة {format_number(REFERRAL_BONUS)} {COIN_NAME} إلى رصيدك.",
                            parse_mode='Markdown'
                        )
                    except:
                        pass
            
            await query.edit_message_text(
                f"✅ *تم التحقق بنجاح!*\n\n"
                f"✨ تم إضافة {format_number(WELCOME_BONUS)} {COIN_NAME} إلى رصيدك.\n"
                f"💰 رصيدك الحالي: {format_number(new_balance)} {COIN_NAME}\n\n"
                f"👥 شارك رابطك مع أصدقائك واكسب {format_number(REFERRAL_BONUS)} {COIN_NAME} عن كل صديق.",
                reply_markup=get_main_menu_keyboard(),
                parse_mode='Markdown'
            )
        else:
            await show_main_menu(update, user_id)
    else:
        # عرض القنوات التي لم ينضم لها
        not_joined_text = "\n".join([f"• {ch}" for ch in not_joined])
        await query.edit_message_text(
            f"❌ *لم تنضم إلى القنوات التالية:*\n{not_joined_text}\n\n"
            f"الرجاء الانضمام ثم اضغط على 'تحقق' مرة أخرى.",
            reply_markup=get_channels_keyboard(),
            parse_mode='Markdown'
        )

async def show_main_menu(update: Update, user_id: int) -> None:
    """عرض القائمة الرئيسية"""
    query = update.callback_query
    
    user_data = get_user_data(user_id)
    balance = user_data.get('balance', 0)
    
    text = (
        f"🎯 *القائمة الرئيسية*\n\n"
        f"💰 رصيدك: {format_number(balance)} {COIN_NAME}\n"
        f"💵 القيمة: ${refi_to_usd(balance):.2f}\n"
        f"👥 إحالاتك: {user_data.get('referrals_count', 0)}\n\n"
        f"اختر من الأزرار أدناه:"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')
    else:
        await update.message.reply_text(text, reply_markup=get_main_menu_keyboard(), parse_mode='Markdown')

async def show_balance(update: Update, user_id: int) -> None:
    """عرض الرصيد والإحصائيات"""
    query = update.callback_query
    
    user_data = get_user_data(user_id)
    balance = user_data.get('balance', 0)
    total_earned = user_data.get('total_earned', 0)
    referrals_count = user_data.get('referrals_count', 0)
    
    text = (
        f"💰 *رصيدك*\n\n"
        f"• {COIN_NAME}: {format_number(balance)}\n"
        f"• الدولار: ${refi_to_usd(balance):.2f}\n\n"
        f"📊 *إحصائيات*\n"
        f"• عدد الإحالات: {referrals_count}\n"
        f"• إجمالي الأرباح: {format_number(total_earned)} {COIN_NAME}\n"
        f"• أرباح الإحالات: {format_number(total_earned - WELCOME_BONUS if total_earned > WELCOME_BONUS else 0)} {COIN_NAME}\n\n"
        f"🔹 *كل 1 مليون {COIN_NAME} = $2.00*"
    )
    
    keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def show_referral(update: Update, user_id: int, context: ContextTypes.DEFAULT_TYPE) -> None:
    """عرض رابط الإحالة"""
    query = update.callback_query
    
    user_data = get_user_data(user_id)
    referral_code = user_data.get('referral_code', generate_referral_code(user_id))
    
    # حفظ الكود إذا لم يكن موجوداً
    if 'referral_code' not in user_data:
        user_data['referral_code'] = referral_code
        save_user_data(user_id, user_data)
    
    bot_username = context.bot.username
    referral_link = f"https://t.me/{bot_username}?start={referral_code}"
    
    text = (
        f"🔗 *رابط الإحالة الخاص بك*\n\n"
        f"`{referral_link}`\n\n"
        f"🎁 *المكافآت:*\n"
        f"• أنت تكسب: {format_number(REFERRAL_BONUS)} {COIN_NAME} عن كل صديق\n"
        f"• صديقك يكسب: {format_number(WELCOME_BONUS)} {COIN_NAME} كمكافأة ترحيب\n\n"
        f"💰 *القيمة:* كل 1 مليون {COIN_NAME} = $2.00\n\n"
        f"انسخ الرابط وشاركه مع أصدقائك!"
    )
    
    keyboard = [
        [InlineKeyboardButton("🔙 العودة", callback_data="main_menu")],
        [InlineKeyboardButton("📋 نسخ الرابط", callback_data="copy_link")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')

async def start_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int) -> None:
    """بدء عملية السحب"""
    query = update.callback_query
    
    user_data = get_user_data(user_id)
    balance = user_data.get('balance', 0)
    
    if balance < MIN_WITHDRAW:
        remaining = MIN_WITHDRAW - balance
        text = (
            f"⚠️ *الحد الأدنى للسحب هو {format_number(MIN_WITHDRAW)} {COIN_NAME}*\n\n"
            f"💰 رصيدك الحالي: {format_number(balance)} {COIN_NAME}\n"
            f"💵 القيمة: ${refi_to_usd(balance):.2f}\n\n"
            f"⏳ متبقي لك: {format_number(remaining)} {COIN_NAME} (${refi_to_usd(remaining):.2f})\n\n"
            f"واصل دعوة أصدقائك للوصول للحد الأدنى!"
        )
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="main_menu")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
        return
    
    text = (
        f"💰 *رصيدك: {format_number(balance)} {COIN_NAME}*\n"
        f"💵 القيمة: ${refi_to_usd(balance):.2f}\n\n"
        f"📝 *الرجاء إدخال المبلغ الذي تريد سحبه:*\n"
        f"(الحد الأدنى: {format_number(MIN_WITHDRAW)} {COIN_NAME})"
    )
    
    await query.edit_message_text(text, parse_mode='Markdown')
    context.user_data['waiting_for_withdraw_amount'] = True
    context.user_data['withdraw_user_id'] = user_id

async def refresh_data(update: Update, user_id: int) -> None:
    """تحديث البيانات"""
    query = update.callback_query
    await show_main_menu(update, user_id)

@admin_required
async def show_admin_panel(update: Update) -> None:
    """عرض لوحة المشرف"""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "👨‍💼 *لوحة تحكم المشرف*\n\n"
            "اختر من الأزرار أدناه:",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode='Markdown'
        )
    else:
        await update.message.reply_text(
            "👨‍💼 *لوحة تحكم المشرف*\n\n"
            "اختر من الأزرار أدناه:",
            reply_markup=get_admin_panel_keyboard(),
            parse_mode='Markdown'
        )

@admin_required
async def show_admin_stats(update: Update) -> None:
    """عرض إحصائيات عامة"""
    query = update.callback_query
    
    try:
        # جلب الإحصائيات
        users_ref = db_ref.child('users').get()
        withdrawals_ref = db_ref.child('withdrawals').get()
        
        total_users = len(users_ref) if users_ref else 0
        verified_users = sum(1 for u in (users_ref or {}).values() if u.get('is_verified', False))
        
        total_balance = sum(u.get('balance', 0) for u in (users_ref or {}).values())
        total_withdrawn = 0
        
        pending_withdrawals = 0
        if withdrawals_ref:
            for w_id, w_data in withdrawals_ref.items():
                if w_data.get('status') == 'pending':
                    pending_withdrawals += 1
                if w_data.get('status') == 'approved':
                    total_withdrawn += w_data.get('amount', 0)
        
        text = (
            f"📊 *إحصائيات البوت*\n\n"
            f"👥 *المستخدمين*\n"
            f"• الإجمالي: {total_users}\n"
            f"• الموثقين: {verified_users}\n"
            f"• غير الموثقين: {total_users - verified_users}\n\n"
            f"💰 *الأرصدة*\n"
            f"• إجمالي الأرصدة: {format_number(total_balance)} {COIN_NAME}\n"
            f"• القيمة: ${refi_to_usd(total_balance):.2f}\n\n"
            f"💸 *السحوبات*\n"
            f"• طلبات معلقة: {pending_withdrawals}\n"
            f"• إجمالي المسحوبات: {format_number(total_withdrawn)} {COIN_NAME}\n"
            f"• القيمة: ${refi_to_usd(total_withdrawn):.2f}"
        )
        
        keyboard = [[InlineKeyboardButton("🔙 العودة", callback_data="admin_back")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"خطأ في عرض الإحصائيات: {e}")
        await query.edit_message_text("❌ حدث خطأ في جلب الإحصائيات.")

@admin_required
async def show_admin_withdrawals(update: Update) -> None:
    """عرض طلبات السحب المعلقة"""
    query = update.callback_query
    
    try:
        withdrawals_ref = db_ref.child('withdrawals').order_by_child('status').equal_to('pending').get()
        
        if not withdrawals_ref:
            await query.edit_message_text(
                "✅ لا توجد طلبات سحب معلقة.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 العودة", callback_data="admin_back")]]),
                parse_mode='Markdown'
            )
            return
        
        text = "💰 *طلبات السحب المعلقة*\n\n"
        keyboard = []
        
        for w_id, w_data in withdrawals_ref.items():
            user_id = w_data.get('user_id')
            amount = w_data.get('amount', 0)
            wallet = w_data.get('wallet', '')
            date = datetime.fromtimestamp(w_data.get('created_at', 0)).strftime('%Y-%m-%d %H:%M')
            
            short_wallet = wallet[:10] + '...' + wallet[-6:] if len(wallet) > 20 else wallet
            
            text += f"🆔 *{w_id}*\n"
            text += f"👤 المستخدم: `{user_id}`\n"
            text += f"💰 المبلغ: {format_number(amount)} {COIN_NAME} (${refi_to_usd(amount):.2f})\n"
            text += f"📮 المحفظة: `{short_wallet}`\n"
            text += f"📅 التاريخ: {date}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✅ قبول {w_id[:6]}", callback_data=f"approve_{w_id}"),
                InlineKeyboardButton(f"❌ رفض {w_id[:6]}", callback_data=f"reject_{w_id}")
            ])
        
        keyboard.append([InlineKeyboardButton("🔙 العودة", callback_data="admin_back")])
        
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    except Exception as e:
        logger.error(f"خطأ في عرض طلبات السحب: {e}")
        await query.edit_message_text("❌ حدث خطأ في جلب طلبات السحب.")

# ==================== معالجات الرسائل النصية ====================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """معالج الرسائل النصية"""
    user_id = update.effective_user.id
    text = update.message.text
    
    # البحث عن مستخدم
    if context.user_data.get('waiting_for_search'):
        try:
            search_user_id = int(text.strip())
            user_data = get_user_data(search_user_id)
            
            if user_data:
                balance = user_data.get('balance', 0)
                referrals = user_data.get('referrals_count', 0)
                joined = datetime.fromtimestamp(user_data.get('joined_at', 0)).strftime('%Y-%m-%d')
                verified = user_data.get('is_verified', False)
                
                msg = (
                    f"🔍 *نتيجة البحث*\n\n"
                    f"🆔 المعرف: `{search_user_id}`\n"
                    f"👤 الاسم: {user_data.get('first_name', '')}\n"
                    f"📱 اليوزر: @{user_data.get('username', '')}\n"
                    f"💰 الرصيد: {format_number(balance)} {COIN_NAME}\n"
                    f"💵 القيمة: ${refi_to_usd(balance):.2f}\n"
                    f"👥 الإحالات: {referrals}\n"
                    f"✅ موثق: {'نعم' if verified else 'لا'}\n"
                    f"📅 تاريخ الانضمام: {joined}"
                )
            else:
                msg = f"❌ لا يوجد مستخدم بالمعرف `{search_user_id}`"
            
            await update.message.reply_text(msg, parse_mode='Markdown')
        except ValueError:
            await update.message.reply_text("❌ المعرف يجب أن يكون رقماً!")
        
        context.user_data['waiting_for_search'] = False
        return
    
    # البث للمستخدمين
    if context.user_data.get('waiting_for_broadcast'):
        if not is_admin_user(user_id) or not has_admin_session(user_id):
            await update.message.reply_text("⛔ غير مصرح")
            context.user_data['waiting_for_broadcast'] = False
            return
        
        await update.message.reply_text("📢 جاري إرسال الرسالة إلى جميع المستخدمين...")
        
        # جلب جميع المستخدمين
        users_ref = db_ref.child('users').get()
        if users_ref:
            sent = 0
            failed = 0
            for uid in users_ref.keys():
                try:
                    await context.bot.send_message(chat_id=int(uid), text=text, parse_mode='Markdown')
                    sent += 1
                except Exception as e:
                    failed += 1
                    logger.error(f"فشل إرسال رسالة إلى {uid}: {e}")
            
            await update.message.reply_text(
                f"✅ *تم البث*\n\n"
                f"• تم الإرسال: {sent}\n"
                f"• فشل: {failed}",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text("❌ لا يوجد مستخدمين.")
        
        context.user_data['waiting_for_broadcast'] = False
        return
    
    # معالجة السحب
    if context.user_data.get('waiting_for_withdraw_amount'):
        try:
            amount = int(text.strip().replace(',', ''))
            
            user_data = get_user_data(user_id)
            balance = user_data.get('balance', 0)
            
            if amount < MIN_WITHDRAW:
                await update.message.reply_text(
                    f"❌ المبلغ أقل من الحد الأدنى ({format_number(MIN_WITHDRAW)} {COIN_NAME}).\n"
                    f"الرجاء إدخال مبلغ أكبر."
                )
                return
            
            if amount > balance:
                await update.message.reply_text(
                    f"❌ المبلغ يتجاوز رصيدك ({format_number(balance)} {COIN_NAME}).\n"
                    f"الرجاء إدخال مبلغ أقل."
                )
                return
            
            # حفظ المبلغ وطلب عنوان المحفظة
            context.user_data['withdraw_amount'] = amount
            context.user_data['waiting_for_withdraw_amount'] = False
            context.user_data['waiting_for_wallet_address'] = True
            
            await update.message.reply_text(
                f"💰 مبلغ السحب: {format_number(amount)} {COIN_NAME} (${refi_to_usd(amount):.2f})\n\n"
                f"📮 *الرجاء إدخال عنوان محفظتك (يبدأ بـ 0x):*",
                parse_mode='Markdown'
            )
        except ValueError:
            await update.message.reply_text("❌ الرجاء إدخال رقم صحيح.")
        return
    
    if context.user_data.get('waiting_for_wallet_address'):
        wallet = text.strip()
        
        if not wallet.startswith('0x') or len(wallet) < 30:
            await update.message.reply_text(
                "❌ عنوان المحفظة غير صالح!\n"
                "الرجاء إدخال عنوان صحيح يبدأ بـ 0x"
            )
            return
        
        # معالجة طلب السحب
        amount = context.user_data.get('withdraw_amount')
        if not amount:
            await update.message.reply_text("❌ حدث خطأ. الرجاء البدء من جديد.")
            context.user_data.clear()
            return
        
        # خصم الرصيد
        new_balance = update_user_balance(user_id, amount, 'subtract')
        if new_balance is None:
            await update.message.reply_text("❌ رصيد غير كاف.")
            context.user_data.clear()
            return
        
        # إنشاء طلب سحب
        withdrawal_id = f"W{int(time.time())}_{user_id}"
        withdrawal_data = {
            'id': withdrawal_id,
            'user_id': user_id,
            'username': update.effective_user.username,
            'amount': amount,
            'wallet': wallet,
            'created_at': time.time(),
            'status': 'pending',
            'processed_at': None
        }
        
        db_ref.child(f'withdrawals/{withdrawal_id}').set(withdrawal_data)
        
        await update.message.reply_text(
            f"✅ *تم تقديم طلب السحب بنجاح!*\n\n"
            f"🆔 رقم الطلب: `{withdrawal_id}`\n"
            f"💰 المبلغ: {format_number(amount)} {COIN_NAME}\n"
            f"💵 القيمة: ${refi_to_usd(amount):.2f}\n"
            f"📮 المحفظة: `{wallet[:10]}...{wallet[-6:]}`\n\n"
            f"⏳ حالة الطلب: قيد المراجعة\n\n"
            f"سيتم إشعارك عند معالجة الطلب.",
            parse_mode='Markdown'
        )
        
        # إشعار المشرف
        for admin_id in ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=f"💰 *طلب سحب جديد*\n\n"
                         f"🆔 المستخدم: `{user_id}`\n"
                         f"👤 @{update.effective_user.username}\n"
                         f"💰 المبلغ: {format_number(amount)} {COIN_NAME}\n"
                         f"💵 القيمة: ${refi_to_usd(amount):.2f}\n"
                         f"📮 المحفظة: `{wallet[:15]}...`\n\n"
                         f"استخدم /admin للموافقة أو الرفض",
                    parse_mode='Markdown'
                )
            except:
                pass
        
        context.user_data.clear()

# ==================== معالجات الموافقة على السحوبات ====================

@admin_required
async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, withdrawal_id: str) -> None:
    """الموافقة على طلب سحب"""
    query = update.callback_query
    
    try:
        withdrawal_ref = db_ref.child(f'withdrawals/{withdrawal_id}')
        withdrawal_data = withdrawal_ref.get()
        
        if not withdrawal_data:
            await query.edit_message_text("❌ طلب السحب غير موجود.")
            return
        
        if withdrawal_data.get('status') != 'pending':
            await query.edit_message_text(f"❌ الطلب تم معالجته بالفعل (الحالة: {withdrawal_data.get('status')})")
            return
        
        # تحديث حالة الطلب
        withdrawal_data['status'] = 'approved'
        withdrawal_data['processed_at'] = time.time()
        withdrawal_data['processed_by'] = update.effective_user.id
        withdrawal_ref.set(withdrawal_data)
        
        # إشعار المستخدم
        user_id = withdrawal_data.get('user_id')
        amount = withdrawal_data.get('amount')
        wallet = withdrawal_data.get('wallet')
        
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"✅ *تمت الموافقة على طلب السحب!*\n\n"
                     f"💰 المبلغ: {format_number(amount)} {COIN_NAME}\n"
                     f"💵 القيمة: ${refi_to_usd(amount):.2f}\n"
                     f"📮 المحفظة: `{wallet}`\n\n"
                     f"سيتم إرسال المبلغ قريباً.",
                parse_mode='Markdown'
            )
        except:
            pass
        
        await query.edit_message_text(f"✅ تمت الموافقة على الطلب {withdrawal_id}")
    except Exception as e:
        logger.error(f"خطأ في الموافقة على الطلب: {e}")
        await query.edit_message_text("❌ حدث خطأ.")

@admin_required
async def reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE, withdrawal_id: str) -> None:
    """رفض طلب سحب"""
    query = update.callback_query
    
    try:
        withdrawal_ref = db_ref.child(f'withdrawals/{withdrawal_id}')
        withdrawal_data = withdrawal_ref.get()
        
        if not withdrawal_data:
            await query.edit_message_text("❌ طلب السحب غير موجود.")
            return
        
        if withdrawal_data.get('status') != 'pending':
            await query.edit_message_text(f"❌ الطلب تم معالجته بالفعل (الحالة: {withdrawal_data.get('status')})")
            return
        
        user_id = withdrawal_data.get('user_id')
        amount = withdrawal_data.get('amount')
        
        # إعادة الرصيد للمستخدم
        update_user_balance(user_id, amount, 'add')
        
        # تحديث حالة الطلب
        withdrawal_data['status'] = 'rejected'
        withdrawal_data['processed_at'] = time.time()
        withdrawal_data['processed_by'] = update.effective_user.id
        withdrawal_ref.set(withdrawal_data)
        
        # إشعار المستخدم
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"❌ *تم رفض طلب السحب*\n\n"
                     f"💰 المبلغ: {format_number(amount)} {COIN_NAME}\n"
                     f"💵 القيمة: ${refi_to_usd(amount):.2f}\n\n"
                     f"تم إعادة المبلغ إلى رصيدك.\n"
                     f"يرجى التواصل مع الدعم للمزيد من المعلومات.",
                parse_mode='Markdown'
            )
        except:
            pass
        
        await query.edit_message_text(f"✅ تم رفض الطلب {withdrawal_id} وإعادة الرصيد.")
    except Exception as e:
        logger.error(f"خطأ في رفض الطلب: {e}")
        await query.edit_message_text("❌ حدث خطأ.")

# ==================== الإعداد والتشغيل ====================

def main() -> None:
    """الدالة الرئيسية لتشغيل البوت"""
    
    # إنشاء التطبيق
    application = Application.builder().token(BOT_TOKEN).build()
    
    # محادثة دخول المشرف
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_command)],
        states={
            WAITING_FOR_ADMIN_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_password)]
        },
        fallbacks=[]
    )
    
    # إضافة المعالجات
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("admin", admin_command))
    application.add_handler(CommandHandler("logout", admin_logout_command))
    application.add_handler(admin_conv)
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # معالجات خاصة بالسحوبات (للاستعلامات)
    # سيتم معالجتها في button_callback
    
    # بدء البوت
    print("🤖 بوت REFi جاهز للعمل!")
    print(f"👤 المشرفون: {ADMIN_IDS}")
    print(f"💰 مكافأة الترحيب: {format_number(WELCOME_BONUS)} {COIN_NAME}")
    print(f"👥 مكافأة الإحالة: {format_number(REFERRAL_BONUS)} {COIN_NAME}")
    print(f"💸 الحد الأدنى للسحب: {format_number(MIN_WITHDRAW)} {COIN_NAME}")
    
    application.run_polling()

if __name__ == '__main__':
    main()

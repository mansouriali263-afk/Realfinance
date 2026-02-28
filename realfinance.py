#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi BOT - FINAL FIXED VERSION
"""

import logging
import time
import random
import string
from datetime import datetime

# ==================== FIX THE ISSUE ====================
# Apply monkey patch before importing telegram
import types
import telegram.ext._updater

# Fix the missing __dict__ issue
if not hasattr(telegram.ext._updater.Updater, '__dict__'):
    telegram.ext._updater.Updater.__dict__ = {}

# Now import telegram safely
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, filters, ContextTypes, ConversationHandler
)
from telegram.constants import ParseMode

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
users = {}
withdrawals = {}
admin_sessions = {}

def save_data():
    """Save data to file (optional)"""
    try:
        data = {
            'users': users,
            'withdrawals': withdrawals,
            'timestamp': time.time()
        }
        with open('bot_data.json', 'w') as f:
            import json
            json.dump(data, f)
    except:
        pass

# ==================== UTILS ====================
def format_number(num):
    return f"{num:,}"

def refi_to_usd(refi):
    return (refi / 1_000_000) * 2.0

def is_valid_wallet(wallet):
    if not wallet or not wallet.startswith('0x'):
        return False
    if len(wallet) != 42:
        return False
    try:
        int(wallet[2:], 16)
        return True
    except:
        return False

def generate_code(user_id):
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

def generate_request_id(user_id):
    return f"W{int(time.time())}{user_id}"

# ==================== KEYBOARDS ====================
def channels_keyboard():
    keyboard = []
    for ch in REQUIRED_CHANNELS:
        keyboard.append([InlineKeyboardButton(f"📢 Join {ch['name']}", url=ch['link'])])
    keyboard.append([InlineKeyboardButton("✅ Verify", callback_data="verify")])
    return InlineKeyboardMarkup(keyboard)

def main_keyboard(is_admin=False):
    keyboard = [
        [InlineKeyboardButton("💰 Balance", callback_data="balance"),
         InlineKeyboardButton("🔗 Referral", callback_data="referral")],
        [InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
         InlineKeyboardButton("📊 Stats", callback_data="stats")]
    ]
    if is_admin:
        keyboard.append([InlineKeyboardButton("👑 Admin", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def back_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Back", callback_data="main_menu")]])

# ==================== HANDLERS ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = str(user.id)
    
    logger.info(f"Start from {user_id}")
    
    # Create user if not exists
    if user_id not in users:
        users[user_id] = {
            'id': user_id,
            'username': user.username or '',
            'name': user.first_name or '',
            'joined': time.time(),
            'balance': 0,
            'total_earned': 0,
            'referred_by': None,
            'referrals': 0,
            'code': generate_code(user.id),
            'verified': False,
            'wallet': None
        }
        save_data()
    
    await update.message.reply_text(
        f"🎉 *Welcome to REFi Bot!*\n\n"
        f"Your ID: `{user_id}`\n\n"
        f"This is the final fixed version.",
        reply_markup=main_keyboard(user.id in [str(a) for a in ADMIN_IDS]),
        parse_mode=ParseMode.MARKDOWN
    )

async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user = users.get(user_id, {})
    bal = user.get('balance', 0)
    
    await query.edit_message_text(
        f"💰 *Your Balance*\n\n"
        f"{format_number(bal)} REFi\n"
        f"${refi_to_usd(bal):.2f} USD",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    user = users.get(user_id, {})
    code = user.get('code', '')
    link = f"https://t.me/{context.bot.username}?start={code}"
    
    await query.edit_message_text(
        f"🔗 *Your Link*\n\n"
        f"`{link}`\n\n"
        f"Share this with friends!",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    await query.edit_message_text(
        "🎯 *Main Menu*",
        reply_markup=main_keyboard(user_id in [str(a) for a in ADMIN_IDS]),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return ConversationHandler.END
    
    await update.message.reply_text("🔐 Enter password:")
    return 1

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text
    
    if password == ADMIN_PASSWORD:
        admin_sessions[user.id] = time.time() + 3600
        await update.message.reply_text("✅ Login successful!")
        await update.message.reply_text(
            "👑 *Admin Panel*\n\n"
            f"Users: {len(users)}",
            parse_mode=ParseMode.MARKDOWN
        )
    else:
        await update.message.reply_text("❌ Wrong password")
    
    return ConversationHandler.END

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Use /start")

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    print("\n" + "="*50)
    print("🤖 REFi BOT - FINAL FIX")
    print("="*50)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"🐍 Python: 3.11 (from runtime.txt)")
    print(f"👤 Users: {len(users)}")
    print("="*50 + "\n")
    
    # Create application
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Admin conversation
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_login)],
        states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_password)]},
        fallbacks=[]
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(admin_conv)
    app.add_handler(MessageHandler(filters.COMMAND, unknown))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(referral, pattern="^referral$"))
    
    # Error handler
    app.add_error_handler(error)
    
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*50 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Fatal")

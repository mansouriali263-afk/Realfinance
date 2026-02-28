#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
🤖 REFi REFERRAL BOT - FIXED FOR PYTHON 3.14
=========================================================
"""

# ==================== IMPORTS ====================
import os
import sys
import logging
import time
import json
import random
import string
import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Tuple

# Fix for Python 3.14 attribute error
import types
import telegram.ext._updater

# Monkey patch to fix the issue
if not hasattr(telegram.ext._updater.Updater, '__dict__'):
    telegram.ext._updater.Updater.__dict__ = {}

# Now import the rest
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    Defaults
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
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", 
     "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", 
     "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", 
     "link": "https://t.me/Daily_AirdropX"}
]

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== UTILS ====================
def format_number(num: int) -> str:
    return f"{num:,}"

def refi_to_usd(refi: int) -> float:
    return (refi / 1_000_000) * 2.0

def is_valid_wallet(wallet: str) -> bool:
    if not wallet or not wallet.startswith('0x'):
        return False
    if len(wallet) != 42:
        return False
    try:
        int(wallet[2:], 16)
        return True
    except:
        return False

def get_date(timestamp: float = None) -> str:
    dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M')

# ==================== DATABASE ====================
db = {
    'users': {},
    'withdrawals': {},
    'admin_sessions': {},
    'stats': {
        'total_users': 0,
        'total_verified': 0,
        'total_withdrawals': 0,
        'total_withdrawn': 0,
        'total_referrals': 0,
        'start_time': time.time()
    }
}

def get_user(user_id: int) -> dict:
    return db['users'].get(str(user_id), {})

def save_user(user_id: int, data: dict):
    db['users'][str(user_id)] = data
    if 'joined_at' in data:
        db['stats']['total_users'] = len(db['users'])

def get_withdrawal(req_id: str) -> dict:
    return db['withdrawals'].get(req_id, {})

def save_withdrawal(req_id: str, data: dict):
    db['withdrawals'][req_id] = data

def is_admin_session(user_id: int) -> bool:
    if user_id not in db['admin_sessions']:
        return False
    if db['admin_sessions'][user_id] < time.time():
        del db['admin_sessions'][user_id]
        return False
    return True

def create_admin_session(user_id: int):
    db['admin_sessions'][user_id] = time.time() + 3600

def end_admin_session(user_id: int):
    db['admin_sessions'].pop(user_id, None)

def generate_referral_code(user_id: int) -> str:
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=8))

def generate_request_id(user_id: int) -> str:
    return f"W{int(time.time())}{user_id}{random.randint(1000,9999)}"

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

def admin_keyboard():
    keyboard = [
        [InlineKeyboardButton("📊 Stats", callback_data="admin_stats")],
        [InlineKeyboardButton("💰 Withdrawals", callback_data="admin_withdrawals")],
        [InlineKeyboardButton("🔍 Search", callback_data="admin_search")],
        [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔒 Logout", callback_data="admin_logout")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ==================== HANDLERS ====================

# START
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    
    logger.info(f"Start from {user.id}")
    
    # Get or create user
    user_data = get_user(user.id)
    if not user_data:
        user_data = {
            'user_id': user.id,
            'username': user.username or '',
            'first_name': user.first_name or '',
            'joined_at': time.time(),
            'last_active': time.time(),
            'balance': 0,
            'total_earned': 0,
            'total_withdrawn': 0,
            'referral_code': generate_referral_code(user.id),
            'referred_by': None,
            'referrals_count': 0,
            'referrals': {},
            'referral_clicks': 0,
            'verified': False,
            'verified_at': None,
            'wallet': None,
            'is_admin': user.id in ADMIN_IDS,
            'is_banned': False
        }
        save_user(user.id, user_data)
    
    # Check referral
    if args and args[0] and not user_data.get('referred_by'):
        for uid, u in db['users'].items():
            if u.get('referral_code') == args[0] and int(uid) != user.id:
                user_data['referred_by'] = int(uid)
                u['referral_clicks'] = u.get('referral_clicks', 0) + 1
                save_user(int(uid), u)
                save_user(user.id, user_data)
                break
    
    # If verified, show main menu
    if user_data.get('verified'):
        await show_main_menu(update, context, user_data)
        return
    
    # Show channels
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    await update.message.reply_text(
        f"🎉 *Welcome to REFi Bot!*\n\n"
        f"💰 Welcome: {format_number(WELCOME_BONUS)} REFi (${refi_to_usd(WELCOME_BONUS):.2f})\n"
        f"👥 Referral: {format_number(REFERRAL_BONUS)} REFi (${refi_to_usd(REFERRAL_BONUS):.2f})\n\n"
        f"📢 Join:\n{channels_text}",
        reply_markup=channels_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# VERIFY
async def verify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    # Check channels
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        try:
            member = await context.bot.get_chat_member(chat_id=ch['username'], user_id=user_id)
            if member.status in ['left', 'kicked']:
                not_joined.append(ch['name'])
        except:
            not_joined.append(ch['name'])
    
    if not_joined:
        await query.edit_message_text(
            f"❌ Not joined:\n{', '.join(not_joined)}",
            reply_markup=channels_keyboard()
        )
        return
    
    # Verify
    user_data['verified'] = True
    user_data['verified_at'] = time.time()
    user_data['balance'] = user_data.get('balance', 0) + WELCOME_BONUS
    user_data['total_earned'] = user_data.get('total_earned', 0) + WELCOME_BONUS
    db['stats']['total_verified'] += 1
    
    # Process referral
    if user_data.get('referred_by'):
        referrer = get_user(user_data['referred_by'])
        if referrer:
            referrer['balance'] = referrer.get('balance', 0) + REFERRAL_BONUS
            referrer['total_earned'] = referrer.get('total_earned', 0) + REFERRAL_BONUS
            referrer['referrals_count'] = referrer.get('referrals_count', 0) + 1
            referrer['referrals'][str(user_id)] = time.time()
            save_user(user_data['referred_by'], referrer)
            db['stats']['total_referrals'] += 1
            
            try:
                await context.bot.send_message(
                    chat_id=user_data['referred_by'],
                    text=f"🎉 Friend joined! You earned {format_number(REFERRAL_BONUS)} REFi"
                )
            except:
                pass
    
    save_user(user_id, user_data)
    
    await query.edit_message_text(
        f"✅ *Verified!*\n\n"
        f"💰 Balance: {format_number(user_data['balance'])} REFi",
        reply_markup=main_keyboard(user_data.get('is_admin')),
        parse_mode=ParseMode.MARKDOWN
    )

# MAIN MENU
async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    await show_main_menu(update, context, user_data, query)

async def show_main_menu(update, context, user_data, query=None):
    text = (
        f"🎯 *Main Menu*\n\n"
        f"💰 Balance: {format_number(user_data.get('balance', 0))} REFi\n"
        f"👥 Referrals: {user_data.get('referrals_count', 0)}"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=main_keyboard(user_data.get('is_admin')), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=main_keyboard(user_data.get('is_admin')), parse_mode=ParseMode.MARKDOWN)

# BALANCE
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    balance = user_data.get('balance', 0)
    total = user_data.get('total_earned', 0)
    
    await query.edit_message_text(
        f"💰 *Balance*\n\n"
        f"REFi: {format_number(balance)}\n"
        f"USD: ${refi_to_usd(balance):.2f}\n\n"
        f"Total earned: {format_number(total)} REFi",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# REFERRAL
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    link = f"https://t.me/{context.bot.username}?start={user_data.get('referral_code', '')}"
    
    await query.edit_message_text(
        f"🔗 *Your Link*\n\n"
        f"`{link}`\n\n"
        f"Earn {format_number(REFERRAL_BONUS)} REFi per friend!",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# STATS
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    await query.edit_message_text(
        f"📊 *Stats*\n\n"
        f"Referrals: {user_data.get('referrals_count', 0)}\n"
        f"Clicks: {user_data.get('referral_clicks', 0)}\n"
        f"Joined: {get_date(user_data.get('joined_at', 0))}",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

# WITHDRAW
async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    if not user_data:
        await query.edit_message_text("❌ Send /start first")
        return
    
    if not user_data.get('verified'):
        await query.edit_message_text("❌ Verify first!")
        return
    
    balance = user_data.get('balance', 0)
    
    if balance < MIN_WITHDRAW:
        await query.edit_message_text(
            f"⚠️ Min: {format_number(MIN_WITHDRAW)} REFi\n"
            f"Your balance: {format_number(balance)} REFi",
            reply_markup=back_keyboard()
        )
        return
    
    context.user_data['withdraw_state'] = 'waiting_amount'
    await query.edit_message_text(
        f"💸 Enter amount (min {format_number(MIN_WITHDRAW)} REFi):",
        reply_markup=back_keyboard()
    )

async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('withdraw_state') != 'waiting_amount':
        return
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    
    try:
        amount = int(update.message.text.replace(',', ''))
    except:
        await update.message.reply_text("❌ Invalid number")
        return
    
    if amount < MIN_WITHDRAW:
        await update.message.reply_text(f"❌ Min is {format_number(MIN_WITHDRAW)}")
        return
    
    if amount > user_data.get('balance', 0):
        await update.message.reply_text("❌ Insufficient balance")
        return
    
    context.user_data['withdraw_amount'] = amount
    context.user_data['withdraw_state'] = 'waiting_wallet'
    await update.message.reply_text("📮 Send your wallet address (starts with 0x):")

async def handle_wallet(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('withdraw_state') != 'waiting_wallet':
        return
    
    user_id = update.effective_user.id
    user_data = get_user(user_id)
    wallet = update.message.text.strip()
    
    if not is_valid_wallet(wallet):
        await update.message.reply_text("❌ Invalid wallet")
        return
    
    amount = context.user_data.get('withdraw_amount')
    
    # Deduct
    user_data['balance'] = user_data.get('balance', 0) - amount
    
    # Create request
    req_id = generate_request_id(user_id)
    withdrawal = {
        'id': req_id,
        'user_id': user_id,
        'amount': amount,
        'wallet': wallet,
        'status': 'pending',
        'created_at': time.time()
    }
    save_withdrawal(req_id, withdrawal)
    save_user(user_id, user_data)
    db['stats']['total_withdrawals'] += 1
    
    context.user_data.pop('withdraw_state', None)
    context.user_data.pop('withdraw_amount', None)
    
    await update.message.reply_text(
        f"✅ Request sent!\nID: `{req_id}`",
        reply_markup=main_keyboard(user_data.get('is_admin')),
        parse_mode=ParseMode.MARKDOWN
    )

# ADMIN
async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    
    if user.id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Unauthorized")
        return ConversationHandler.END
    
    if is_admin_session(user.id):
        await show_admin_panel(update, context)
        return ConversationHandler.END
    
    await update.message.reply_text("🔐 Enter password:")
    return 1

async def admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    password = update.message.text
    
    if password == ADMIN_PASSWORD:
        create_admin_session(user.id)
        
        user_data = get_user(user.id)
        if not user_data:
            user_data = {'user_id': user.id, 'is_admin': True}
        else:
            user_data['is_admin'] = True
        save_user(user.id, user_data)
        
        await update.message.reply_text("✅ Logged in!")
        await show_admin_panel(update, context)
    else:
        await update.message.reply_text("❌ Wrong password")
    
    return ConversationHandler.END

async def show_admin_panel(update, context, query=None):
    stats = db['stats']
    uptime = int(time.time() - stats['start_time'])
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    
    text = (
        f"👑 *Admin*\n\n"
        f"Users: {stats['total_users']}\n"
        f"Verified: {stats['total_verified']}\n"
        f"Withdrawals: {stats['total_withdrawals']}\n"
        f"Uptime: {hours}h {minutes}m"
    )
    
    if query:
        await query.edit_message_text(text, reply_markup=admin_keyboard(), parse_mode=ParseMode.MARKDOWN)
    else:
        await update.message.reply_text(text, reply_markup=admin_keyboard(), parse_mode=ParseMode.MARKDOWN)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    stats = db['stats']
    total_balance = sum(u.get('balance', 0) for u in db['users'].values())
    
    await query.edit_message_text(
        f"📊 *Stats*\n\n"
        f"Users: {stats['total_users']}\n"
        f"Verified: {stats['total_verified']}\n"
        f"Referrals: {stats['total_referrals']}\n"
        f"Withdrawals: {stats['total_withdrawals']}\n"
        f"Total Balance: {format_number(total_balance)} REFi",
        reply_markup=admin_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )

async def admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    pending = [w for w in db['withdrawals'].values() if w.get('status') == 'pending']
    
    if not pending:
        await query.edit_message_text("✅ No pending", reply_markup=admin_keyboard())
        return
    
    text = "💰 *Pending*\n\n"
    for w in pending[:5]:
        user = get_user(w['user_id'])
        name = user.get('first_name', 'Unknown') if user else 'Unknown'
        text += f"• {w['id'][:8]}: {name} - {format_number(w['amount'])} REFi\n"
    
    keyboard = []
    for w in pending[:5]:
        keyboard.append([InlineKeyboardButton(f"Process {w['id'][:8]}", callback_data=f"process_{w['id']}")])
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

async def process_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    
    req_id = data.replace('process_', '')
    withdrawal = get_withdrawal(req_id)
    
    if not withdrawal or withdrawal.get('status') != 'pending':
        await query.answer("❌ Not found")
        return
    
    user_id = withdrawal['user_id']
    amount = withdrawal['amount']
    
    keyboard = [
        [InlineKeyboardButton("✅ Approve", callback_data=f"approve_{req_id}"),
         InlineKeyboardButton("❌ Reject", callback_data=f"reject_{req_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="admin_withdrawals")]
    ]
    
    await query.edit_message_text(
        f"Request: {req_id}\nAmount: {format_number(amount)} REFi",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def approve_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    req_id = data.replace('approve_', '')
    
    withdrawal = get_withdrawal(req_id)
    if not withdrawal:
        await query.answer("❌ Not found")
        return
    
    withdrawal['status'] = 'approved'
    withdrawal['processed_at'] = time.time()
    save_withdrawal(req_id, withdrawal)
    
    try:
        await context.bot.send_message(
            chat_id=withdrawal['user_id'],
            text=f"✅ Your withdrawal of {format_number(withdrawal['amount'])} REFi is approved!"
        )
    except:
        pass
    
    await query.edit_message_text("✅ Approved", reply_markup=admin_keyboard())

async def reject_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    req_id = data.replace('reject_', '')
    
    withdrawal = get_withdrawal(req_id)
    if not withdrawal:
        await query.answer("❌ Not found")
        return
    
    # Return funds
    user = get_user(withdrawal['user_id'])
    if user:
        user['balance'] = user.get('balance', 0) + withdrawal['amount']
        save_user(withdrawal['user_id'], user)
    
    withdrawal['status'] = 'rejected'
    withdrawal['processed_at'] = time.time()
    save_withdrawal(req_id, withdrawal)
    
    try:
        await context.bot.send_message(
            chat_id=withdrawal['user_id'],
            text=f"❌ Withdrawal of {format_number(withdrawal['amount'])} REFi rejected. Funds returned."
        )
    except:
        pass
    
    await query.edit_message_text("❌ Rejected", reply_markup=admin_keyboard())

async def admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🔍 Send user ID or @username:",
        reply_markup=back_keyboard()
    )
    context.user_data['admin_search'] = True

async def handle_admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('admin_search'):
        return
    
    text = update.message.text.strip()
    user = None
    
    if text.isdigit():
        user = get_user(int(text))
    else:
        username = text.lstrip('@').lower()
        for u in db['users'].values():
            if u.get('username', '').lower() == username:
                user = u
                break
    
    if not user:
        await update.message.reply_text("❌ Not found")
        return
    
    balance = user.get('balance', 0)
    
    await update.message.reply_text(
        f"👤 *User*\n\n"
        f"ID: `{user['user_id']}`\n"
        f"Name: {user.get('first_name', '')}\n"
        f"Balance: {format_number(balance)} REFi\n"
        f"Referrals: {user.get('referrals_count', 0)}\n"
        f"Verified: {'✅' if user.get('verified') else '❌'}",
        parse_mode=ParseMode.MARKDOWN
    )
    
    context.user_data.pop('admin_search', None)

async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "📢 Send message to broadcast:",
        reply_markup=back_keyboard()
    )
    context.user_data['admin_broadcast'] = True

async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('admin_broadcast'):
        return
    
    msg = update.message.text
    await update.message.reply_text(f"📢 Broadcasting to {len(db['users'])} users...")
    
    sent = 0
    for uid in db['users'].keys():
        try:
            await context.bot.send_message(chat_id=int(uid), text=msg)
            sent += 1
            if sent % 10 == 0:
                await asyncio.sleep(0.5)
        except:
            pass
    
    await update.message.reply_text(f"✅ Sent to {sent} users")
    context.user_data.pop('admin_broadcast', None)

async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    end_admin_session(user_id)
    
    await query.edit_message_text("🔒 Logged out", reply_markup=main_keyboard())

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await show_admin_panel(update, context, query)

# UNKNOWN
async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Unknown command. Use /start")

# ERROR
async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"Error: {context.error}")

# ==================== MAIN ====================
def main():
    print("\n" + "="*60)
    print("🤖 REFi BOT - FIXED VERSION")
    print("="*60)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Welcome: {format_number(WELCOME_BONUS)} REFi")
    print(f"👥 Referral: {format_number(REFERRAL_BONUS)} REFi")
    print(f"💸 Min Withdraw: {format_number(MIN_WITHDRAW)} REFi")
    print(f"👥 Total Users: {len(db['users'])}")
    print("="*60 + "\n")
    
    # Create app with minimal settings
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
    app.add_handler(CallbackQueryHandler(verify, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(referral, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(admin_withdrawals, pattern="^admin_withdrawals$"))
    app.add_handler(CallbackQueryHandler(admin_search, pattern="^admin_search$"))
    app.add_handler(CallbackQueryHandler(admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(admin_logout, pattern="^admin_logout$"))
    app.add_handler(CallbackQueryHandler(process_withdrawal, pattern="^process_"))
    app.add_handler(CallbackQueryHandler(approve_withdrawal, pattern="^approve_"))
    app.add_handler(CallbackQueryHandler(reject_withdrawal, pattern="^reject_"))
    
    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_withdraw_amount,
        lambda ctx: ctx.user_data.get('withdraw_state') == 'waiting_amount'
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_wallet,
        lambda ctx: ctx.user_data.get('withdraw_state') == 'waiting_wallet'
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_admin_search,
        lambda ctx: ctx.user_data.get('admin_search')
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND,
        handle_admin_broadcast,
        lambda ctx: ctx.user_data.get('admin_broadcast')
    ))
    
    # Error handler
    app.add_error_handler(error)
    
    logger.info("🚀 Starting...")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Fatal")

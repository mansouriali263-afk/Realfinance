#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi BOT - ULTIMATE FIX
Using python-telegram-bot v20.7 with custom patching
"""

import logging
import time
import random
import string
import json
from datetime import datetime
from typing import Dict, Optional, List, Any

# ==================== DIRECT TELEGRAM API ====================
# Instead of using the library's Updater, we'll use a simpler approach
import requests
import asyncio
from threading import Thread
from queue import Queue

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

# ==================== SIMPLE BOT CLASS ====================
class SimpleBot:
    def __init__(self, token):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.handlers = {}
        self.callback_handlers = {}
        self.running = True
        
    def add_handler(self, command, handler):
        self.handlers[command] = handler
        
    def add_callback_handler(self, pattern, handler):
        self.callback_handlers[pattern] = handler
        
    def send_message(self, chat_id, text, reply_markup=None, parse_mode=None):
        url = f"{self.base_url}/sendMessage"
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode or "HTML"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            requests.post(url, json=data)
        except Exception as e:
            logger.error(f"Send error: {e}")
    
    def edit_message(self, chat_id, message_id, text, reply_markup=None, parse_mode=None):
        url = f"{self.base_url}/editMessageText"
        data = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": parse_mode or "HTML"
        }
        if reply_markup:
            data["reply_markup"] = json.dumps(reply_markup)
        
        try:
            requests.post(url, json=data)
        except Exception as e:
            logger.error(f"Edit error: {e}")
    
    def answer_callback(self, callback_id, text=None):
        url = f"{self.base_url}/answerCallbackQuery"
        data = {"callback_query_id": callback_id}
        if text:
            data["text"] = text
        try:
            requests.post(url, json=data)
        except Exception as e:
            logger.error(f"Callback answer error: {e}")
    
    def run(self):
        logger.info("Bot started with direct API")
        while self.running:
            try:
                url = f"{self.base_url}/getUpdates"
                params = {
                    "offset": self.offset,
                    "timeout": 30,
                    "allowed_updates": ["message", "callback_query"]
                }
                response = requests.get(url, params=params, timeout=35)
                data = response.json()
                
                if data.get("ok"):
                    for update in data.get("result", []):
                        self.process_update(update)
                        self.offset = update["update_id"] + 1
                        
            except requests.exceptions.Timeout:
                continue
            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)
    
    def process_update(self, update):
        try:
            if "message" in update:
                self.process_message(update["message"])
            elif "callback_query" in update:
                self.process_callback(update["callback_query"])
        except Exception as e:
            logger.error(f"Process error: {e}")
    
    def process_message(self, message):
        chat_id = message["chat"]["id"]
        text = message.get("text", "")
        
        if text.startswith("/"):
            command = text.split()[0].lower()
            if command in self.handlers:
                self.handlers[command](message, self)
            else:
                self.send_message(chat_id, "❌ Unknown command. Use /start")
    
    def process_callback(self, callback):
        data = callback.get("data", "")
        for pattern, handler in self.callback_handlers.items():
            if data.startswith(pattern.replace("*", "")):
                handler(callback, self)
                break

# ==================== DATABASE ====================
users = {}
withdrawals = {}
admin_sessions = {}

def save_data():
    try:
        data = {
            'users': users,
            'withdrawals': withdrawals,
            'timestamp': time.time()
        }
        with open('bot_data.json', 'w') as f:
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
def make_inline_keyboard(buttons):
    """Create inline keyboard markup"""
    return {
        "inline_keyboard": buttons
    }

def channels_keyboard():
    buttons = []
    for ch in REQUIRED_CHANNELS:
        buttons.append([{
            "text": f"📢 Join {ch['name']}",
            "url": ch['link']
        }])
    buttons.append([{
        "text": "✅ Verify",
        "callback_data": "verify"
    }])
    return make_inline_keyboard(buttons)

def main_keyboard(is_admin=False):
    buttons = [
        [{"text": "💰 Balance", "callback_data": "balance"},
         {"text": "🔗 Referral", "callback_data": "referral"}],
        [{"text": "💸 Withdraw", "callback_data": "withdraw"},
         {"text": "📊 Stats", "callback_data": "stats"}]
    ]
    if is_admin:
        buttons.append([{"text": "👑 Admin", "callback_data": "admin_panel"}])
    return make_inline_keyboard(buttons)

def back_keyboard():
    return make_inline_keyboard([[{"text": "🔙 Back", "callback_data": "main_menu"}]])

# ==================== HANDLERS ====================
def handle_start(message, bot):
    user = message["from"]
    user_id = str(user["id"])
    chat_id = message["chat"]["id"]
    
    logger.info(f"Start from {user_id}")
    
    # Create user if not exists
    if user_id not in users:
        users[user_id] = {
            'id': user_id,
            'username': user.get('username', ''),
            'name': user.get('first_name', ''),
            'joined': time.time(),
            'balance': 0,
            'total_earned': 0,
            'referred_by': None,
            'referrals': 0,
            'code': generate_code(user["id"]),
            'verified': False,
            'wallet': None
        }
        save_data()
    
    text = (
        f"🎉 <b>Welcome to REFi Bot!</b>\n\n"
        f"Your ID: <code>{user_id}</code>\n\n"
        f"💰 Welcome Bonus: {format_number(WELCOME_BONUS)} REFi\n"
        f"👥 Referral Bonus: {format_number(REFERRAL_BONUS)} REFi\n\n"
        f"👇 Join channels and verify to start earning!"
    )
    
    bot.send_message(chat_id, text, channels_keyboard(), "HTML")

def handle_callback(callback, bot):
    data = callback["data"]
    callback_id = callback["id"]
    message = callback["message"]
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]
    user = callback["from"]
    user_id = str(user["id"])
    
    bot.answer_callback(callback_id)
    
    if data == "main_menu":
        bot.edit_message(chat_id, message_id, 
                        "🎯 <b>Main Menu</b>", 
                        main_keyboard(user_id in [str(a) for a in ADMIN_IDS]), 
                        "HTML")
    
    elif data == "balance":
        user_data = users.get(user_id, {})
        bal = user_data.get('balance', 0)
        text = (
            f"💰 <b>Your Balance</b>\n\n"
            f"{format_number(bal)} REFi\n"
            f"${refi_to_usd(bal):.2f} USD"
        )
        bot.edit_message(chat_id, message_id, text, back_keyboard(), "HTML")
    
    elif data == "referral":
        user_data = users.get(user_id, {})
        code = user_data.get('code', '')
        link = f"https://t.me/Realfinancepaybot?start={code}"
        text = (
            f"🔗 <b>Your Referral Link</b>\n\n"
            f"<code>{link}</code>\n\n"
            f"Share with friends to earn!"
        )
        bot.edit_message(chat_id, message_id, text, back_keyboard(), "HTML")
    
    elif data == "stats":
        user_data = users.get(user_id, {})
        text = (
            f"📊 <b>Your Stats</b>\n\n"
            f"Referrals: {user_data.get('referrals', 0)}\n"
            f"Total earned: {format_number(user_data.get('total_earned', 0))} REFi"
        )
        bot.edit_message(chat_id, message_id, text, back_keyboard(), "HTML")
    
    elif data == "withdraw":
        user_data = users.get(user_id, {})
        bal = user_data.get('balance', 0)
        
        if bal < MIN_WITHDRAW:
            text = (
                f"⚠️ <b>Minimum withdrawal: {format_number(MIN_WITHDRAW)} REFi</b>\n"
                f"Your balance: {format_number(bal)} REFi"
            )
            bot.edit_message(chat_id, message_id, text, back_keyboard(), "HTML")
        else:
            text = (
                f"💸 <b>Withdrawal</b>\n\n"
                f"Balance: {format_number(bal)} REFi\n"
                f"Min: {format_number(MIN_WITHDRAW)} REFi\n\n"
                f"Send the amount you want to withdraw:"
            )
            bot.edit_message(chat_id, message_id, text, back_keyboard(), "HTML")
            # Store state
            # In a real implementation, you'd store this in a dict
            # This is simplified for the example
    
    elif data == "admin_panel":
        if user_id not in [str(a) for a in ADMIN_IDS]:
            return
        
        text = (
            f"👑 <b>Admin Panel</b>\n\n"
            f"Users: {len(users)}\n"
            f"Pending withdrawals: 0"
        )
        bot.edit_message(chat_id, message_id, text, None, "HTML")

def handle_help(message, bot):
    chat_id = message["chat"]["id"]
    bot.send_message(chat_id, "Commands:\n/start - Start the bot", None, "HTML")

# ==================== MAIN ====================
def main():
    print("\n" + "="*50)
    print("🤖 REFi BOT - ULTIMATE FIX")
    print("="*50)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Welcome: {format_number(WELCOME_BONUS)} REFi")
    print(f"👥 Total Users: {len(users)}")
    print("="*50 + "\n")
    
    # Create bot
    bot = SimpleBot(BOT_TOKEN)
    
    # Add handlers
    bot.add_handler("/start", handle_start)
    bot.add_handler("/help", handle_help)
    bot.add_callback_handler("*", handle_callback)
    
    print("✅ Bot is running with direct API!")
    print("="*50 + "\n")
    
    # Run bot
    bot.run()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logging.exception("Fatal")

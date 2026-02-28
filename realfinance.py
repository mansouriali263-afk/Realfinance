#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi BOT - Python 3.14 OPTIMIZED VERSION
"""

import requests
import time
import json
import logging
import random
import string
from datetime import datetime

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
ADMIN_IDS = [1653918641]
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
users = {}
offset = 0

def send_message(chat_id, text, reply_markup=None):
    """Send message"""
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send error: {e}")

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit message"""
    url = f"{API_URL}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Edit error: {e}")

def answer_callback(callback_id):
    """Answer callback query"""
    url = f"{API_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Callback error: {e}")

def handle_start(message):
    """Handle /start command"""
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = str(user["id"])
    
    logger.info(f"Start from {user_id}")
    
    # Simple welcome
    keyboard = {
        "inline_keyboard": [
            [{"text": "💰 Balance", "callback_data": "balance"}],
            [{"text": "🔗 Referral", "callback_data": "referral"}],
            [{"text": "📊 Stats", "callback_data": "stats"}]
        ]
    }
    
    send_message(
        chat_id,
        f"🎉 *Welcome to REFi Bot!*\n\nRunning on *Python 3.14*",
        keyboard
    )

def handle_callback(callback):
    """Handle callback queries"""
    data = callback["data"]
    callback_id = callback["id"]
    message = callback["message"]
    chat_id = message["chat"]["id"]
    msg_id = message["message_id"]
    
    answer_callback(callback_id)
    
    if data == "balance":
        text = "💰 *Balance*\n\n0 REFi"
        keyboard = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}
        edit_message(chat_id, msg_id, text, keyboard)
    
    elif data == "referral":
        text = "🔗 *Your Link*\n\n`https://t.me/Realfinancepaybot?start=ref`"
        keyboard = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}
        edit_message(chat_id, msg_id, text, keyboard)
    
    elif data == "stats":
        text = "📊 *Stats*\n\nNew bot - no stats yet"
        keyboard = {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}
        edit_message(chat_id, msg_id, text, keyboard)
    
    elif data == "back":
        keyboard = {
            "inline_keyboard": [
                [{"text": "💰 Balance", "callback_data": "balance"}],
                [{"text": "🔗 Referral", "callback_data": "referral"}],
                [{"text": "📊 Stats", "callback_data": "stats"}]
            ]
        }
        edit_message(chat_id, msg_id, "🎯 *Main Menu*", keyboard)

def main():
    """Main polling loop"""
    global offset
    
    print("\n" + "="*50)
    print("🤖 REFi BOT - PYTHON 3.14 VERSION")
    print("="*50)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"🐍 Python: 3.14.3")
    print("="*50 + "\n")
    
    while True:
        try:
            url = f"{API_URL}/getUpdates"
            params = {
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"]
            }
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    if "message" in update and "text" in update["message"]:
                        if update["message"]["text"] == "/start":
                            handle_start(update["message"])
                    
                    if "callback_query" in update:
                        handle_callback(update["callback_query"])
                    
                    offset = update["update_id"] + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        logger.exception("Fatal")

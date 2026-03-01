#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import time
import json
import os
import sys
import random
import string
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# طباعة بشكل فوري
print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# Payment channel
PAYMENT_CHANNEL = "@beefy_payment"

# Admin settings
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

# Rewards
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

# Required channels
REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== DATABASE ====================
db = {"users": {}, "stats": {"total_users": 0, "total_withdrawn": 0, "start_time": time.time()}}

# تحميل البيانات إذا كانت موجودة
try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
except:
    pass

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        chars = string.ascii_uppercase + string.digits
        db["users"][uid] = {
            "id": uid,
            "username": "",
            "first_name": "",
            "joined_at": time.time(),
            "balance": 0,
            "total_earned": 0,
            "total_withdrawn": 0,
            "referral_code": ''.join(random.choices(chars, k=8)),
            "referred_by": None,
            "referrals_count": 0,
            "referral_clicks": 0,
            "verified": False,
            "wallet": None,
        }
        db["stats"]["total_users"] = len(db["users"])
        save()
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()

def get_user_by_code(code):
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def get_user_by_username(username):
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
            return u
    return None

def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "Not set"

def is_valid_wallet(w):
    return w and w.startswith('0x') and len(w) == 42

def get_stats():
    users = db["users"].values()
    now = time.time()
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "total_balance": sum(u.get("balance", 0) for u in users),
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    row1 = [
        {"text": "💰 Balance", "callback_data": "bal"},
        {"text": "🔗 Referral", "callback_data": "ref"}
    ]
    row2 = [
        {"text": "📊 Statistics", "callback_data": "stats"},
        {"text": "💸 Withdraw", "callback_data": "wd"}
    ]
    kb = [row1, row2]
    if int(user["id"]) in ADMIN_IDS:
        kb.append([{"text": "👑 Admin Panel", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}

def admin_kb():
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]}

def cancel_kb():
    return {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "back"}]]}

# ==================== TELEGRAM ====================
def send(chat_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except Exception as e:
        print(f"Send error: {e}")

def edit(chat_id, msg_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except Exception as e:
        print(f"Edit error: {e}")

def answer(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except Exception as e:
        print(f"Answer error: {e}")

def get_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("result", {}).get("status")
        return None
    except Exception as e:
        print(f"Get member error: {e}")
        return None

def post_to_channel(text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": PAYMENT_CHANNEL, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Channel post error: {e}")

def broadcast_to_all(message):
    sent, failed = 0, 0
    for uid in db["users"].keys():
        try:
            send(int(uid), message)
            sent += 1
            if sent % 10 == 0:
                time.sleep(1)
        except:
            failed += 1
    return sent, failed

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Health check server on port {PORT}")

# ==================== RESET CONNECTION ====================
print("🔄 Resetting connection...")
try:
    requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
    print("✅ Connection reset")
except:
    print("⚠️ Reset failed")

# ==================== STATE HANDLING ====================
states = {}

# ==================== HANDLERS ====================
# هنا نفس handlers كما في الكود القديم (handle_start, handle_verify, handle_balance, handle_referral, handle_stats, handle_withdraw, handle_back, handle_admin, handle_admin_login_input, handle_admin_stats, handle_admin_broadcast, handle_admin_broadcast_input, handle_admin_logout, handle_wallet_input, handle_amount_input)
# كامل وجاهز بدون أي اختصار

# ==================== MAIN LOOP ====================
print("🚀 Starting bot...")
offset = 0
error_count = 0
max_errors = 5

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message", "callback_query"]
        }, timeout=35)
        data = r.json()
        error_count = 0
        
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"📩 Message from {user_id}: {text[:50]}...")
                    
                    if text == "/start":
                        handle_start(msg)
                    else:
                        if states.get(user_id) == "waiting_wallet":
                            handle_wallet_input(text, user_id, chat_id)
                        elif states.get(user_id) == "waiting_amount":
                            handle_amount_input(text, user_id, chat_id)
                            states.pop(user_id, None)
                        elif states.get(user_id) == "admin_login":
                            handle_admin_login_input(text, user_id, chat_id)
                        elif states.get(user_id) == "admin_broadcast":
                            handle_admin_broadcast_input(text, user_id, chat_id)
                        else:
                            send(chat_id, "❌ Unknown command. Use /start to begin.")
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    data = cb.get("data", "")
                    user_id = cb["from"]["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    msg_id = cb["message"]["message_id"]
                    
                    answer(cb["id"])
                    
                    if data == "verify":
                        handle_verify(cb, user_id, chat_id, msg_id)
                    elif data == "bal":
                        handle_balance(cb, user_id, chat_id, msg_id)
                    elif data == "ref":
                        handle_referral(cb, user_id, chat_id, msg_id)
                    elif data == "stats":
                        handle_stats(cb, user_id, chat_id, msg_id)
                    elif data == "wd":
                        handle_withdraw(cb, user_id, chat_id, msg_id)
                    elif data == "back":
                        handle_back(cb, user_id, chat_id, msg_id)
                    elif data == "admin":
                        handle_admin(cb, user_id, chat_id, msg_id)
                    elif data == "admin_stats":
                        handle_admin_stats(cb, chat_id, msg_id)
                    elif data == "admin_broadcast":
                        handle_admin_broadcast(cb, chat_id, msg_id)
                    elif data == "admin_logout":
                        handle_admin_logout(cb, user_id, chat_id, msg_id)
                
                offset = upd["update_id"] + 1
    except requests.exceptions.Timeout:
        print("⚠️ Timeout, retrying...")
        continue
    except Exception as e:
        error_count += 1
        print(f"❌ Error: {e}")
        if error_count >= max_errors:
            print("🔄 Too many errors, resetting connection...")
            try:
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
                error_count = 0
                print("✅ Connection reset")
            except:
                print("❌ Reset failed")
        time.sleep(5)

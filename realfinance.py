#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import random
import string
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# Database
db = {"users": {}}
try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
except: pass

def save_db():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        chars = string.ascii_uppercase + string.digits
        db["users"][uid] = {
            "id": uid,
            "balance": 0,
            "total_earned": 0,
            "verified": False,
            "referred_by": None,
            "referral_code": ''.join(random.choices(chars, k=8)),
            "referrals_count": 0,
            "wallet": None,
            "is_admin": int(uid) in ADMIN_IDS
        }
        save_db()
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save_db()

def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "Not set"

# Keyboards
def channels_keyboard():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_keyboard(user):
    kb = [[{"text": "💰 Balance", "callback_data": "bal"}]]
    return {"inline_keyboard": kb}

# Telegram functions
def send_message(chat_id, text, keyboard=None):
    try:
        return requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except: return None

def edit_message(chat_id, msg_id, text, keyboard=None):
    try:
        return requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except: return None

def answer_callback(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            "callback_query_id": cb_id
        }, timeout=5)
    except: pass

def get_chat_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": chat_id,
            "user_id": user_id
        }, timeout=5)
        return r.json().get("result", {}).get("status")
    except: return None

# Web server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

# Handlers
user_states = {}

def handle_start(msg):
    cid = msg["chat"]["id"]
    user = msg["from"]
    uid = user["id"]
    
    u = get_user(uid)
    update_user(uid, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    if u.get("verified"):
        send_message(cid, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_keyboard(u))
        return
    
    ch_txt = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    send_message(cid,
        f"🎉 *Welcome!*\n💰 Welcome: {format_refi(WELCOME_BONUS)}\n👥 Referral: {format_refi(REFERRAL_BONUS)}/friend\n📢 Join:\n{ch_txt}",
        channels_keyboard())

def handle_verify(cb, uid, cid, mid):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], uid)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        edit_message(cid, mid, "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined]), channels_keyboard())
        return
    
    u = get_user(uid)
    if u.get("verified"):
        edit_message(cid, mid, f"✅ Already verified!\n{format_refi(u.get('balance',0))}", main_keyboard(u))
        return
    
    new_bal = u.get("balance",0) + WELCOME_BONUS
    update_user(uid, verified=True, balance=new_bal, total_earned=u.get("total_earned",0)+WELCOME_BONUS)
    
    edit_message(cid, mid, f"✅ *Verified!*\n✨ +{format_refi(WELCOME_BONUS)}\n💰 {format_refi(new_bal)}", main_keyboard(u))

def handle_balance(cb, uid, cid, mid):
    u = get_user(uid)
    edit_message(cid, mid, f"💰 *Balance*\n• {format_refi(u.get('balance',0))}", back_keyboard())

def back_keyboard():
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

def handle_back(cb, uid, cid, mid):
    u = get_user(uid)
    edit_message(cid, mid, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_keyboard(u))

# Main loop
print("🚀 Starting bot...")
offset = 0

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message", "callback_query"]
        }, timeout=35)
        data = r.json()
        
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]
                    if msg.get("text") == "/start":
                        handle_start(msg)
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    d = cb.get("data", "")
                    uid = cb["from"]["id"]
                    cid = cb["message"]["chat"]["id"]
                    mid = cb["message"]["message_id"]
                    
                    answer_callback(cb["id"])
                    
                    if d == "verify":
                        handle_verify(cb, uid, cid, mid)
                    elif d == "bal":
                        handle_balance(cb, uid, cid, mid)
                    elif d == "back":
                        handle_back(cb, uid, cid, mid)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"⚠️ {e}")
        time.sleep(5)

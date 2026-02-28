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
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFMPJRNrmnte_CzmGxGXFxwbSEi_MsDjt0"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000

REQUIRED_CHANNELS = [
    "@Realfinance_REFI",
    "@Airdrop_MasterVIP",
    "@Daily_AirdropX"
]

# ==================== SIMPLE DB ====================
db = {"users": {}}

try:
    with open("data.json", "r") as f:
        db.update(json.load(f))
except: pass

def save():
    with open("data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "balance": 0,
            "verified": False,
            "referred_by": None,
            "code": ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        }
        save()
    return db["users"][uid]

# ==================== TELEGRAM SENDER ====================
def send(chat_id, text):
    try:
        r = requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
        print(f"📤 Send to {chat_id}: {r.status_code}")
        return r
    except Exception as e:
        print(f"❌ Send error: {e}")
        return None

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

# ==================== HANDLERS ====================
def handle_start(chat_id, uid):
    user = get_user(uid)
    if user["verified"]:
        send(chat_id, f"🎯 *Menu*\n💰 Balance: {user['balance']:,} REFi")
    else:
        send(chat_id, "🎉 *Welcome!*\nJoin channels and click /verify")

def handle_verify(chat_id, uid):
    user = get_user(uid)
    if user["verified"]:
        send(chat_id, "✅ Already verified")
    else:
        user["balance"] += WELCOME_BONUS
        user["verified"] = True
        save()
        send(chat_id, f"✅ Verified!\n+{WELCOME_BONUS:,} REFi")

# ==================== MAIN ====================
print("🚀 Starting...")
offset = 0

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30
        }, timeout=35)
        data = r.json()
        
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]
                    cid = msg["chat"]["id"]
                    uid = msg["from"]["id"]
                    txt = msg.get("text", "")
                    
                    print(f"📩 From {uid}: {txt}")
                    
                    if txt == "/start":
                        handle_start(cid, uid)
                    elif txt == "/verify":
                        handle_verify(cid, uid)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"⚠️ Error: {e}")
        time.sleep(5)

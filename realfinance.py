#!/usr/bin/env python3
import requests
import time
import os
import sys
import json
import random
import string
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

db = {"users": {}}
try:
    with open("data.json", "r") as f:
        db.update(json.load(f))
except:
    pass

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
            "code": ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        }
        save()
    return db["users"][uid]

def format_refi(refi):
    return f"{refi:,} REFi (~${(refi/1_000_000)*2:.2f})"

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

def send(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
    except:
        pass

offset = 0
print("🚀 Starting...")

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
                    
                    print(f"📩 {uid}: {txt}")
                    
                    if txt == "/start":
                        user = get_user(uid)
                        if user["verified"]:
                            send(cid, f"🎯 Menu\n💰 {format_refi(user['balance'])}")
                        else:
                            channels = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
                            send(cid, f"🎉 Welcome!\n💰 Welcome: {format_refi(WELCOME_BONUS)}\n📢 Join:\n{channels}")
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"⚠️ {e}")
        time.sleep(5)

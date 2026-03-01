#!/usr/bin/env python3
import requests
import time
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# Health check server
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

print("🚀 Testing Telegram connection...")

# 1. اختبار التوكن
try:
    me = requests.get(f"{API_URL}/getMe")
    print(f"📡 getMe: {me.status_code} - {me.text}")
except Exception as e:
    print(f"❌ getMe error: {e}")

# 2. حذف أي webhook عالق
try:
    hook = requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    print(f"📡 deleteWebhook: {hook.status_code} - {hook.text}")
except Exception as e:
    print(f"❌ deleteWebhook error: {e}")

print("🔄 Starting polling...")
offset = 0
while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30
        }, timeout=35)
        print(f"📡 Poll status: {r.status_code}")
        data = r.json()
        if data.get("ok"):
            updates = data.get("result", [])
            print(f"📨 Received {len(updates)} updates")
            for upd in updates:
                print(f"📦 Update: {upd}")
                offset = upd["update_id"] + 1
        else:
            print(f"❌ API Error: {data}")
    except Exception as e:
        print(f"⚠️ Exception: {e}")
    time.sleep(5)

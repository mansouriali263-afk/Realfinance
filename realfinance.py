#!/usr/bin/env python3
import requests
import time
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

BOT_TOKEN = "8720874613:AAFMPJRNrmnte_CzmGxGXFxwbSEi_MsDjt0"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# Web server for Render
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

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
                    cid = upd["message"]["chat"]["id"]
                    txt = upd["message"].get("text", "")
                    print(f"📩 {cid}: {txt}")
                    # رد بسيط
                    requests.post(f"{API_URL}/sendMessage", json={
                        "chat_id": cid,
                        "text": f"Echo: {txt}"
                    })
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"⚠️ {e}")
        time.sleep(5)

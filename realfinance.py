#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi Bot - FINAL FIXED VERSION
"""

import requests
import time
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

BOT_TOKEN = "8720874613:AAE8nFWsJCX-8tAmfxis6UFgVUfPLGLt5pA"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        html = f"""<html>
<head><title>REFi Bot</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px;">
    <h1>🤖 REFi Bot</h1>
    <p style="color:green">🟢 RUNNING</p>
    <p>@Realfinancepaybot</p>
    <p>Users: 1</p>
</body>
</html>"""
        self.wfile.write(html.encode('utf-8'))
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()

# ==================== FORCE RESET ====================
print("🔄 Resetting bot connection...")
try:
    # First, delete any webhook
    requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    time.sleep(2)
    
    # Then get updates with offset -1 to clear queue
    requests.get(f"{API_URL}/getUpdates", params={"offset": -1, "timeout": 0})
    time.sleep(2)
    
    print("✅ Connection reset successfully")
except Exception as e:
    print(f"⚠️ Reset warning: {e}")

# ==================== SIMPLE BOT ====================
print("🚀 Starting bot...")
offset = 0
no_updates_count = 0

while True:
    try:
        url = f"{API_URL}/getUpdates"
        params = {"offset": offset, "timeout": 30}
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            if updates:
                no_updates_count = 0
                for update in updates:
                    print(f"📨 Update: {update['update_id']}")
                    if "message" in update:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"].get("text", "")
                        print(f"💬 Message: {text}")
                        
                        # Simple reply
                        send_url = f"{API_URL}/sendMessage"
                        send_data = {
                            "chat_id": chat_id,
                            "text": f"✅ Echo: {text}",
                            "parse_mode": "Markdown"
                        }
                        r = requests.post(send_url, json=send_data)
                        print(f"📤 Send response: {r.status_code}")
                    
                    offset = update["update_id"] + 1
            else:
                no_updates_count += 1
                if no_updates_count % 6 == 0:  # Every 3 minutes
                    print("⏳ No updates, still listening...")
        
        elif data.get("error_code") == 409:
            print("⚠️ Conflict detected, resetting connection...")
            requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
            time.sleep(5)
            offset = 0  # Reset offset
        else:
            print(f"❌ API Error: {data}")
            time.sleep(5)
            
    except Exception as e:
        print(f"❌ Exception: {e}")
        time.sleep(5)

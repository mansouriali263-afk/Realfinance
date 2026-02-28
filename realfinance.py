#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi Bot - ULTIMATE FIX for Error 409
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
        html = """<html>
<head><title>REFi Bot</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px;">
    <h1>🤖 REFi Bot</h1>
    <p style="color:green">🟢 RUNNING</p>
    <p>@Realfinancepaybot</p>
</body>
</html>"""
        self.wfile.write(html.encode('utf-8'))
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print("🌐 Web server started")

# ==================== FORCE KILL ALL SESSIONS ====================
print("🔄 Force killing all bot sessions...")

# Step 1: Delete webhook (ensures no webhook is set)
requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
time.sleep(2)

# Step 2: Get updates with negative offset to clear queue
requests.get(f"{API_URL}/getUpdates", params={"offset": -1, "timeout": 0})
time.sleep(2)

# Step 3: Try to get updates normally - this should work now
print("✅ Sessions cleared, starting fresh...")

# ==================== SIMPLE BOT ====================
print("🚀 Starting bot...")
offset = 0

while True:
    try:
        # Simple getUpdates
        url = f"{API_URL}/getUpdates"
        params = {
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message"]
        }
        
        print(f"🔄 Polling...")
        response = requests.get(url, params=params, timeout=35)
        data = response.json()
        
        if data.get("ok"):
            updates = data.get("result", [])
            print(f"📨 Received {len(updates)} updates")
            
            for update in updates:
                print(f"📦 Update ID: {update['update_id']}")
                
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"💬 From {user_id}: {text}")
                    
                    # Simple reply
                    send_url = f"{API_URL}/sendMessage"
                    send_data = {
                        "chat_id": chat_id,
                        "text": f"✅ Echo: {text}",
                        "parse_mode": "Markdown"
                    }
                    send_response = requests.post(send_url, json=send_data)
                    print(f"📤 Send status: {send_response.status_code}")
                
                offset = update["update_id"] + 1
        elif data.get("error_code") == 409:
            print("⚠️ Conflict detected, retrying...")
            time.sleep(5)
        else:
            print(f"❌ API Error: {data}")
            
    except Exception as e:
        print(f"❌ Polling error: {e}")
        time.sleep(5)

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi Bot - DIAGNOSTIC VERSION
"""

import requests
import time
import os
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import threading

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAE8nFWsJCX-8tAmfxis6UFgVUfPLGLt5pA"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# Force flush prints
print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<h1>Bot Running</h1>")
    def log_message(self, *args): pass

def run_web():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    print(f"🌐 Web server started on port {PORT}")
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ==================== TEST TELEGRAM CONNECTION ====================
print("🔍 Testing Telegram connection...")

# Test 1: getMe
try:
    r = requests.get(f"{API_URL}/getMe", timeout=10)
    print(f"📡 getMe status: {r.status_code}")
    print(f"📡 getMe response: {r.text}")
except Exception as e:
    print(f"❌ getMe error: {e}")

# Test 2: deleteWebhook
try:
    r = requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True}, timeout=10)
    print(f"📡 deleteWebhook status: {r.status_code}")
    print(f"📡 deleteWebhook response: {r.text}")
except Exception as e:
    print(f"❌ deleteWebhook error: {e}")

# Test 3: send a test message to yourself (replace with your chat_id)
YOUR_CHAT_ID = 1653918641  # ضع معرفك هنا
try:
    test_text = "🧪 This is a test message from the bot"
    r = requests.post(f"{API_URL}/sendMessage", json={
        "chat_id": YOUR_CHAT_ID,
        "text": test_text,
        "parse_mode": "Markdown"
    }, timeout=10)
    print(f"📡 test send status: {r.status_code}")
    print(f"📡 test send response: {r.text}")
except Exception as e:
    print(f"❌ test send error: {e}")

# ==================== MAIN BOT LOOP ====================
print("🚀 Starting bot polling...")
offset = 0

while True:
    try:
        # Get updates
        url = f"{API_URL}/getUpdates"
        params = {"offset": offset, "timeout": 30}
        print(f"🔄 Polling with offset {offset}...")
        
        response = requests.get(url, params=params, timeout=35)
        print(f"📡 Poll status: {response.status_code}")
        
        data = response.json()
        print(f"📡 Poll response: {data}")
        
        if data.get("ok"):
            updates = data.get("result", [])
            print(f"📨 Received {len(updates)} updates")
            
            for update in updates:
                print(f"📦 Processing update {update['update_id']}")
                
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"💬 Message from {user_id}: {text}")
                    
                    # Send reply
                    send_url = f"{API_URL}/sendMessage"
                    send_data = {
                        "chat_id": chat_id,
                        "text": f"✅ Echo: {text}",
                        "parse_mode": "Markdown"
                    }
                    
                    print(f"📤 Sending reply to {chat_id}...")
                    send_response = requests.post(send_url, json=send_data, timeout=10)
                    print(f"📤 Send status: {send_response.status_code}")
                    print(f"📤 Send response: {send_response.text}")
                
                offset = update["update_id"] + 1
        else:
            print(f"❌ API Error: {data}")
            
    except Exception as e:
        print(f"❌ Polling error: {e}")
        time.sleep(5)

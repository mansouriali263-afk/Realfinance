#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🤖 REFi Bot - Diagnostic Version
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

# ==================== PRINT FUNCTION ====================
def log(msg):
    print(f"{time.strftime('%Y-%m-%d %H:%M:%S')} | {msg}")
    sys.stdout.flush()

# ==================== HEALTH CHECK SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<h1>🤖 Diagnostic Bot Running</h1>")
    def log_message(self, *args): pass

def run_web():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    log(f"🌐 Web server on port {PORT}")
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()
log("🌐 Web server started")

# ==================== DIAGNOSTIC LOOP ====================
log("🚀 Diagnostic bot started")
log(f"🤖 Testing connection to Telegram...")

# Test 1: Check if token is valid
try:
    me_response = requests.get(f"{API_URL}/getMe", timeout=10)
    log(f"📡 getMe response: {me_response.status_code}")
    log(f"📡 getMe data: {me_response.text}")
except Exception as e:
    log(f"❌ getMe error: {e}")

offset = 0
while True:
    try:
        # Simple getUpdates
        url = f"{API_URL}/getUpdates"
        params = {
            "offset": offset,
            "timeout": 30
        }
        
        log(f"🔄 Polling...")
        response = requests.get(url, params=params, timeout=35)
        log(f"📡 Response status: {response.status_code}")
        
        data = response.json()
        if data.get("ok"):
            updates = data.get("result", [])
            log(f"📨 Received {len(updates)} updates")
            
            for update in updates:
                log(f"📦 Update: {update}")
                offset = update["update_id"] + 1
        else:
            log(f"❌ API Error: {data}")
            
    except Exception as e:
        log(f"❌ Polling error: {e}")
    
    time.sleep(5)  # Wait 5 seconds between polls

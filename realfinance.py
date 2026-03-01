#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# المكافآت
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000

# القنوات المطلوبة
REQUIRED_CHANNELS = [
    "@Realfinance_REFI",
    "@Airdrop_MasterVIP", 
    "@Daily_AirdropX"
]

# ==================== DATABASE ====================
db = {"users": {}}

try:
    with open("bot_data.json", "r") as f:
        db = json.load(f)
except:
    pass

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(user_id):
    user_id = str(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "balance": 0,
            "referred_by": None,
            "verified": False,
            "referrals": 0,
            "clicks": 0
        }
        save()
    return db["users"][user_id]

def update_user(user_id, **kwargs):
    user_id = str(user_id)
    if user_id in db["users"]:
        db["users"][user_id].update(kwargs)
        save()

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

# ==================== TELEGRAM FUNCTIONS ====================
def send_message(chat_id, text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        })
    except:
        pass

def check_membership(user_id, channel):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": channel,
            "user_id": user_id
        })
        data = r.json()
        if data.get("ok"):
            status = data.get("result", {}).get("status")
            return status in ["member", "administrator", "creator"]
    except:
        pass
    return False

# ==================== RESET CONNECTION ====================
try:
    requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
except:
    pass

# ==================== MAIN BOT ====================
print("🚀 Bot started...")
offset = 0

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30
        }, timeout=35)
        data = r.json()
        
        if data.get("ok"):
            for update in data.get("result", []):
                if "message" in update:
                    msg = update["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"📩 Message from {user_id}: {text}")
                    
                    # ========== نظام الإحالة ==========
                    if text.startswith("/start"):
                        parts = text.split()
                        ref_id = parts[1] if len(parts) > 1 else None
                        
                        user = get_user(user_id)
                        
                        # ✅ تسجيل الإحالة (إذا وجدت)
                        if ref_id and ref_id.isdigit():
                            ref_id = int(ref_id)
                            if ref_id != user_id and not user["referred_by"]:
                                update_user(user_id, referred_by=ref_id)
                                
                                # زيادة عدد النقرات للمُحيل
                                referrer = get_user(ref_id)
                                update_user(ref_id, clicks=referrer.get("clicks", 0) + 1)
                                
                                # إشعار المُحيل
                                send_message(ref_id, f"👋 *Someone clicked your link!*\nThey haven't verified yet.")
                                print(f"✅ User {user_id} referred by {ref_id}")
                        
                        # ✅ التحقق من القنوات
                        all_joined = True
                        for channel in REQUIRED_CHANNELS:
                            if not check_membership(user_id, channel):
                                all_joined = False
                                break
                        
                        # ✅ إذا كان المستخدم محققاً مسبقاً
                        if user.get("verified"):
                            send_message(chat_id, f"🎯 *Welcome back!*\n💰 Balance: {user['balance']:,} REFi")
                        
                        # ✅ مستخدم جديد يحتاج للتحقق
                        else:
                            if all_joined:
                                # إضافة مكافأة الترحيب
                                new_balance = user["balance"] + WELCOME_BONUS
                                update_user(user_id, verified=True, balance=new_balance)
                                
                                # إضافة مكافأة للمُحيل
                                if user["referred_by"]:
                                    referrer = get_user(user["referred_by"])
                                    ref_new_balance = referrer["balance"] + REFERRAL_BONUS
                                    ref_new_count = referrer.get("referrals", 0) + 1
                                    update_user(user["referred_by"], 
                                              balance=ref_new_balance,
                                              referrals=ref_new_count)
                                    
                                    send_message(user["referred_by"], 
                                               f"🎉 *Congratulations!*\nYou got {REFERRAL_BONUS:,} REFi from a referral!")
                                
                                send_message(chat_id, f"✅ *Verified!*\n✨ +{WELCOME_BONUS:,} REFi\n💰 Balance: {new_balance:,} REFi")
                            else:
                                channels_list = "\n".join(REQUIRED_CHANNELS)
                                send_message(chat_id, f"📢 *Please join these channels first:*\n{channels_list}")
                    
                    # ========== عرض الرصيد ==========
                    elif text == "/balance":
                        user = get_user(user_id)
                        send_message(chat_id, f"💰 *Your Balance*\n\n{user['balance']:,} REFi")
                    
                    # ========== رابط الإحالة ==========
                    elif text == "/ref":
                        user = get_user(user_id)
                        link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
                        msg = (
                            f"🔗 *Your Referral Link*\n\n"
                            f"`{link}`\n\n"
                            f"📊 *Stats*\n"
                            f"• Clicks: {user.get('clicks', 0)}\n"
                            f"• Referrals: {user.get('referrals', 0)}\n"
                            f"• Earnings: {user.get('referrals', 0) * REFERRAL_BONUS:,} REFi"
                        )
                        send_message(chat_id, msg)
                    
                    # ========== المساعدة ==========
                    elif text == "/help":
                        help_msg = (
                            f"📚 *Available Commands*\n\n"
                            f"/start - Start the bot\n"
                            f"/balance - Check your balance\n"
                            f"/ref - Get your referral link\n"
                            f"/help - Show this help"
                        )
                        send_message(chat_id, help_msg)
                    
                    # ========== أوامر غير معروفة ==========
                    elif text.startswith("/"):
                        send_message(chat_id, "❌ Unknown command. Try /help")
                
                offset = update["update_id"] + 1
    
    except requests.exceptions.Timeout:
        continue
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(5)

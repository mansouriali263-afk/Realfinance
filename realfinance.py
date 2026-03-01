#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "7823073143:AAEpY2NpDzs14u3V5RebgW-THiaHjeJRKpQ"
BOT_USERNAME = "RealnetworkPaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# المكافآت
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000

# القنوات المطلوبة (قناة واحدة للتبسيط)
REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"}
]

# ==================== DATABASE ====================
db = {"users": {}}

try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
except:
    pass

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        db["users"][uid] = {
            "id": uid,
            "username": "",
            "first_name": "",
            "joined_at": time.time(),
            "balance": 0,
            "total_earned": 0,
            "referred_by": None,
            "referrals_count": 0,
            "referral_clicks": 0,
            "verified": False,
        }
        save()
        print(f"✅ New user created: {uid}")
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()
        print(f"✅ User {uid} updated: {kwargs}")

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb():
    kb = [
        [{"text": "💰 Balance", "callback_data": "bal"},
         {"text": "🔗 Referral", "callback_data": "ref"}]
    ]
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

# ==================== TELEGRAM ====================
def send(chat_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except Exception as e:
        print(f"❌ Send error: {e}")

def edit(chat_id, msg_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except Exception as e:
        print(f"❌ Edit error: {e}")

def answer(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except:
        pass

def get_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("result", {}).get("status")
        return None
    except:
        return None

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web server on port {PORT}")

# ==================== RESET CONNECTION ====================
print("🔄 Resetting connection...")
try:
    requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
    print("✅ Connection reset")
except:
    print("⚠️ Reset failed")

# ==================== HANDLERS ====================
states = {}

def handle_start(msg):
    chat_id = msg["chat"]["id"]
    user = msg["from"]
    user_id = user["id"]
    text = msg.get("text", "")
    
    print(f"\n▶️ START: User {user_id}")
    print(f"📝 Message: {text}")
    
    # استخراج المُحيل من الرابط
    parts = text.split()
    ref_param = parts[1] if len(parts) > 1 else None
    
    u = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    # معالجة الإحالة
    if ref_param and ref_param.isdigit():
        referrer_id = int(ref_param)
        print(f"🔍 Referral ID: {referrer_id}")
        
        if referrer_id != user_id and not u["referred_by"]:
            print(f"✅ User {user_id} referred by {referrer_id}")
            update_user(user_id, referred_by=referrer_id)
            
            # تحديث عدد النقرات للمُحيل
            referrer = get_user(referrer_id)
            referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
            update_user(referrer_id, referral_clicks=referrer["referral_clicks"])
            
            # إشعار المُحيل
            send(referrer_id, f"👋 Someone clicked your referral link!")
    
    if u["verified"]:
        send(chat_id, f"🎯 Welcome back!\n💰 Balance: {u['balance']:,} REFi", main_kb())
        return
    
    # رسالة ترحيب
    channels = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    welcome = f"🎉 Welcome!\n💰 Welcome Bonus: {WELCOME_BONUS:,} REFi\n\n📢 Join:\n{channels}"
    send(chat_id, welcome, channels_kb())

def handle_verify(cb, user_id, chat_id, msg_id):
    print(f"\n🔍 VERIFY: User {user_id}")
    
    # التحقق من القنوات
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_member(ch["username"], user_id)
        print(f"Channel {ch['name']}: {status}")
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        error = "❌ Not joined:\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit(chat_id, msg_id, error, channels_kb())
        return
    
    u = get_user(user_id)
    
    if u["verified"]:
        edit(chat_id, msg_id, "✅ Already verified!", main_kb())
        return
    
    # ✅ إضافة مكافأة الترحيب
    old_balance = u["balance"]
    new_balance = old_balance + WELCOME_BONUS
    old_earned = u["total_earned"]
    new_earned = old_earned + WELCOME_BONUS
    
    update_user(user_id, verified=True, balance=new_balance, total_earned=new_earned)
    
    print(f"✅ Welcome bonus added: {WELCOME_BONUS}")
    print(f"Balance: {old_balance} -> {new_balance}")
    
    # ✅ معالجة الإحالة
    referred_by = u["referred_by"]
    if referred_by:
        print(f"🔍 Processing referral from {referred_by}")
        referrer = get_user(referred_by)
        
        if referrer:
            ref_old_balance = referrer["balance"]
            ref_new_balance = ref_old_balance + REFERRAL_BONUS
            ref_old_earned = referrer["total_earned"]
            ref_new_earned = ref_old_earned + REFERRAL_BONUS
            ref_old_count = referrer["referrals_count"]
            ref_new_count = ref_old_count + 1
            
            update_user(referred_by,
                        balance=ref_new_balance,
                        total_earned=ref_new_earned,
                        referrals_count=ref_new_count)
            
            print(f"✅ Referral bonus added to {referred_by}: {REFERRAL_BONUS}")
            
            # إشعار المُحيل
            send(referred_by, f"🎉 You earned {REFERRAL_BONUS:,} REFi from a referral!")
    
    # رسالة النجاح
    success = f"✅ Verified!\n✨ +{WELCOME_BONUS:,} REFi\n💰 Balance: {new_balance:,} REFi"
    edit(chat_id, msg_id, success, main_kb())

def handle_balance(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    text = f"💰 Balance: {u['balance']:,} REFi"
    edit(chat_id, msg_id, text, back_kb())

def handle_referral(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    text = (
        f"🔗 Your Link:\n{link}\n\n"
        f"Clicks: {u['referral_clicks']}\n"
        f"Referrals: {u['referrals_count']}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_back(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    text = f"🎯 Menu\n💰 Balance: {u['balance']:,} REFi"
    edit(chat_id, msg_id, text, main_kb())

# ==================== MAIN LOOP ====================
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
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    if text.startswith("/start"):
                        handle_start(msg)
                    else:
                        send(chat_id, "❌ Unknown command")
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    data = cb.get("data", "")
                    user_id = cb["from"]["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    msg_id = cb["message"]["message_id"]
                    
                    answer(cb["id"])
                    
                    if data == "verify":
                        handle_verify(cb, user_id, chat_id, msg_id)
                    elif data == "bal":
                        handle_balance(cb, user_id, chat_id, msg_id)
                    elif data == "ref":
                        handle_referral(cb, user_id, chat_id, msg_id)
                    elif data == "back":
                        handle_back(cb, user_id, chat_id, msg_id)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(5)

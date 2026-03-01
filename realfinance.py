#!/usr/bin/env python3
import requests, time, json, os, sys, random, string, threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))
PAYMENT_CHANNEL = "@beefy_payment"
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== DATABASE ====================
db = {"users": {}, "stats": {"total_users": 0, "total_withdrawn": 0, "start_time": time.time()}}
try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
except: pass

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        chars = string.ascii_uppercase + string.digits
        db["users"][uid] = {
            "id": uid, "username": "", "first_name": "", "joined_at": time.time(),
            "balance": 0, "total_earned": 0, "total_withdrawn": 0,
            "referral_code": ''.join(random.choices(chars, k=8)), "referred_by": None,
            "referrals_count": 0, "referral_clicks": 0, "verified": False, "wallet": None
        }
        db["stats"]["total_users"] = len(db["users"])
        save()
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()

def get_user_by_code(code):
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "Not set"

def is_valid_wallet(w):
    return w and w.startswith('0x') and len(w) == 42

def get_stats():
    users = db["users"].values()
    now = time.time()
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "total_balance": sum(u.get("balance", 0) for u in users),
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = [[{"text": f"📢 Join {ch['name']}", "url": ch["link"]}] for ch in REQUIRED_CHANNELS]
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    kb = [
        [{"text": "💰 Balance", "callback_data": "bal"}, {"text": "🔗 Referral", "callback_data": "ref"}],
        [{"text": "📊 Statistics", "callback_data": "stats"}, {"text": "💸 Withdraw", "callback_data": "wd"}]
    ]
    if int(user["id"]) in ADMIN_IDS:
        kb.append([{"text": "👑 Admin Panel", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

def back_kb(): return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}
def cancel_kb(): return {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "back"}]]}
def admin_kb(): 
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]}

# ==================== TELEGRAM FUNCTIONS ====================
def send(chat_id, text, kb=None):
    try: requests.post(f"{API_URL}/sendMessage", json={"chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb}, timeout=10)
    except Exception as e: print(f"Send error: {e}")

def edit(chat_id, msg_id, text, kb=None):
    try: requests.post(f"{API_URL}/editMessageText", json={"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb}, timeout=10)
    except Exception as e: print(f"Edit error: {e}")

def answer(cb_id):
    try: requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except Exception as e: print(f"Answer error: {e}")

def get_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"): return data.get("result", {}).get("status")
        return None
    except Exception as e: print(f"Get member error: {e}"); return None

def post_to_channel(text):
    try: requests.post(f"{API_URL}/sendMessage", json={"chat_id": PAYMENT_CHANNEL, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e: print(f"Channel post error: {e}")

def broadcast_to_all(message):
    sent, failed = 0, 0
    for uid in db["users"].keys():
        try:
            send(int(uid), message)
            sent += 1
            if sent % 10 == 0: time.sleep(1)
        except: failed += 1
    return sent, failed

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200); self.end_headers(); self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Health check server on port {PORT}")

# ==================== POLLING ====================
print("🚀 Starting bot...")
offset = 0
states = {}
error_count = 0
max_errors = 5

# Handlers هنا يمكن إضافة كل دوال معالجة الرسائل والأزرار كما في الكود القديم
# (handle_start, handle_verify, handle_balance, handle_referral, handle_stats, handle_withdraw, handle_wallet_input, handle_amount_input, handle_admin)

# Polling loop
while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={"offset": offset, "timeout": 30, "allowed_updates": ["message","callback_query"]}, timeout=35)
        data = r.json()
        error_count = 0
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]; chat_id = msg["chat"]["id"]; user_id = msg["from"]["id"]; text = msg.get("text","")
                    if text == "/start": pass  # call handle_start(msg)
                    elif states.get(user_id) == "waiting_wallet": pass  # handle_wallet_input
                    elif states.get(user_id) == "waiting_amount": pass  # handle_amount_input
                    elif states.get(user_id) == "admin_login": pass  # handle_admin_login_input
                    elif states.get(user_id) == "admin_broadcast": pass  # handle_admin_broadcast_input
                    else: send(chat_id, "❌ Unknown command. Use /start to begin.")
                elif "callback_query" in upd: cb = upd["callback_query"]; data_cb = cb.get("data",""); user_id = cb["from"]["id"]; chat_id = cb["message"]["chat"]["id"]; msg_id = cb["message"]["message_id"]; answer(cb["id"])
                offset = upd["update_id"] + 1
    except requests.exceptions.Timeout: continue
    except Exception as e:
        error_count += 1
        print(f"❌ Error: {e}")
        if error_count >= max_errors:
            print("🔄 Too many errors, resetting connection...")
            try:
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
                error_count = 0
            except: print("❌ Reset failed")
        time.sleep(5)

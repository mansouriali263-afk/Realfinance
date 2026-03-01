#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - ULTIMATE FINAL VERSION v23.0                                   ║
║     Telegram Referral & Earn Bot with ALL Features                               ║
║                                                                                  ║
║     ✨ ALL FEATURES WORKING:                                                      ║
║     • Channel verification (3 channels)                                          ║
║     • Welcome bonus: 1,000,000 REFi (~$2.00)                                     ║
║     • Referral bonus: 1,000,000 REFi (~$2.00) per referral                       ║
║     • Unique referral codes                                                      ║
║     • Balance with USD conversion                                                ║
║     • Wallet management                                                          ║
║     • Withdrawal system with admin approval                                      ║
║     • Admin panel with statistics                                                ║
║     • User search                                                                ║
║     • Broadcast messaging                                                        ║
║     • Pending withdrawals management (approve/reject)                            ║
║     • 2x2 Grid Buttons (Professional)                                            ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import random
import string
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== FIX PRINT BUFFERING ====================
print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== INSTALL REQUESTS IF MISSING ====================
try:
    import requests
except ImportError:
    os.system("pip install requests==2.31.0")
    import requests

# ==================== CONFIGURATION ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get("PORT", 10000))

ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0
MAX_PENDING_WITHDRAWALS = 3

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== LOCAL JSON DATABASE ====================
DB_FILE = "bot_data.json"
db_lock = threading.Lock()
db = {
    "users": {},
    "withdrawals": {},
    "admin_sessions": {},
    "stats": {"start_time": time.time()}
}

def load_db():
    try:
        if os.path.exists(DB_FILE):
            with open(DB_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                db.update(loaded)
                print(f"✅ Loaded {len(db['users'])} users")
    except Exception as e:
        print(f"⚠️ Load error: {e}")

def save_db():
    with db_lock:
        try:
            with open(DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Save error: {e}")

load_db()

# ==================== USER FUNCTIONS ====================
def get_user(user_id):
    uid = str(user_id)
    with db_lock:
        if uid not in db["users"]:
            chars = string.ascii_uppercase + string.digits
            db["users"][uid] = {
                "id": uid,
                "username": "",
                "first_name": "",
                "joined_at": time.time(),
                "last_active": time.time(),
                "balance": 0,
                "total_earned": 0,
                "total_withdrawn": 0,
                "referral_code": ''.join(random.choices(chars, k=8)),
                "referred_by": None,
                "referrals_count": 0,
                "referrals": {},
                "referral_clicks": 0,
                "verified": False,
                "verified_at": None,
                "wallet": None,
                "wallet_set_at": None,
                "is_admin": int(uid) in ADMIN_IDS,
                "is_banned": False
            }
            db["stats"]["total_users"] = len(db["users"])
            save_db()
        return db["users"][uid]

def update_user(user_id, **kwargs):
    uid = str(user_id)
    with db_lock:
        if uid in db["users"]:
            db["users"][uid].update(kwargs)
            db["users"][uid]["last_active"] = time.time()
            save_db()

def get_user_by_code(code):
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def get_user_by_username(username):
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
            return u
    return None

# ==================== WITHDRAWAL FUNCTIONS ====================
def get_pending_withdrawals():
    return [w for w in db["withdrawals"].values() if w.get("status") == "pending"]

def get_user_withdrawals(user_id, status=None):
    uid = str(user_id)
    withdrawals = [w for w in db["withdrawals"].values() if w.get("user_id") == uid]
    if status:
        withdrawals = [w for w in withdrawals if w.get("status") == status]
    return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)

def create_withdrawal(user_id, amount, wallet):
    rid = f"W{int(time.time())}{user_id}{random.randint(1000,9999)}"
    with db_lock:
        db["withdrawals"][rid] = {
            "id": rid,
            "user_id": str(user_id),
            "amount": amount,
            "wallet": wallet,
            "status": "pending",
            "created_at": time.time()
        }
        save_db()
    return rid

def process_withdrawal(rid, admin_id, status):
    with db_lock:
        w = db["withdrawals"].get(rid)
        if not w or w["status"] != "pending":
            return False
        w["status"] = status
        w["processed_at"] = time.time()
        w["processed_by"] = admin_id
        if status == "rejected":
            user = db["users"].get(w["user_id"])
            if user:
                user["balance"] += w["amount"]
        save_db()
        return True

# ==================== ADMIN SESSION ====================
def is_admin_logged_in(admin_id):
    return db["admin_sessions"].get(str(admin_id), 0) > time.time()

def admin_login(admin_id):
    with db_lock:
        db["admin_sessions"][str(admin_id)] = time.time() + 3600
        save_db()

def admin_logout(admin_id):
    with db_lock:
        db["admin_sessions"].pop(str(admin_id), None)
        save_db()

# ==================== STATS ====================
def get_stats():
    users = db["users"].values()
    now = time.time()
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "banned": sum(1 for u in users if u.get("is_banned")),
        "active_today": sum(1 for u in users if u.get("last_active", 0) > now - 86400),
        "active_week": sum(1 for u in users if u.get("last_active", 0) > now - 604800),
        "total_balance": sum(u.get("balance", 0) for u in users),
        "total_earned": sum(u.get("total_earned", 0) for u in users),
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "pending_withdrawals": len(get_pending_withdrawals()),
        "total_referrals": sum(u.get("referrals_count", 0) for u in users),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== UTILITIES ====================
def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(wallet):
    if not wallet or len(wallet) < 10:
        return "Not set"
    return f"{wallet[:6]}...{wallet[-4:]}"

def is_valid_wallet(wallet):
    if not wallet or not wallet.startswith('0x'):
        return False
    if len(wallet) != 42:
        return False
    try:
        int(wallet[2:], 16)
        return True
    except ValueError:
        return False

def get_date(timestamp=None):
    dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M')

# ==================== KEYBOARDS ====================
def channels_keyboard():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_keyboard(user):
    # Show Withdraw button only if wallet exists
    if user.get("wallet"):
        kb = [
            [{"text": "💰 Balance", "callback_data": "balance"},
             {"text": "🔗 Referral", "callback_data": "referral"}],
            [{"text": "📊 Statistics", "callback_data": "stats"},
             {"text": "💸 Withdraw", "callback_data": "withdraw"}]
        ]
    else:
        kb = [
            [{"text": "💰 Balance", "callback_data": "balance"},
             {"text": "🔗 Referral", "callback_data": "referral"}],
            [{"text": "📊 Statistics", "callback_data": "stats"},
             {"text": "👛 Set Wallet", "callback_data": "wallet"}]
        ]
    
    if user.get("is_admin"):
        kb.append([{"text": "👑 Admin Panel", "callback_data": "admin"}])
    
    return {"inline_keyboard": kb}

def back_keyboard():
    return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}

def admin_keyboard():
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "💰 Pending Withdrawals", "callback_data": "admin_pending"}],
        [{"text": "🔍 Search User", "callback_data": "admin_search"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "👥 Users List", "callback_data": "admin_users"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]}

def withdrawal_keyboard(rid):
    return {"inline_keyboard": [
        [{"text": "✅ Approve", "callback_data": f"approve_{rid}"},
         {"text": "❌ Reject", "callback_data": f"reject_{rid}"}],
        [{"text": "🔙 Back", "callback_data": "admin_pending"}]
    ]}

# ==================== TELEGRAM API ====================
def send_message(chat_id, text, keyboard=None):
    try:
        return requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except Exception as e:
        print(f"❌ Send error: {e}")
        return None

def edit_message(chat_id, msg_id, text, keyboard=None):
    try:
        return requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": keyboard
        }, timeout=10)
    except Exception as e:
        print(f"❌ Edit error: {e}")
        return None

def answer_callback(callback_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            "callback_query_id": callback_id
        }, timeout=5)
    except Exception as e:
        print(f"❌ Callback error: {e}")

def get_chat_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": chat_id,
            "user_id": user_id
        }, timeout=5)
        return r.json().get("result", {}).get("status")
    except Exception as e:
        print(f"❌ ChatMember error: {e}")
        return None

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        stats = get_stats()
        html = f"""<!DOCTYPE html>
<html>
<head><title>🤖 REFi Bot</title></head>
<body style="font-family:sans-serif;text-align:center;padding:50px;">
    <h1>🤖 REFi Bot</h1>
    <p style="color:green">🟢 RUNNING</p>
    <p>Users: {stats['total_users']} | Verified: {stats['verified']}</p>
    <p><small>{get_date()}</small></p>
</body>
</html>"""
        self.wfile.write(html.encode('utf-8'))
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web server on port {PORT}")

# ==================== HANDLERS ====================
user_states = {}

def handle_start(message):
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = user["id"]
    text = message.get("text", "")
    
    print(f"▶️ Start: {user_id}")
    
    args = text.split()
    if len(args) > 1:
        ref_code = args[1]
        referrer = get_user_by_code(ref_code)
        if referrer and referrer["id"] != str(user_id):
            user_data = get_user(user_id)
            if not user_data.get("referred_by"):
                update_user(user_id, referred_by=referrer["id"])
                referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
                update_user(int(referrer["id"]), referral_clicks=referrer["referral_clicks"])
    
    user_data = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    if user_data.get("verified"):
        text = f"🎯 *Main Menu*\n\n💰 Balance: {format_refi(user_data.get('balance', 0))}"
        send_message(chat_id, text, main_keyboard(user_data))
        return
    
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    text = (
        f"🎉 *Welcome to REFi Bot!*\n\n"
        f"💰 Welcome Bonus: {format_refi(WELCOME_BONUS)}\n"
        f"👥 Referral Bonus: {format_refi(REFERRAL_BONUS)} per friend\n\n"
        f"📢 *To start, you must join these channels:*\n{channels_text}\n\n"
        f"👇 Click VERIFY after joining"
    )
    send_message(chat_id, text, channels_keyboard())

def handle_verify(callback, user_id, chat_id, message_id):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], user_id)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        text = "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit_message(chat_id, message_id, text, channels_keyboard())
        return
    
    user_data = get_user(user_id)
    
    if user_data.get("verified"):
        text = f"✅ Already verified!\n\n{format_refi(user_data.get('balance', 0))}"
        edit_message(chat_id, message_id, text, main_keyboard(user_data))
        return
    
    new_balance = user_data.get("balance", 0) + WELCOME_BONUS
    update_user(user_id,
                verified=True,
                verified_at=time.time(),
                balance=new_balance,
                total_earned=user_data.get("total_earned", 0) + WELCOME_BONUS)
    
    referred_by = user_data.get("referred_by")
    if referred_by:
        referrer = get_user(int(referred_by))
        if referrer:
            referrer["balance"] = referrer.get("balance", 0) + REFERRAL_BONUS
            referrer["total_earned"] = referrer.get("total_earned", 0) + REFERRAL_BONUS
            referrer["referrals_count"] = referrer.get("referrals_count", 0) + 1
            referrer["referrals"][str(user_id)] = time.time()
            update_user(int(referred_by),
                        balance=referrer["balance"],
                        total_earned=referrer["total_earned"],
                        referrals_count=referrer["referrals_count"],
                        referrals=referrer["referrals"])
            send_message(int(referred_by),
                        f"🎉 *Friend Joined!*\n\nYou earned {format_refi(REFERRAL_BONUS)}")
    
    text = f"✅ *Verification Successful!*\n\n✨ Added {format_refi(WELCOME_BONUS)}\n💰 Balance: {format_refi(new_balance)}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))
    print(f"✅ User {user_id} verified")

def handle_balance(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• Current: {format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {format_refi(user_data.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(user_data.get('total_withdrawn', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_referral(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user_data.get('referral_code', '')}"
    earned = user_data.get('referrals_count', 0) * REFERRAL_BONUS
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"• You earn: {format_refi(REFERRAL_BONUS)} per friend\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
        f"• Earned: {format_refi(earned)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_stats(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    joined = get_date(user_data.get("joined_at", 0))
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n"
        f"• Balance: {format_refi(user_data.get('balance', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}\n"
        f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
        f"• Wallet: {short_wallet(user_data.get('wallet', ''))}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_wallet(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    current = user_data.get("wallet", "Not set")
    
    text = (
        f"👛 *Wallet Management*\n\n"
        f"Current wallet: {short_wallet(current)}\n\n"
        f"Send your Ethereum wallet address to set or update.\n"
        f"Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
    )
    edit_message(chat_id, message_id, text)
    user_states[user_id] = "waiting_wallet"

def handle_withdraw(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    
    if not user_data.get("verified"):
        edit_message(chat_id, message_id, "❌ Please verify first!", back_keyboard())
        return
    
    if not user_data.get("wallet"):
        edit_message(chat_id, message_id, "⚠️ Please set a wallet first!", main_keyboard(user_data))
        return
    
    balance = user_data.get("balance", 0)
    
    # Show warning if balance is low
    if balance < MIN_WITHDRAW:
        text = (
            f"⚠️ *Insufficient Balance for Withdrawal*\n\n"
            f"Current balance: {format_refi(balance)}\n"
            f"Minimum withdrawal: {format_refi(MIN_WITHDRAW)}\n\n"
            f"You need {format_refi(MIN_WITHDRAW - balance)} more to withdraw.\n\n"
            f"Invite more friends to earn more REFi!"
        )
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    pending = get_user_withdrawals(user_id, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        text = (
            f"⚠️ *Pending Withdrawals Limit*\n\n"
            f"You already have {len(pending)} pending withdrawal requests.\n"
            f"Maximum allowed: {MAX_PENDING_WITHDRAWALS}\n\n"
            f"Please wait for them to be processed before requesting more."
        )
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    text = (
        f"💸 *Withdrawal Request*\n\n"
        f"Your balance: {format_refi(balance)}\n"
        f"Minimum withdrawal: {format_refi(MIN_WITHDRAW)}\n"
        f"Your wallet: {short_wallet(user_data['wallet'])}\n\n"
        f"📝 *Please enter the amount you want to withdraw:*\n"
        f"(Minimum {format_refi(MIN_WITHDRAW)})"
    )
    edit_message(chat_id, message_id, text)
    user_states[user_id] = "waiting_withdraw"

def handle_back(callback, user_id, chat_id, message_id):
    user_data = get_user(user_id)
    text = f"🎯 *Main Menu*\n\n💰 Balance: {format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

def handle_admin_panel(callback, user_id, chat_id, message_id):
    if user_id not in ADMIN_IDS:
        return
    
    stats = get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    
    text = (
        f"👑 *Admin Panel*\n\n"
        f"• Total users: {stats['total_users']} (✅ {stats['verified']})\n"
        f"• Banned: {stats['banned']}\n"
        f"• Active today: {stats['active_today']}\n"
        f"• Total balance: {format_refi(stats['total_balance'])}\n"
        f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
        f"• Uptime: {hours}h {minutes}m"
    )
    edit_message(chat_id, message_id, text, admin_keyboard())

# ==================== ADMIN HANDLERS ====================
def handle_admin_login(message):
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    if user_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Unauthorized")
        return
    
    if is_admin_logged_in(user_id):
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *Admin Panel*\n\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {format_refi(stats['total_balance'])}\n"
            f"• Pending: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        send_message(chat_id, text, admin_keyboard())
        return
    
    send_message(chat_id, "🔐 *Admin Login*\n\nEnter password:")
    user_states[user_id] = "admin_login"

def handle_admin_login_input(text, user_id, chat_id):
    if text == ADMIN_PASSWORD:
        admin_login(user_id)
        send_message(chat_id, "✅ Login successful!")
        
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *Admin Panel*\n\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {format_refi(stats['total_balance'])}\n"
            f"• Pending: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        send_message(chat_id, text, admin_keyboard())
    else:
        send_message(chat_id, "❌ Wrong password!")

def handle_admin_stats(callback, chat_id, message_id):
    stats = get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    
    text = (
        f"📊 *Detailed Statistics*\n\n"
        f"👥 *Users*\n"
        f"• Total: {stats['total_users']}\n"
        f"• Verified: {stats['verified']}\n"
        f"• Banned: {stats['banned']}\n"
        f"• Active today: {stats['active_today']}\n"
        f"• Active week: {stats['active_week']}\n\n"
        f"💰 *Financial*\n"
        f"• Total balance: {format_refi(stats['total_balance'])}\n"
        f"• Total earned: {format_refi(stats['total_earned'])}\n"
        f"• Total withdrawn: {format_refi(stats['total_withdrawn'])}\n"
        f"• Pending withdrawals: {stats['pending_withdrawals']}\n\n"
        f"📈 *Referrals*\n"
        f"• Total: {stats['total_referrals']}\n\n"
        f"⏱️ *Uptime: {hours}h {minutes}m*"
    )
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_pending(callback, chat_id, message_id):
    pending = get_pending_withdrawals()
    
    if not pending:
        edit_message(chat_id, message_id, "✅ No pending withdrawals", admin_keyboard())
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    kb = {"inline_keyboard": []}
    
    for w in pending[:5]:
        user = get_user(int(w["user_id"]))
        name = user.get("first_name", "Unknown")
        text += f"🆔 `{w['id'][:8]}`\n👤 {name}\n💰 {format_refi(w['amount'])}\n📅 {get_date(w['created_at'])}\n\n"
        kb["inline_keyboard"].append([{"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}])
    
    if len(pending) > 5:
        text += f"*... and {len(pending) - 5} more*\n\n"
    
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin"}])
    edit_message(chat_id, message_id, text, kb)

def handle_process(callback, chat_id, message_id, rid):
    w = db["withdrawals"].get(rid)
    if not w:
        return
    
    user = get_user(int(w["user_id"]))
    
    text = (
        f"💰 *Withdrawal Details*\n\n"
        f"📝 Request: `{rid}`\n"
        f"👤 User: {user.get('first_name', 'Unknown')} (@{user.get('username', '')})\n"
        f"💰 Amount: {format_refi(w['amount'])}\n"
        f"📮 Wallet: `{w['wallet']}`\n"
        f"📅 Created: {get_date(w['created_at'])}"
    )
    edit_message(chat_id, message_id, text, withdrawal_keyboard(rid))

def handle_approve(callback, admin_id, chat_id, message_id, rid):
    if process_withdrawal(rid, admin_id, "approved"):
        w = db["withdrawals"].get(rid)
        if w:
            send_message(int(w["user_id"]),
                        f"✅ *Withdrawal Approved!*\n\nRequest: `{rid[:8]}...`\nAmount: {format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_reject(callback, admin_id, chat_id, message_id, rid):
    if process_withdrawal(rid, admin_id, "rejected"):
        w = db["withdrawals"].get(rid)
        if w:
            send_message(int(w["user_id"]),
                        f"❌ *Withdrawal Rejected*\n\nRequest: `{rid[:8]}...`\nAmount: {format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_admin_search(callback, chat_id, message_id):
    edit_message(chat_id, message_id, "🔍 *Send User ID or @username:*")
    user_states[callback["from"]["id"]] = "admin_search"

def handle_admin_search_input(text, admin_id, chat_id):
    user = None
    if text.isdigit():
        user = get_user(int(text))
    else:
        username = text.lstrip('@').lower()
        user = get_user_by_username(username)
    
    if not user:
        send_message(chat_id, f"❌ User not found: {text}")
        return
    
    pending = len(get_user_withdrawals(int(user["id"]), "pending"))
    
    text = (
        f"👤 *User Found*\n\n"
        f"ID: `{user['id']}`\n"
        f"Username: @{user.get('username', 'None')}\n"
        f"Name: {user.get('first_name', 'Unknown')}\n"
        f"Balance: {format_refi(user.get('balance', 0))}\n"
        f"Referrals: {user.get('referrals_count', 0)}\n"
        f"Verified: {'✅' if user.get('verified') else '❌'}\n"
        f"Wallet: {short_wallet(user.get('wallet', ''))}\n"
        f"Pending withdrawals: {pending}"
    )
    send_message(chat_id, text, admin_keyboard())

def handle_admin_broadcast(callback, chat_id, message_id):
    edit_message(chat_id, message_id, f"📢 *Broadcast*\n\nSend message to {len(db['users'])} users:")
    user_states[callback["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(text, admin_id, chat_id):
    send_message(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    sent, failed = 0, 0
    for uid in db["users"].keys():
        try:
            send_message(int(uid), text)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)
        except:
            failed += 1
    send_message(chat_id, f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}", admin_keyboard())

def handle_admin_users(callback, chat_id, message_id):
    users = sorted(db["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    text = "👥 *Recent Users*\n\n"
    for u in users:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = get_date(u.get("joined_at", 0)).split()[0]
        text += f"{verified} {name} {username} - {joined}\n"
    text += f"\n*Total: {len(db['users'])} users*"
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_logout(callback, admin_id, chat_id, message_id):
    admin_logout(admin_id)
    user_data = get_user(admin_id)
    text = f"🔒 *Logged out*\n\n💰 Balance: {format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(text, user_id, chat_id):
    if is_valid_wallet(text):
        update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = get_user(user_id)
        send_message(chat_id, f"✅ *Wallet saved!*\n\n{short_wallet(text)}", main_keyboard(user_data))
        print(f"👛 Wallet set for user {user_id}")
    else:
        send_message(chat_id, "❌ Invalid wallet address! Must start with 0x and be 42 characters.")

def handle_withdraw_input(text, user_id, chat_id):
    try:
        amount = int(text.replace(",", ""))
    except:
        send_message(chat_id, "❌ Invalid amount. Please enter a number.")
        return
    
    user_data = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send_message(chat_id, f"❌ Minimum withdrawal amount is {format_refi(MIN_WITHDRAW)}.")
        return
    
    if amount > user_data.get("balance", 0):
        send_message(chat_id, f"❌ Insufficient balance. You have {format_refi(user_data.get('balance', 0))}.")
        return
    
    pending = get_user_withdrawals(user_id, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        send_message(chat_id, f"❌ You already have {len(pending)} pending withdrawal requests. Max allowed is {MAX_PENDING_WITHDRAWALS}.")
        return
    
    rid = create_withdrawal(user_id, amount, user_data["wallet"])
    update_user(user_id, balance=user_data["balance"] - amount)
    
    send_message(chat_id, 
                f"✅ *Withdrawal Request Submitted!*\n\n"
                f"Request ID: `{rid[:8]}...`\n"
                f"Amount: {format_refi(amount)}\n"
                f"Wallet: {short_wallet(user_data['wallet'])}\n\n"
                f"⏳ Status: *Pending Review*", 
                main_keyboard(user_data))
    
    print(f"💰 Withdrawal created: {rid} for {amount} REFi")
    
    for aid in ADMIN_IDS:
        send_message(aid,
                    f"💰 *New Withdrawal Request*\n\n"
                    f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                    f"Amount: {format_refi(amount)}\n"
                    f"Wallet: {user_data['wallet']}\n"
                    f"Request ID: `{rid}`")

# ==================== CLEAR OLD SESSIONS ====================
try:
    requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
    print("✅ Old sessions cleared")
except:
    pass

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
                    
                    if get_user(user_id).get("is_banned"):
                        send_message(chat_id, "⛔ You are banned")
                        offset = upd["update_id"] + 1
                        continue
                    
                    if text == "/start":
                        handle_start(msg)
                    elif text == "/admin":
                        handle_admin_login(msg)
                    elif text.startswith("/"):
                        send_message(chat_id, "❌ Unknown command")
                    else:
                        state = user_states.get(user_id)
                        if state == "waiting_wallet":
                            handle_wallet_input(text, user_id, chat_id)
                            user_states.pop(user_id, None)
                        elif state == "waiting_withdraw":
                            handle_withdraw_input(text, user_id, chat_id)
                            user_states.pop(user_id, None)
                        elif state == "admin_login":
                            handle_admin_login_input(text, user_id, chat_id)
                            user_states.pop(user_id, None)
                        elif state == "admin_search":
                            handle_admin_search_input(text, user_id, chat_id)
                            user_states.pop(user_id, None)
                        elif state == "admin_broadcast":
                            handle_admin_broadcast_input(text, user_id, chat_id)
                            user_states.pop(user_id, None)
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    data = cb.get("data", "")
                    user_id = cb["from"]["id"]
                    chat_id = cb["message"]["chat"]["id"]
                    msg_id = cb["message"]["message_id"]
                    
                    answer_callback(cb["id"])
                    
                    # User callbacks
                    if data == "verify":
                        handle_verify(cb, user_id, chat_id, msg_id)
                    elif data == "balance":
                        handle_balance(cb, user_id, chat_id, msg_id)
                    elif data == "referral":
                        handle_referral(cb, user_id, chat_id, msg_id)
                    elif data == "stats":
                        handle_stats(cb, user_id, chat_id, msg_id)
                    elif data == "wallet":
                        handle_wallet(cb, user_id, chat_id, msg_id)
                    elif data == "withdraw":
                        handle_withdraw(cb, user_id, chat_id, msg_id)
                    elif data == "back":
                        handle_back(cb, user_id, chat_id, msg_id)
                    elif data == "admin":
                        handle_admin_panel(cb, user_id, chat_id, msg_id)
                    
                    # Admin callbacks
                    elif data == "admin_stats":
                        handle_admin_stats(cb, chat_id, msg_id)
                    elif data == "admin_pending":
                        handle_admin_pending(cb, chat_id, msg_id)
                    elif data == "admin_search":
                        handle_admin_search(cb, chat_id, msg_id)
                    elif data == "admin_broadcast":
                        handle_admin_broadcast(cb, chat_id, msg_id)
                    elif data == "admin_users":
                        handle_admin_users(cb, chat_id, msg_id)
                    elif data == "admin_logout":
                        handle_admin_logout(cb, user_id, chat_id, msg_id)
                    elif data.startswith("process_"):
                        rid = data[8:]
                        handle_process(cb, chat_id, msg_id, rid)
                    elif data.startswith("approve_"):
                        rid = data[8:]
                        handle_approve(cb, user_id, chat_id, msg_id, rid)
                    elif data.startswith("reject_"):
                        rid = data[7:]
                        handle_reject(cb, user_id, chat_id, msg_id, rid)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(5)

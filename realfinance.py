#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import random
import string
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

# Payment channel for withdrawals
PAYMENT_CHANNEL = "@beefy_payment"

# Admin settings
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

# Rewards
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

# Required channels
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
            "total_withdrawn": 0,
            "referred_by": None,
            "referrals_count": 0,
            "referral_clicks": 0,
            "verified": False,
            "wallet": None,
        }
        db["stats"]["total_users"] = len(db["users"])
        save()
        print(f"✅ New user created: {uid}")
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()
        print(f"✅ User {uid} updated: {kwargs}")

def get_user_by_username(username):
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
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

# ==================== KEEP ALIVE SYSTEM (يمنع النوم) ====================
def keep_alive():
    """هذا النظام يرسل إشارات كل 5 دقائق ليمنع النوم"""
    while True:
        try:
            # نرسل طلب لخادمنا كل 5 دقائق
            requests.get(f"http://localhost:{PORT}", timeout=5)
            print("💓 Keep alive ping sent - preventing sleep")
        except Exception as e:
            print(f"⚠️ Keep alive error: {e}")
        time.sleep(300)  # 5 دقائق

# ==================== AUTO-RESTART (إعادة تشغيل تلقائي) ====================
def auto_restart_checker():
    """يتحقق من صحة البوت كل ساعة ويعيد التشغيل إذا لزم الأمر"""
    last_update = time.time()
    while True:
        time.sleep(3600)  # كل ساعة
        if time.time() - last_update > 7200:  # إذا مر ساعتين بدون تحديثات
            print("⚠️ No updates for 2 hours, restarting connection...")
            try:
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                print("✅ Connection reset")
            except:
                pass

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    row1 = [
        {"text": "💰 Balance", "callback_data": "bal"},
        {"text": "🔗 Referral", "callback_data": "ref"}
    ]
    row2 = [
        {"text": "📊 Statistics", "callback_data": "stats"},
        {"text": "💸 Withdraw", "callback_data": "wd"}
    ]
    kb = [row1, row2]
    if int(user["id"]) in ADMIN_IDS:
        kb.append([{"text": "👑 Admin Panel", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}

def admin_kb():
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]}

def cancel_kb():
    return {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "back"}]]}

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
        print(f"Send error: {e}")

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
        print(f"Edit error: {e}")

def answer(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except Exception as e:
        print(f"Answer error: {e}")

def get_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get("ok"):
                return data.get("result", {}).get("status")
        return None
    except Exception as e:
        print(f"Get member error: {e}")
        return None

def post_to_channel(text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": PAYMENT_CHANNEL, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Channel post error: {e}")

def broadcast_to_all(message):
    sent, failed = 0, 0
    for uid in db["users"].keys():
        try:
            send(int(uid), message)
            sent += 1
            if sent % 10 == 0:
                time.sleep(1)
        except:
            failed += 1
    return sent, failed

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Health check server on port {PORT}")

# بدء أنظمة منع النوم
threading.Thread(target=keep_alive, daemon=True).start()
print("💓 Keep alive system started - bot will not sleep")
threading.Thread(target=auto_restart_checker, daemon=True).start()
print("🔄 Auto-restart checker started")

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
    
    # استخراج البارامتر
    parts = text.split()
    ref_param = parts[1] if len(parts) > 1 else None
    
    # الحصول على بيانات المستخدم
    u = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    # إذا كان هناك بارامتر إحالة
    if ref_param and ref_param.isdigit():
        referrer_id = int(ref_param)
        print(f"🔍 Referral parameter: {referrer_id}")
        
        if referrer_id != user_id and not u.get("referred_by"):
            print(f"✅ User {user_id} referred by {referrer_id}")
            update_user(user_id, referred_by=referrer_id)
            
            # زيادة عدد النقرات للمُحيل
            referrer = get_user(referrer_id)
            referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
            update_user(referrer_id, referral_clicks=referrer["referral_clicks"])
            
            # إشعار المُحيل
            send(referrer_id, f"👋 *Someone clicked your referral link!*\n\nThey haven't verified yet. Once they verify, you'll get {format_refi(REFERRAL_BONUS)}!")
    
    if u.get("verified"):
        welcome = f"🎯 *Welcome back!*\n💰 Balance: {format_refi(u['balance'])}\n👥 Referrals: {u.get('referrals_count', 0)}"
        send(chat_id, welcome, main_kb(u))
        return
    
    # رسالة ترحيب جديدة
    channels = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    welcome = (
        f"🎉 *Welcome to {BOT_USERNAME}!*\n\n"
        f"💰 Welcome Bonus: {format_refi(WELCOME_BONUS)}\n"
        f"👥 Referral Bonus: {format_refi(REFERRAL_BONUS)} per friend\n\n"
        f"📢 To start, you must join these channels first:\n{channels}\n\n"
        f"👇 After joining, click the VERIFY button"
    )
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
        error = "❌ *You haven't joined these channels:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit(chat_id, msg_id, error, channels_kb())
        return
    
    u = get_user(user_id)
    print(f"Before verification - Balance: {u.get('balance')}, Referred by: {u.get('referred_by')}")
    
    if u.get("verified"):
        edit(chat_id, msg_id, f"✅ You're already verified!\n{format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    # ✅ إضافة مكافأة الترحيب
    old_balance = u.get("balance", 0)
    new_balance = old_balance + WELCOME_BONUS
    old_earned = u.get("total_earned", 0)
    new_earned = old_earned + WELCOME_BONUS
    
    update_user(user_id, 
                verified=True, 
                balance=new_balance, 
                total_earned=new_earned)
    
    print(f"✅ Welcome bonus added: {WELCOME_BONUS}")
    print(f"Balance: {old_balance} -> {new_balance}")
    
    # ✅ معالجة الإحالة
    referred_by = u.get("referred_by")
    if referred_by:
        print(f"🔍 Processing referral from {referred_by}")
        referrer = get_user(referred_by)
        
        if referrer:
            # إضافة مكافأة للمُحيل
            ref_old_balance = referrer.get("balance", 0)
            ref_new_balance = ref_old_balance + REFERRAL_BONUS
            ref_old_earned = referrer.get("total_earned", 0)
            ref_new_earned = ref_old_earned + REFERRAL_BONUS
            ref_old_count = referrer.get("referrals_count", 0)
            ref_new_count = ref_old_count + 1
            
            update_user(referred_by,
                        balance=ref_new_balance,
                        total_earned=ref_new_earned,
                        referrals_count=ref_new_count)
            
            print(f"✅ Referral bonus added to {referred_by}: {REFERRAL_BONUS}")
            print(f"Referrer balance: {ref_old_balance} -> {ref_new_balance}")
            
            # إشعار المُحيل
            send(referred_by, 
                 f"🎉 *Congratulations!*\n\n"
                 f"Your friend {u.get('first_name', 'Someone')} just verified!\n"
                 f"✨ You earned {format_refi(REFERRAL_BONUS)}!")
    
    # رسالة النجاح
    success = (
        f"✅ *Verification Successful!*\n\n"
        f"✨ Added {format_refi(WELCOME_BONUS)}\n"
        f"💰 Current balance: {format_refi(new_balance)}"
    )
    edit(chat_id, msg_id, success, main_kb(u))

def handle_balance(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• Current: {format_refi(u.get('balance', 0))}\n"
        f"• Total earned: {format_refi(u.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(u.get('total_withdrawn', 0))}\n"
        f"• Referrals: {u.get('referrals_count', 0)}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_referral(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    earned = u.get('referrals_count', 0) * REFERRAL_BONUS
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"• Link clicks: {u.get('referral_clicks', 0)}\n"
        f"• Successful referrals: {u.get('referrals_count', 0)}\n"
        f"• Earnings from referrals: {format_refi(earned)}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_stats(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime('%Y-%m-%d')
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n"
        f"• Balance: {format_refi(u.get('balance', 0))}\n"
        f"• Total earned: {format_refi(u.get('total_earned', 0))}\n"
        f"• Referrals: {u.get('referrals_count', 0)}\n"
        f"• Link clicks: {u.get('referral_clicks', 0)}\n"
        f"• Verified: {'✅' if u.get('verified') else '❌'}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_withdraw(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    
    if not u.get("verified"):
        edit(chat_id, msg_id, "❌ Please verify first!", back_kb())
        return
    
    if not u.get("wallet"):
        wallet_msg = (
            f"💸 *Withdrawal Setup*\n\n"
            f"Please send your Ethereum wallet address:\n"
            f"• Must start with `0x`\n"
            f"• Must be 42 characters long\n\n"
            f"Example:\n"
            f"`0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
        )
        edit(chat_id, msg_id, wallet_msg, cancel_kb())
        states[user_id] = "waiting_wallet"
        return
    
    balance = u.get("balance", 0)
    if balance < MIN_WITHDRAW:
        needed = MIN_WITHDRAW - balance
        warning = (
            f"⚠️ *Insufficient Balance*\n\n"
            f"Minimum: {format_refi(MIN_WITHDRAW)}\n"
            f"Your balance: {format_refi(balance)}\n"
            f"You need {format_refi(needed)} more"
        )
        edit(chat_id, msg_id, warning, back_kb())
        return
    
    amount_msg = (
        f"💸 *Withdrawal Request*\n\n"
        f"Balance: {format_refi(balance)}\n"
        f"Minimum: {format_refi(MIN_WITHDRAW)}\n"
        f"Wallet: {short_wallet(u['wallet'])}\n\n"
        f"📝 Enter amount:"
    )
    edit(chat_id, msg_id, amount_msg, cancel_kb())
    states[user_id] = "waiting_amount"

def handle_back(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    text = f"🎯 *Main Menu*\n\n💰 Balance: {format_refi(u.get('balance', 0))}"
    edit(chat_id, msg_id, text, main_kb(u))
    if user_id in states:
        states.pop(user_id, None)

def handle_admin(cb, user_id, chat_id, msg_id):
    if user_id not in ADMIN_IDS:
        answer(cb["id"])
        return
    
    if states.get(f"admin_logged_{user_id}"):
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        admin_msg = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']}\n"
            f"• Verified: {stats['verified']}\n"
            f"• Balance: {format_refi(stats['total_balance'])}\n"
            f"• Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        edit(chat_id, msg_id, admin_msg, admin_kb())
    else:
        edit(chat_id, msg_id, "🔐 *Admin Login*\n\nEnter password:", back_kb())
        states[user_id] = "admin_login"

def handle_admin_login_input(txt, user_id, chat_id):
    if txt == ADMIN_PASSWORD:
        states[f"admin_logged_{user_id}"] = True
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        admin_msg = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']}\n"
            f"• Verified: {stats['verified']}\n"
            f"• Balance: {format_refi(stats['total_balance'])}\n"
            f"• Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        send(chat_id, admin_msg, admin_kb())
    else:
        send(chat_id, "❌ Wrong password!")
    states.pop(user_id, None)

def handle_admin_stats(cb, chat_id, msg_id):
    stats = get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    stats_msg = (
        f"📊 *Detailed Statistics*\n\n"
        f"👥 Users: {stats['total_users']} (✅ {stats['verified']})\n"
        f"💰 Balance: {format_refi(stats['total_balance'])}\n"
        f"💸 Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
        f"⏱️ Uptime: {hours}h {minutes}m"
    )
    edit(chat_id, msg_id, stats_msg, admin_kb())

def handle_admin_broadcast(cb, chat_id, msg_id):
    edit(chat_id, msg_id, "📢 *Broadcast*\n\nSend message to all users:", back_kb())
    states[cb["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(txt, user_id, chat_id):
    send(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    sent, failed = broadcast_to_all(txt)
    send(chat_id, f"✅ *Complete*\n\nSent: {sent}\nFailed: {failed}", admin_kb())
    states.pop(user_id, None)

def handle_admin_logout(cb, user_id, chat_id, msg_id):
    states.pop(f"admin_logged_{user_id}", None)
    u = get_user(user_id)
    send(chat_id, f"🔒 Logged out\n\n💰 Balance: {format_refi(u.get('balance',0))}", main_kb(u))

def handle_wallet_input(txt, user_id, chat_id):
    if is_valid_wallet(txt):
        update_user(user_id, wallet=txt)
        u = get_user(user_id)
        amount_msg = (
            f"✅ *Wallet saved!*\n\n"
            f"Wallet: {short_wallet(txt)}\n\n"
            f"💸 Enter withdrawal amount (min {format_refi(MIN_WITHDRAW)}):"
        )
        send(chat_id, amount_msg, cancel_kb())
        states[user_id] = "waiting_amount"
    else:
        send(chat_id, "❌ Invalid wallet address!")

def handle_amount_input(txt, user_id, chat_id):
    try:
        amount = int(txt.replace(",","").strip())
    except:
        send(chat_id, "❌ Invalid amount")
        return
    
    u = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send(chat_id, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
        return
    
    if amount > u.get("balance", 0):
        send(chat_id, f"❌ Insufficient balance")
        return
    
    # Process withdrawal
    new_balance = u["balance"] - amount
    new_withdrawn = u.get("total_withdrawn", 0) + amount
    update_user(user_id, balance=new_balance, total_withdrawn=new_withdrawn)
    db["stats"]["total_withdrawn"] = db["stats"].get("total_withdrawn", 0) + amount
    save()
    
    # Post to channel
    channel_msg = (
        f"💰 *New Withdrawal*\n\n"
        f"User: {u.get('first_name', 'Unknown')} (@{u.get('username', 'None')})\n"
        f"ID: `{user_id}`\n"
        f"Referrals: {u.get('referrals_count', 0)}\n"
        f"Amount: {format_refi(amount)}\n"
        f"Wallet: `{u['wallet']}`"
    )
    post_to_channel(channel_msg)
    
    send(chat_id, f"✅ *Request submitted!*\n\nAmount: {format_refi(amount)}", main_kb(u))

# ==================== MAIN LOOP ====================
print("🚀 Starting bot...")
offset = 0
error_count = 0
max_errors = 5
last_update_time = time.time()

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message", "callback_query"]
        }, timeout=35)
        data = r.json()
        error_count = 0
        
        if data.get("ok"):
            for upd in data.get("result", []):
                last_update_time = time.time()
                
                if "message" in upd:
                    msg = upd["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    if text.startswith("/start"):
                        handle_start(msg)
                    else:
                        if states.get(user_id) == "waiting_wallet":
                            handle_wallet_input(text, user_id, chat_id)
                        elif states.get(user_id) == "waiting_amount":
                            handle_amount_input(text, user_id, chat_id)
                            states.pop(user_id, None)
                        elif states.get(user_id) == "admin_login":
                            handle_admin_login_input(text, user_id, chat_id)
                        elif states.get(user_id) == "admin_broadcast":
                            handle_admin_broadcast_input(text, user_id, chat_id)
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
                    elif data == "stats":
                        handle_stats(cb, user_id, chat_id, msg_id)
                    elif data == "wd":
                        handle_withdraw(cb, user_id, chat_id, msg_id)
                    elif data == "back":
                        handle_back(cb, user_id, chat_id, msg_id)
                    elif data == "admin":
                        handle_admin(cb, user_id, chat_id, msg_id)
                    elif data == "admin_stats":
                        handle_admin_stats(cb, chat_id, msg_id)
                    elif data == "admin_broadcast":
                        handle_admin_broadcast(cb, chat_id, msg_id)
                    elif data == "admin_logout":
                        handle_admin_logout(cb, user_id, chat_id, msg_id)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        error_count += 1
        print(f"❌ Error: {e}")
        if error_count >= max_errors:
            print("🔄 Too many errors, resetting connection...")
            try:
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                error_count = 0
                print("✅ Connection reset")
            except:
                pass
        time.sleep(5)

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
BOT_TOKEN = "7823073143:AAEpY2NpDzs14u3V5RebgW-THiaHjeJRKpQ"
BOT_USERNAME = "RealnetworkPaybot"
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
MAX_PENDING_WITHDRAWALS = 3

# Required channels
REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== DATABASE ====================
db = {"users": {}, "withdrawals": {}, "admin_sessions": {}, "stats": {"total_users": 0, "total_withdrawn": 0, "start_time": time.time()}}

try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
        print(f"✅ Loaded {len(db['users'])} users from JSON")
except:
    print("⚠️ No existing data, starting fresh")

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f, indent=2)

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

def get_pending_withdrawals():
    return [w for w in db["withdrawals"].values() if w.get("status") == "pending"]

def get_user_withdrawals(uid, status=None):
    uid = str(uid)
    withdrawals = [w for w in db["withdrawals"].values() if w.get("user_id") == uid]
    if status:
        withdrawals = [w for w in withdrawals if w.get("status") == status]
    return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)

def create_withdrawal(uid, amount, wallet):
    rid = f"W{int(time.time())}{uid}{random.randint(1000,9999)}"
    db["withdrawals"][rid] = {
        "id": rid,
        "user_id": str(uid),
        "amount": amount,
        "wallet": wallet,
        "status": "pending",
        "created_at": time.time()
    }
    save()
    return rid

def process_withdrawal(rid, admin_id, status):
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
    save()
    return True

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
        "total_earned": sum(u.get("total_earned", 0) for u in users),
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "pending_withdrawals": len(get_pending_withdrawals()),
        "total_referrals": sum(u.get("referrals_count", 0) for u in users),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

def is_admin_logged_in(admin_id):
    return db["admin_sessions"].get(str(admin_id), 0) > time.time()

def admin_login(admin_id):
    db["admin_sessions"][str(admin_id)] = time.time() + 3600
    save()

def admin_logout(admin_id):
    db["admin_sessions"].pop(str(admin_id), None)
    save()

# ==================== KEEP ALIVE SYSTEM ====================
def keep_alive():
    while True:
        try:
            requests.get(f"http://localhost:{PORT}", timeout=5)
            print("💓 Keep alive ping sent")
        except:
            pass
        time.sleep(300)

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    # الصف الأول: الرصيد والإحالة
    row1 = [
        {"text": "💰 Balance", "callback_data": "bal"},
        {"text": "🔗 Referral", "callback_data": "ref"}
    ]
    
    # الصف الثاني: الإحصائيات والسحب
    row2 = [
        {"text": "📊 Statistics", "callback_data": "stats"},
        {"text": "💸 Withdraw", "callback_data": "wd"}
    ]
    
    kb = [row1, row2]
    
    # زر المشرف للمشرفين فقط
    if int(user["id"]) in ADMIN_IDS and is_admin_logged_in(int(user["id"])):
        kb.append([{"text": "👑 Admin Panel", "callback_data": "admin"}])
    
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}

def admin_kb():
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "💰 Pending Withdrawals", "callback_data": "admin_pending"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "👥 Users List", "callback_data": "admin_users"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]}

def cancel_kb():
    return {"inline_keyboard": [[{"text": "❌ Cancel", "callback_data": "back"}]]}

def withdrawal_kb(rid):
    return {"inline_keyboard": [
        [{"text": "✅ Approve", "callback_data": f"approve_{rid}"},
         {"text": "❌ Reject", "callback_data": f"reject_{rid}"}],
        [{"text": "🔙 Back", "callback_data": "admin_pending"}]
    ]}

# ==================== TELEGRAM ====================
def send(chat_id, text, kb=None):
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if kb:
            payload["reply_markup"] = kb
            
        requests.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        print(f"📤 Sent to {chat_id}")
    except Exception as e:
        print(f"❌ Send error: {e}")

def edit(chat_id, msg_id, text, kb=None):
    try:
        payload = {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if kb:
            payload["reply_markup"] = kb
            
        requests.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        print(f"✏️ Edited message {msg_id}")
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

def post_to_channel(text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={"chat_id": PAYMENT_CHANNEL, "text": text, "parse_mode": "Markdown"}, timeout=10)
        print(f"📢 Posted to channel")
    except:
        pass

def broadcast_to_all(message):
    sent = 0
    failed = 0
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
print(f"🌐 Web server on port {PORT}")

# بدء نظام keep alive
threading.Thread(target=keep_alive, daemon=True).start()
print("💓 Keep alive started")

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
    
    # الحصول على بيانات المستخدم
    u = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    # معالجة الإحالة (تسجل فوراً)
    if ref_param and ref_param.isdigit():
        referrer_id = int(ref_param)
        print(f"🔍 Referral ID: {referrer_id}")
        
        if referrer_id != user_id and not u.get("referred_by"):
            print(f"✅ User {user_id} referred by {referrer_id}")
            update_user(user_id, referred_by=referrer_id)
            
            # تحديث عدد النقرات للمُحيل
            referrer = get_user(referrer_id)
            referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
            update_user(referrer_id, referral_clicks=referrer["referral_clicks"])
            
            # إشعار المُحيل
            send(referrer_id, f"👋 *Someone clicked your referral link!*\n\nThey haven't verified yet. Once they verify, you'll get {format_refi(REFERRAL_BONUS)}!")
    
    # إذا كان المستخدم محققاً مسبقاً
    if u.get("verified"):
        welcome = f"🎯 *Welcome back!*\n💰 Balance: {format_refi(u['balance'])}"
        send(chat_id, welcome, main_kb(u))
        return
    
    # التحقق من القنوات
    all_joined = True
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_member(ch["username"], user_id)
        print(f"Channel {ch['name']}: {status}")
        if status not in ["member", "administrator", "creator"]:
            all_joined = False
            not_joined.append(ch["name"])
    
    # إذا كان المستحق محققاً بالفعل (من القنوات)
    if all_joined:
        # ✅ إضافة مكافأة الترحيب
        old_balance = u["balance"]
        new_balance = old_balance + WELCOME_BONUS
        old_earned = u["total_earned"]
        new_earned = old_earned + WELCOME_BONUS
        
        update_user(user_id, verified=True, balance=new_balance, total_earned=new_earned)
        print(f"✅ Welcome bonus added: {WELCOME_BONUS}")
        print(f"Balance: {old_balance} -> {new_balance}")
        
        # ✅ معالجة الإحالة (المُحيل يحصل على مكافأته)
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
                send(referred_by, 
                     f"🎉 *Congratulations!*\n\n"
                     f"Your friend {u.get('first_name', 'Someone')} just verified!\n"
                     f"✨ You earned {format_refi(REFERRAL_BONUS)}!\n"
                     f"💰 New balance: {format_refi(ref_new_balance)}")
        
        # رسالة النجاح مع الأزرار
        success = f"✅ *Verification Successful!*\n\n✨ Added {format_refi(WELCOME_BONUS)}\n💰 Current balance: {format_refi(new_balance)}"
        send(chat_id, success, main_kb(u))
    else:
        # رسالة المطالبة بالانضمام للقنوات
        channels_list = "\n".join([f"• {ch}" for ch in not_joined])
        msg = f"📢 *Please join these channels first:*\n{channels_list}\n\n👇 After joining, click VERIFY"
        send(chat_id, msg, channels_kb())

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
    
    if u["verified"]:
        edit(chat_id, msg_id, f"✅ You're already verified!", main_kb(u))
        return
    
    # ✅ إضافة مكافأة الترحيب
    old_balance = u["balance"]
    new_balance = old_balance + WELCOME_BONUS
    old_earned = u["total_earned"]
    new_earned = old_earned + WELCOME_BONUS
    
    update_user(user_id, 
                verified=True, 
                balance=new_balance, 
                total_earned=new_earned)
    
    print(f"✅ Welcome bonus added: {WELCOME_BONUS}")
    print(f"Balance: {old_balance} -> {new_balance}")
    
    # ✅ معالجة الإحالة (المُحيل يحصل على مكافأته)
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
            send(referred_by, 
                 f"🎉 *Congratulations!*\n\n"
                 f"Your friend {u.get('first_name', 'Someone')} just verified!\n"
                 f"✨ You earned {format_refi(REFERRAL_BONUS)}!\n"
                 f"💰 New balance: {format_refi(ref_new_balance)}")
    
    # رسالة النجاح مع الأزرار
    success = f"✅ *Verification Successful!*\n\n✨ Added {format_refi(WELCOME_BONUS)}\n💰 Current balance: {format_refi(new_balance)}"
    edit(chat_id, msg_id, success, main_kb(u))

def handle_balance(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• Current: {format_refi(u['balance'])}\n"
        f"• Total earned: {format_refi(u['total_earned'])}\n"
        f"• Total withdrawn: {format_refi(u['total_withdrawn'])}\n"
        f"• Referrals: {u['referrals_count']}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_referral(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"
    earned = u['referrals_count'] * REFERRAL_BONUS
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"• Link clicks: {u['referral_clicks']}\n"
        f"• Successful referrals: {u['referrals_count']}\n"
        f"• Earnings from referrals: {format_refi(earned)}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_stats(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    joined = datetime.fromtimestamp(u["joined_at"]).strftime('%Y-%m-%d')
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n"
        f"• Balance: {format_refi(u['balance'])}\n"
        f"• Total earned: {format_refi(u['total_earned'])}\n"
        f"• Referrals: {u['referrals_count']}\n"
        f"• Link clicks: {u['referral_clicks']}\n"
        f"• Verified: {'✅' if u['verified'] else '❌'}"
    )
    edit(chat_id, msg_id, text, back_kb())

def handle_withdraw(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    
    if not u["verified"]:
        edit(chat_id, msg_id, "❌ Please verify first!", back_kb())
        return
    
    if not u["wallet"]:
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
    
    balance = u["balance"]
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
    
    # التحقق من عدد طلبات السحب المعلقة
    pending = get_user_withdrawals(user_id, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        edit(chat_id, msg_id, f"⚠️ You have {len(pending)} pending withdrawals. Max allowed is {MAX_PENDING_WITHDRAWALS}.", back_kb())
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
    text = f"🎯 *Main Menu*\n\n💰 Balance: {format_refi(u['balance'])}"
    edit(chat_id, msg_id, text, main_kb(u))
    if user_id in states:
        states.pop(user_id, None)

# ==================== ADMIN HANDLERS ====================
def handle_admin(cb, user_id, chat_id, msg_id):
    if user_id not in ADMIN_IDS:
        answer(cb["id"])
        return
    
    if not is_admin_logged_in(user_id):
        edit(chat_id, msg_id, "🔐 *Admin Login*\n\nEnter password:", back_kb())
        states[user_id] = "admin_login"
        return
    
    stats = get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    admin_msg = (
        f"👑 *Admin Panel*\n\n"
        f"📊 *Statistics*\n"
        f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
        f"• Balance: {format_refi(stats['total_balance'])}\n"
        f"• Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
        f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
        f"• Total referrals: {stats['total_referrals']}\n"
        f"• Uptime: {hours}h {minutes}m"
    )
    edit(chat_id, msg_id, admin_msg, admin_kb())

def handle_admin_login_input(txt, user_id, chat_id):
    if txt == ADMIN_PASSWORD:
        admin_login(user_id)
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        admin_msg = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {format_refi(stats['total_balance'])}\n"
            f"• Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
            f"• Pending: {stats['pending_withdrawals']}\n"
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
        f"👥 *Users*\n"
        f"• Total: {stats['total_users']}\n"
        f"• Verified: {stats['verified']}\n\n"
        f"💰 *Balances*\n"
        f"• Total balance: {format_refi(stats['total_balance'])}\n"
        f"• Total earned: {format_refi(stats['total_earned'])}\n"
        f"• Total withdrawn: {format_refi(stats['total_withdrawn'])}\n\n"
        f"⏳ *Pending Withdrawals: {stats['pending_withdrawals']}*\n"
        f"👥 *Total Referrals: {stats['total_referrals']}*\n\n"
        f"⏱️ *Uptime: {hours}h {minutes}m*"
    )
    edit(chat_id, msg_id, stats_msg, admin_kb())

def handle_admin_pending(cb, chat_id, msg_id):
    pending = get_pending_withdrawals()
    
    if not pending:
        edit(chat_id, msg_id, "✅ No pending withdrawals", admin_kb())
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    kb = {"inline_keyboard": []}
    
    for w in pending[:5]:
        user = get_user(int(w["user_id"]))
        name = user.get("first_name", "Unknown")
        username = f"@{user.get('username', '')}" if user.get('username') else ""
        text += f"🆔 `{w['id'][:8]}`\n👤 {name} {username}\n💰 {format_refi(w['amount'])}\n📅 {datetime.fromtimestamp(w['created_at']).strftime('%Y-%m-%d %H:%M')}\n\n"
        kb["inline_keyboard"].append([{"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}])
    
    if len(pending) > 5:
        text += f"*... and {len(pending) - 5} more*\n\n"
    
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin"}])
    edit(chat_id, msg_id, text, kb)

def handle_process(cb, chat_id, msg_id, rid):
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
        f"📅 Created: {datetime.fromtimestamp(w['created_at']).strftime('%Y-%m-%d %H:%M')}"
    )
    edit(chat_id, msg_id, text, withdrawal_kb(rid))

def handle_approve(cb, admin_id, chat_id, msg_id, rid):
    if process_withdrawal(rid, admin_id, "approved"):
        w = db["withdrawals"].get(rid)
        if w:
            send(int(w["user_id"]), f"✅ *Withdrawal Approved!*\n\nAmount: {format_refi(w['amount'])}")
    handle_admin_pending(cb, chat_id, msg_id)

def handle_reject(cb, admin_id, chat_id, msg_id, rid):
    if process_withdrawal(rid, admin_id, "rejected"):
        w = db["withdrawals"].get(rid)
        if w:
            send(int(w["user_id"]), f"❌ *Withdrawal Rejected*\n\nAmount returned: {format_refi(w['amount'])}")
    handle_admin_pending(cb, chat_id, msg_id)

def handle_admin_broadcast(cb, chat_id, msg_id):
    edit(chat_id, msg_id, "📢 *Broadcast*\n\nSend message to all users:", back_kb())
    states[cb["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(txt, user_id, chat_id):
    send(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    sent, failed = broadcast_to_all(txt)
    send(chat_id, f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}", admin_kb())
    states.pop(user_id, None)

def handle_admin_users(cb, chat_id, msg_id):
    users = sorted(db["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    text = "👥 *Recent Users*\n\n"
    for u in users:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime('%Y-%m-%d')
        balance = format_refi(u.get("balance", 0))
        text += f"{verified} {name} {username}\n📅 {joined} | 💰 {balance}\n\n"
    text += f"\nTotal users: {len(db['users'])}"
    edit(chat_id, msg_id, text, admin_kb())

def handle_admin_logout(cb, user_id, chat_id, msg_id):
    admin_logout(user_id)
    u = get_user(user_id)
    send(chat_id, f"🔒 Logged out\n\n💰 Balance: {format_refi(u['balance'])}", main_kb(u))

# ==================== INPUT HANDLERS ====================
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
        amount = int(txt.replace(",", "").strip())
    except:
        send(chat_id, "❌ Invalid amount")
        return
    
    u = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send(chat_id, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
        return
    
    if amount > u["balance"]:
        send(chat_id, f"❌ Insufficient balance")
        return
    
    # إنشاء طلب سحب
    rid = create_withdrawal(user_id, amount, u["wallet"])
    
    # خصم الرصيد
    new_balance = u["balance"] - amount
    new_withdrawn = u["total_withdrawn"] + amount
    update_user(user_id, balance=new_balance, total_withdrawn=new_withdrawn)
    db["stats"]["total_withdrawn"] += amount
    save()
    
    # نشر في قناة المدفوعات
    channel_msg = (
        f"💰 *New Withdrawal Request*\n\n"
        f"👤 User: {u.get('first_name', 'Unknown')} (@{u.get('username', 'None')})\n"
        f"🆔 ID: `{user_id}`\n"
        f"📊 Referrals: {u['referrals_count']}\n"
        f"💵 Amount: {format_refi(amount)}\n"
        f"📮 Wallet: `{u['wallet']}`\n"
        f"🆔 Request ID: `{rid}`"
    )
    post_to_channel(channel_msg)
    
    send(chat_id, f"✅ *Withdrawal Request Submitted!*\n\nRequest ID: `{rid[:8]}...`\nAmount: {format_refi(amount)}", main_kb(u))

# ==================== MAIN LOOP ====================
print("🚀 Starting bot...")
offset = 0
error_count = 0
max_errors = 5

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
                    elif data == "admin_pending":
                        handle_admin_pending(cb, chat_id, msg_id)
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

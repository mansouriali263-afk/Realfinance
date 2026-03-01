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
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()

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

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    # Row 1: Balance & Referral
    row1 = [
        {"text": "💰 Balance", "callback_data": "bal"},
        {"text": "🔗 Referral", "callback_data": "ref"}
    ]
    
    # Row 2: Stats & Withdraw
    row2 = [
        {"text": "📊 Statistics", "callback_data": "stats"},
        {"text": "💸 Withdraw", "callback_data": "wd"}
    ]
    
    kb = [row1, row2]
    
    # Admin button for admins
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
    
    print(f"▶️ Start: {user_id}")
    
    # Check for referral using User ID
    args = text.split()
    if len(args) > 1:
        try:
            referrer_id = int(args[1])
            print(f"🔍 Referrer ID from start param: {referrer_id}")
            
            # Don't allow self-referral
            if referrer_id != user_id:
                referrer = get_user(referrer_id)
                u = get_user(user_id)
                
                # Only set referred_by if not already set
                if not u.get("referred_by"):
                    update_user(user_id, referred_by=referrer_id)
                    referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
                    update_user(referrer_id, referral_clicks=referrer["referral_clicks"])
                    print(f"✅ User {user_id} referred by {referrer_id}")
        except ValueError:
            print(f"⚠️ Invalid referral ID: {args[1]}")
    
    u = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    if u.get("verified"):
        welcome_back = (
            f"🎯 *Welcome back, {u.get('first_name', 'Friend')}!*\n\n"
            f"💰 Your balance: {format_refi(u.get('balance', 0))}\n"
            f"👥 Total referrals: {u.get('referrals_count', 0)}"
        )
        send(chat_id, welcome_back, main_kb(u))
        return
    
    # Welcome message for new users
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    welcome_msg = (
        f"🎉 *Welcome to {BOT_USERNAME}!*\n\n"
        f"💰 Welcome Bonus: {format_refi(WELCOME_BONUS)}\n"
        f"👥 Referral Bonus: {format_refi(REFERRAL_BONUS)} per friend\n\n"
        f"📢 To start, you must join these channels first:\n{channels_text}\n\n"
        f"👇 After joining, click the VERIFY button"
    )
    send(chat_id, welcome_msg, channels_kb())

def handle_verify(cb, user_id, chat_id, msg_id):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_member(ch["username"], user_id)
        print(f"🔍 Channel {ch['name']} status: {status}")
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        error_text = "❌ *You haven't joined these channels:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit(chat_id, msg_id, error_text, channels_kb())
        return
    
    u = get_user(user_id)
    
    if u.get("verified"):
        edit(chat_id, msg_id, f"✅ You're already verified!\n{format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    # Add welcome bonus
    new_balance = u.get("balance", 0) + WELCOME_BONUS
    update_user(
        user_id, 
        verified=True, 
        balance=new_balance, 
        total_earned=u.get("total_earned", 0) + WELCOME_BONUS
    )
    
    # Process referral
    referred_by = u.get("referred_by")
    if referred_by:
        referrer = get_user(int(referred_by))
        if referrer:
            referrer["balance"] = referrer.get("balance", 0) + REFERRAL_BONUS
            referrer["total_earned"] = referrer.get("total_earned", 0) + REFERRAL_BONUS
            referrer["referrals_count"] = referrer.get("referrals_count", 0) + 1
            update_user(
                int(referred_by), 
                balance=referrer["balance"], 
                total_earned=referrer["total_earned"], 
                referrals_count=referrer["referrals_count"]
            )
            send(int(referred_by), 
                 f"🎉 *Congratulations!*\nYour friend {u.get('first_name', 'Someone')} joined using your link!\n✨ You earned {format_refi(REFERRAL_BONUS)}")
    
    success_msg = (
        f"✅ *Verification Successful!*\n\n"
        f"✨ Added {format_refi(WELCOME_BONUS)} to your balance\n"
        f"💰 Current balance: {format_refi(new_balance)}\n\n"
        f"👥 Share your referral link and earn {format_refi(REFERRAL_BONUS)} per friend!"
    )
    edit(chat_id, msg_id, success_msg, main_kb(u))
    print(f"✅ User {user_id} verified and received {WELCOME_BONUS} REFi bonus")

def handle_balance(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    msg = (
        f"💰 *Your Balance*\n\n"
        f"• Current: {format_refi(u.get('balance', 0))}\n"
        f"• Total earned: {format_refi(u.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(u.get('total_withdrawn', 0))}\n"
        f"• Referrals: {u.get('referrals_count', 0)}"
    )
    edit(chat_id, msg_id, msg, back_kb())

def handle_referral(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    link = f"https://t.me/{BOT_USERNAME}?start={user_id}"  # Using user_id as referral code
    earned = u.get('referrals_count', 0) * REFERRAL_BONUS
    
    msg = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"• You earn: {format_refi(REFERRAL_BONUS)} per friend\n"
        f"• Link clicks: {u.get('referral_clicks', 0)}\n"
        f"• Earnings from referrals: {format_refi(earned)}"
    )
    edit(chat_id, msg_id, msg, back_kb())

def handle_stats(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime('%Y-%m-%d')
    
    msg = (
        f"📊 *Your Statistics*\n\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n"
        f"• Balance: {format_refi(u.get('balance', 0))}\n"
        f"• Total earned: {format_refi(u.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(u.get('total_withdrawn', 0))}\n"
        f"• Referrals: {u.get('referrals_count', 0)}\n"
        f"• Verified: {'✅' if u.get('verified') else '❌'}\n"
        f"• Wallet: {short_wallet(u.get('wallet', ''))}"
    )
    edit(chat_id, msg_id, msg, back_kb())

def handle_withdraw(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    
    print(f"🔍 Withdraw check - Verified status: {u.get('verified')}")
    print(f"🔍 User balance: {u.get('balance', 0)}")
    print(f"🔍 User wallet: {u.get('wallet')}")
    
    # Check if user has wallet
    if not u.get("wallet"):
        wallet_msg = (
            f"💸 *Withdrawal Setup*\n\n"
            f"You need to set up your wallet address first.\n\n"
            f"📝 *Please send your Ethereum wallet address:*\n"
            f"• Must start with `0x`\n"
            f"• Must be 42 characters long\n\n"
            f"Example:\n"
            f"`0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
        )
        edit(chat_id, msg_id, wallet_msg, cancel_kb())
        states[user_id] = "waiting_wallet"
        return
    
    # Check balance
    balance = u.get("balance", 0)
    
    if balance < MIN_WITHDRAW:
        needed = MIN_WITHDRAW - balance
        warning_msg = (
            f"⚠️ *Insufficient Balance*\n\n"
            f"Minimum withdrawal: {format_refi(MIN_WITHDRAW)}\n"
            f"Your balance: {format_refi(balance)}\n\n"
            f"You need {format_refi(needed)} more to withdraw.\n\n"
            f"💡 Invite more friends to earn more REFi!"
        )
        edit(chat_id, msg_id, warning_msg, back_kb())
        return
    
    # Ask for amount
    amount_msg = (
        f"💸 *Withdrawal Request*\n\n"
        f"Your balance: {format_refi(balance)}\n"
        f"Minimum withdrawal: {format_refi(MIN_WITHDRAW)}\n"
        f"Your wallet: `{short_wallet(u['wallet'])}`\n\n"
        f"📝 *Please enter the amount you want to withdraw:*"
    )
    edit(chat_id, msg_id, amount_msg, cancel_kb())
    states[user_id] = "waiting_amount"

def handle_back(cb, user_id, chat_id, msg_id):
    u = get_user(user_id)
    msg = f"🎯 *Main Menu*\n\n💰 Your balance: {format_refi(u.get('balance', 0))}"
    edit(chat_id, msg_id, msg, main_kb(u))
    # Clear any pending state
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
            f"• Total users: {stats['total_users']}\n"
            f"• Verified users: {stats['verified']}\n"
            f"• Total balance: {format_refi(stats['total_balance'])}\n"
            f"• Total withdrawn: {format_refi(stats['total_withdrawn'])}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        edit(chat_id, msg_id, admin_msg, admin_kb())
    else:
        edit(chat_id, msg_id, "🔐 *Admin Login*\n\nPlease enter the admin password:", back_kb())
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
            f"• Total users: {stats['total_users']}\n"
            f"• Verified users: {stats['verified']}\n"
            f"• Total balance: {format_refi(stats['total_balance'])}\n"
            f"• Total withdrawn: {format_refi(stats['total_withdrawn'])}\n"
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
        f"• Total withdrawn: {format_refi(stats['total_withdrawn'])}\n\n"
        f"⏱️ *Uptime: {hours}h {minutes}m*"
    )
    edit(chat_id, msg_id, stats_msg, admin_kb())

def handle_admin_broadcast(cb, chat_id, msg_id):
    edit(chat_id, msg_id, "📢 *Broadcast Message*\n\nSend the message you want to broadcast to all users:", back_kb())
    states[cb["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(txt, user_id, chat_id):
    send(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    sent, failed = broadcast_to_all(txt)
    send(chat_id, f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}", admin_kb())
    states.pop(user_id, None)

def handle_admin_logout(cb, user_id, chat_id, msg_id):
    states.pop(f"admin_logged_{user_id}", None)
    u = get_user(user_id)
    send(chat_id, f"🔒 Logged out\n\n💰 Your balance: {format_refi(u.get('balance',0))}", main_kb(u))

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(txt, user_id, chat_id):
    if is_valid_wallet(txt):
        update_user(user_id, wallet=txt)
        u = get_user(user_id)
        # After saving wallet, go to amount input
        amount_msg = (
            f"✅ *Wallet saved successfully!*\n\n"
            f"Your wallet: {short_wallet(txt)}\n\n"
            f"💸 *Now, enter the amount you want to withdraw:*\n"
            f"Minimum: {format_refi(MIN_WITHDRAW)}"
        )
        send(chat_id, amount_msg, cancel_kb())
        states[user_id] = "waiting_amount"
        print(f"👛 User {user_id} saved wallet: {txt}")
    else:
        send(chat_id, "❌ *Invalid wallet address!*\n\nPlease send a valid Ethereum address starting with `0x` and 42 characters long.")

def handle_amount_input(txt, user_id, chat_id):
    try:
        amount = int(txt.replace(",","").strip())
    except:
        send(chat_id, "❌ *Invalid amount*\n\nPlease enter a valid number.")
        return
    
    u = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send(chat_id, f"❌ *Amount too low*\n\nMinimum withdrawal is {format_refi(MIN_WITHDRAW)}.")
        return
    
    if amount > u.get("balance", 0):
        send(chat_id, f"❌ *Insufficient balance*\n\nYour current balance: {format_refi(u.get('balance', 0))}")
        return
    
    # Process withdrawal
    new_balance = u["balance"] - amount
    new_withdrawn = u.get("total_withdrawn", 0) + amount
    update_user(user_id, balance=new_balance, total_withdrawn=new_withdrawn)
    db["stats"]["total_withdrawn"] = db["stats"].get("total_withdrawn", 0) + amount
    save()
    
    # Post to payment channel
    channel_msg = (
        f"💰 *New Withdrawal Request*\n\n"
        f"👤 *User:* {u.get('first_name', 'Unknown')}\n"
        f"📱 *Username:* @{u.get('username', 'None')}\n"
        f"🆔 *ID:* `{user_id}`\n"
        f"📊 *Referrals:* {u.get('referrals_count', 0)}\n"
        f"💵 *Amount:* {format_refi(amount)}\n"
        f"📮 *Wallet:* `{u['wallet']}`\n"
        f"⏱️ *Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    post_to_channel(channel_msg)
    
    # Confirm to user
    confirm_msg = (
        f"✅ *Withdrawal Request Submitted!*\n\n"
        f"Amount: {format_refi(amount)}\n"
        f"Wallet: {short_wallet(u['wallet'])}\n\n"
        f"⏳ Status: *Pending Review*\n"
        f"You will be notified once processed."
    )
    send(chat_id, confirm_msg, main_kb(u))
    print(f"💰 User {user_id} requested withdrawal of {amount} REFi")

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
        error_count = 0  # Reset error count on success
        
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]
                    chat_id = msg["chat"]["id"]
                    user_id = msg["from"]["id"]
                    text = msg.get("text", "")
                    
                    print(f"📩 Message from {user_id}: {text[:50]}...")
                    
                    if text == "/start":
                        handle_start(msg)
                    else:
                        # Check current state
                        if states.get(user_id) == "waiting_wallet":
                            handle_wallet_input(text, user_id, chat_id)
                            # Don't pop yet - transitions to waiting_amount
                        elif states.get(user_id) == "waiting_amount":
                            handle_amount_input(text, user_id, chat_id)
                            states.pop(user_id, None)
                        elif states.get(user_id) == "admin_login":
                            handle_admin_login_input(text, user_id, chat_id)
                        elif states.get(user_id) == "admin_broadcast":
                            handle_admin_broadcast_input(text, user_id, chat_id)
                        else:
                            send(chat_id, "❌ Unknown command. Use /start to begin.")
                
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
    except requests.exceptions.Timeout:
        print("⚠️ Timeout, retrying...")
        continue
    except Exception as e:
        error_count += 1
        print(f"❌ Error: {e}")
        if error_count >= max_errors:
            print("🔄 Too many errors, resetting connection...")
            try:
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
                error_count = 0
                print("✅ Connection reset")
            except:
                print("❌ Reset failed")
        time.sleep(5)

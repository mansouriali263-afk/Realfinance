#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
============================================================
🤖 REFi BOT - WEB SERVICE VERSION (FREE)
============================================================
Python version: 3.14.3
Token: 8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs

✨ Works on Render FREE Web Service
✅ Includes health check server
============================================================
"""

import os
import threading
import requests
import time
import json
import logging
import random
import string
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== HEALTH CHECK SERVER ====================

class HealthHandler(BaseHTTPRequestHandler):
    """Simple health check server to keep Render happy"""
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"<html><body><h1>REFi Bot is running!</h1></body></html>")
    
    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        # Suppress log messages
        return

def run_health_server():
    """Run health check server in background thread"""
    port = int(os.environ.get('PORT', 10000))
    server = HTTPServer(('0.0.0.0', port), HealthHandler)
    print(f"📡 Health check server running on port {port}")
    server.serve_forever()

# Start health server in background thread
health_thread = threading.Thread(target=run_health_server, daemon=True)
health_thread.start()

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0  # 1M REFi = $2

REQUIRED_CHANNELS = [
    {
        "name": "REFi Distribution",
        "username": "@Realfinance_REFI",
        "link": "https://t.me/Realfinance_REFI"
    },
    {
        "name": "Airdrop Master VIP",
        "username": "@Airdrop_MasterVIP",
        "link": "https://t.me/Airdrop_MasterVIP"
    },
    {
        "name": "Daily Airdrop",
        "username": "@Daily_AirdropX",
        "link": "https://t.me/Daily_AirdropX"
    }
]

# ==================== LOGGING ====================
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
db = {
    "users": {},
    "withdrawals": {},
    "admin_sessions": {},
    "stats": {
        "start_time": time.time()
    }
}

# Load existing data
try:
    with open("bot_data.json", "r") as f:
        data = json.load(f)
        db.update(data)
        logger.info(f"✅ Loaded {len(db['users'])} users")
except FileNotFoundError:
    logger.info("📁 No existing data, starting fresh")
except Exception as e:
    logger.error(f"❌ Load error: {e}")

def save_data():
    """Save database to file"""
    try:
        with open("bot_data.json", "w") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        logger.error(f"❌ Save error: {e}")

def get_user(user_id):
    """Get or create user"""
    user_id = str(user_id)
    if user_id not in db["users"]:
        db["users"][user_id] = {
            "id": user_id,
            "username": "",
            "first_name": "",
            "joined_at": time.time(),
            "last_active": time.time(),
            "balance": 0,
            "total_earned": 0,
            "total_withdrawn": 0,
            "referral_code": generate_code(user_id),
            "referred_by": None,
            "referrals_count": 0,
            "referrals": {},
            "referral_clicks": 0,
            "verified": False,
            "verified_at": None,
            "wallet": None,
            "wallet_set_at": None,
            "is_admin": int(user_id) in ADMIN_IDS,
            "is_banned": False
        }
        save_data()
    return db["users"][user_id]

def update_user(user_id, **kwargs):
    """Update user data"""
    user_id = str(user_id)
    if user_id in db["users"]:
        db["users"][user_id].update(kwargs)
        db["users"][user_id]["last_active"] = time.time()
        save_data()

def generate_code(user_id):
    """Generate unique referral code"""
    chars = string.ascii_uppercase + string.digits
    while True:
        code = ''.join(random.choices(chars, k=8))
        # Check uniqueness
        exists = False
        for u in db["users"].values():
            if u.get("referral_code") == code:
                exists = True
                break
        if not exists:
            return code

def get_user_by_code(code):
    """Find user by referral code"""
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def get_user_by_username(username):
    """Find user by username"""
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
            return u
    return None

def refi_to_usd(refi):
    """Convert REFi to USD"""
    return (refi / 1_000_000) * REFI_PER_MILLION

def format_refi(refi):
    """Format REFi with USD value"""
    return f"{refi:,} {COIN_NAME} (~${refi_to_usd(refi):.2f})"

# ==================== TELEGRAM API ====================

def send_message(chat_id, text, reply_markup=None):
    """Send message via Telegram API"""
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"❌ Send error: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None):
    """Edit message"""
    url = f"{API_URL}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Edit error: {e}")

def answer_callback(callback_id):
    """Answer callback query"""
    url = f"{API_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")

def get_chat_member(chat_id, user_id):
    """Check channel membership"""
    url = f"{API_URL}/getChatMember"
    params = {"chat_id": chat_id, "user_id": user_id}
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("ok"):
            return data.get("result", {}).get("status")
    except Exception as e:
        logger.error(f"❌ ChatMember error: {e}")
    return None

# ==================== KEYBOARDS ====================

def verify_keyboard():
    """Single floating verify button"""
    return {"inline_keyboard": [[
        {"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}
    ]]}

def main_keyboard(user):
    """Bottom navigation bar"""
    keyboard = [
        [
            {"text": "💰 Balance", "callback_data": "balance"},
            {"text": "🔗 Referral", "callback_data": "referral"}
        ],
        [
            {"text": "💸 Withdraw", "callback_data": "withdraw"},
            {"text": "📊 Stats", "callback_data": "stats"}
        ]
    ]
    # Add wallet button if not set
    if not user.get("wallet"):
        keyboard.append([{"text": "👛 Set Wallet", "callback_data": "set_wallet"}])
    # Add admin button if admin
    if user.get("is_admin"):
        keyboard.append([{"text": "👑 Admin Panel", "callback_data": "admin_panel"}])
    return {"inline_keyboard": keyboard}

def back_keyboard():
    """Back button only"""
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

def wallet_keyboard():
    """Wallet options"""
    return {"inline_keyboard": [
        [{"text": "🔙 Back to Menu", "callback_data": "back"}]
    ]}

# ==================== HANDLERS ====================

def handle_start(message):
    """Handle /start command"""
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = str(user["id"])
    text = message.get("text", "")
    
    logger.info(f"▶️ Start from {user_id}")
    
    # Check for referral
    args = text.split()
    if len(args) > 1:
        ref_code = args[1]
        referrer = get_user_by_code(ref_code)
        if referrer and referrer["id"] != user_id:
            user_data = get_user(user_id)
            if not user_data.get("referred_by"):
                update_user(user_id, referred_by=referrer["id"])
                # Update referrer clicks
                referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
                update_user(referrer["id"], referral_clicks=referrer["referral_clicks"])
                logger.info(f"📋 Referral click: {referrer['id']} -> {user_id}")
    
    # Get or create user
    user_data = get_user(user_id)
    update_user(user_id,
               username=user.get("username", ""),
               first_name=user.get("first_name", ""))
    
    # If already verified, show main menu
    if user_data.get("verified"):
        text = (
            f"🎯 *Main Menu*\n\n"
            f"💰 Balance: {format_refi(user_data.get('balance', 0))}\n"
            f"👥 Referrals: {user_data.get('referrals_count', 0)}"
        )
        send_message(chat_id, text, main_keyboard(user_data))
        return
    
    # Show verification screen
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    welcome_text = (
        f"🎉 *Welcome to {COIN_NAME} Bot!*\n\n"
        f"💰 *Welcome Bonus:* {format_refi(WELCOME_BONUS)}\n"
        f"👥 *Referral Bonus:* {format_refi(REFERRAL_BONUS)} per friend\n\n"
        f"📢 *To start, you must join these channels:*\n{channels_text}\n\n"
        f"👇 Click the button below to verify"
    )
    send_message(chat_id, welcome_text, verify_keyboard())

def handle_verify(callback, user_id, chat_id, message_id):
    """Handle verify button"""
    user_id = str(user_id)
    
    # Check channel membership
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], int(user_id))
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        text = "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit_message(chat_id, message_id, text, verify_keyboard())
        return
    
    # Verify user
    user_data = get_user(user_id)
    
    if user_data.get("verified"):
        text = f"✅ *Already verified!*\n\n{format_refi(user_data.get('balance', 0))}"
        edit_message(chat_id, message_id, text, main_keyboard(user_data))
        return
    
    # Add welcome bonus
    new_balance = user_data.get("balance", 0) + WELCOME_BONUS
    update_user(user_id,
               verified=True,
               verified_at=time.time(),
               balance=new_balance,
               total_earned=user_data.get("total_earned", 0) + WELCOME_BONUS)
    
    # Process referral if exists
    referred_by = user_data.get("referred_by")
    if referred_by:
        referrer = get_user(referred_by)
        if referrer:
            # Add referral bonus
            referrer["balance"] = referrer.get("balance", 0) + REFERRAL_BONUS
            referrer["total_earned"] = referrer.get("total_earned", 0) + REFERRAL_BONUS
            referrer["referrals_count"] = referrer.get("referrals_count", 0) + 1
            referrer["referrals"][str(user_id)] = time.time()
            update_user(referred_by,
                       balance=referrer["balance"],
                       total_earned=referrer["total_earned"],
                       referrals_count=referrer["referrals_count"],
                       referrals=referrer["referrals"])
            
            # Notify referrer
            try:
                send_message(
                    int(referred_by),
                    f"🎉 *Friend Joined!*\n\n"
                    f"{user_data.get('first_name', 'Someone')} joined using your link!\n"
                    f"✨ You earned {format_refi(REFERRAL_BONUS)}"
                )
                logger.info(f"✅ Referral bonus added: {referred_by} -> {user_id}")
            except Exception as e:
                logger.error(f"❌ Referral notification error: {e}")
    
    # Success message
    text = (
        f"✅ *Verification Successful!*\n\n"
        f"✨ Added {format_refi(WELCOME_BONUS)} to your balance\n"
        f"💰 Current: {format_refi(new_balance)}\n\n"
        f"👥 Share your link and earn {format_refi(REFERRAL_BONUS)} per friend!\n\n"
        f"👇 Use the buttons below to navigate"
    )
    edit_message(chat_id, message_id, text, main_keyboard(user_data))
    logger.info(f"✅ User {user_id} verified")

def handle_balance(callback, user_id, chat_id, message_id):
    """Show balance"""
    user_data = get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• REFi: {user_data.get('balance', 0):,}\n"
        f"• USD: ${refi_to_usd(user_data.get('balance', 0)):.2f}\n\n"
        f"📊 *Statistics*\n"
        f"• Total earned: {format_refi(user_data.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(user_data.get('total_withdrawn', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_referral(callback, user_id, chat_id, message_id):
    """Show referral link"""
    user_data = get_user(user_id)
    link = f"https://t.me/Realfinancepaybot?start={user_data.get('referral_code', '')}"
    earned = user_data.get('referrals_count', 0) * REFERRAL_BONUS
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"🎁 *Rewards*\n"
        f"• You earn: {format_refi(REFERRAL_BONUS)} per friend\n"
        f"• Friend gets: {format_refi(WELCOME_BONUS)}\n\n"
        f"📊 *Stats*\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
        f"• Successful: {user_data.get('referrals_count', 0)}\n"
        f"• Earned: {format_refi(earned)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_stats(callback, user_id, chat_id, message_id):
    """Show statistics"""
    user_data = get_user(user_id)
    joined = datetime.fromtimestamp(user_data.get("joined_at", 0)).strftime("%Y-%m-%d %H:%M")
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 *User Info*\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n\n"
        f"💰 *Financial*\n"
        f"• Balance: {format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {format_refi(user_data.get('total_earned', 0))}\n"
        f"• Withdrawn: {format_refi(user_data.get('total_withdrawn', 0))}\n\n"
        f"👥 *Referrals*\n"
        f"• Count: {user_data.get('referrals_count', 0)}\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n\n"
        f"✅ *Status*\n"
        f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
        f"• Wallet: {'✅ Set' if user_data.get('wallet') else '❌ Not set'}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_set_wallet(callback, user_id, chat_id, message_id):
    """Start wallet setup"""
    user_data = get_user(user_id)
    
    text = (
        f"👛 *Set Withdrawal Wallet*\n\n"
        f"Current wallet: {user_data.get('wallet', 'Not set')}\n\n"
        f"Please enter your Ethereum wallet address.\n"
        f"It must start with `0x` and be 42 characters long.\n\n"
        f"Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
    )
    edit_message(chat_id, message_id, text, wallet_keyboard())
    
    # Set state
    global user_states
    user_states[user_id] = {"action": "waiting_wallet"}

def handle_wallet_input(message, user_id, chat_id):
    """Process wallet address input"""
    global user_states
    
    wallet = message.get("text", "").strip()
    
    # Validate wallet
    if not wallet.startswith("0x") or len(wallet) != 42:
        send_message(chat_id, 
                    "❌ *Invalid wallet address*\n\n"
                    "Must start with 0x and be 42 characters long.\n"
                    "Please try again or use /start to cancel.")
        return
    
    try:
        int(wallet[2:], 16)  # Check if hex
    except ValueError:
        send_message(chat_id, "❌ Invalid hex characters. Please try again.")
        return
    
    # Save wallet
    update_user(user_id, wallet=wallet, wallet_set_at=time.time())
    
    user_data = get_user(user_id)
    text = (
        f"✅ *Wallet saved successfully!*\n\n"
        f"Wallet: `{wallet[:6]}...{wallet[-4:]}`\n\n"
        f"You can now withdraw your REFi tokens."
    )
    send_message(chat_id, text, main_keyboard(user_data))
    
    user_states.pop(user_id, None)
    logger.info(f"👛 Wallet set for user {user_id}")

def handle_withdraw(callback, user_id, chat_id, message_id):
    """Start withdrawal process"""
    user_data = get_user(user_id)
    
    if not user_data.get("verified"):
        text = "❌ *You must verify first!*\n\nSend /start to begin."
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    if not user_data.get("wallet"):
        text = (
            "⚠️ *You need to set a wallet first!*\n\n"
            "Please use the [👛 Set Wallet] button to add your wallet address."
        )
        edit_message(chat_id, message_id, text, main_keyboard(user_data))
        return
    
    balance = user_data.get("balance", 0)
    if balance < MIN_WITHDRAW:
        text = (
            f"⚠️ *Minimum withdrawal: {format_refi(MIN_WITHDRAW)}*\n"
            f"Your balance: {format_refi(balance)}\n\n"
            f"You need {format_refi(MIN_WITHDRAW - balance)} more to withdraw."
        )
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    text = (
        f"💸 *Withdraw*\n\n"
        f"Balance: {format_refi(balance)}\n"
        f"Minimum: {format_refi(MIN_WITHDRAW)}\n"
        f"Wallet: `{user_data['wallet'][:6]}...{user_data['wallet'][-4:]}`\n\n"
        f"Send the amount you want to withdraw:"
    )
    edit_message(chat_id, message_id, text)
    
    global user_states
    user_states[user_id] = {"action": "waiting_withdraw_amount"}

def handle_withdraw_amount(message, user_id, chat_id):
    """Process withdrawal amount"""
    global user_states
    
    try:
        amount = int(message.get("text", "").replace(",", "").strip())
    except ValueError:
        send_message(chat_id, "❌ Please enter a valid number.")
        return
    
    user_data = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send_message(chat_id, f"❌ Minimum amount is {format_refi(MIN_WITHDRAW)}")
        return
    
    if amount > user_data.get("balance", 0):
        send_message(chat_id, f"❌ Insufficient balance. You have {format_refi(user_data.get('balance', 0))}")
        return
    
    # Create withdrawal request
    request_id = f"W{int(time.time())}{user_id}{random.randint(100,999)}"
    withdrawal = {
        "id": request_id,
        "user_id": user_id,
        "amount": amount,
        "wallet": user_data["wallet"],
        "status": "pending",
        "created_at": time.time()
    }
    db["withdrawals"][request_id] = withdrawal
    save_data()
    
    # Deduct balance
    new_balance = user_data.get("balance", 0) - amount
    update_user(user_id, balance=new_balance)
    
    # Confirm to user
    text = (
        f"✅ *Withdrawal Request Submitted!*\n\n"
        f"📝 Request ID: `{request_id[:8]}...`\n"
        f"💰 Amount: {format_refi(amount)}\n"
        f"📮 Wallet: `{user_data['wallet'][:6]}...{user_data['wallet'][-4:]}`\n\n"
        f"⏳ Status: *Pending Review*\n\n"
        f"You'll be notified when processed."
    )
    send_message(chat_id, text, main_keyboard(user_data))
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            send_message(
                admin_id,
                f"💰 *New Withdrawal Request*\n\n"
                f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                f"ID: `{user_id}`\n"
                f"Amount: {format_refi(amount)}\n"
                f"Wallet: `{user_data['wallet']}`\n\n"
                f"Request ID: `{request_id}`"
            )
        except Exception as e:
            logger.error(f"❌ Admin notification error: {e}")
    
    logger.info(f"💰 Withdrawal created: {request_id} for {amount} REFi")
    user_states.pop(user_id, None)

def handle_back(callback, user_id, chat_id, message_id):
    """Return to main menu"""
    user_data = get_user(user_id)
    text = (
        f"🎯 *Main Menu*\n\n"
        f"💰 Balance: {format_refi(user_data.get('balance', 0))}\n"
        f"👥 Referrals: {user_data.get('referrals_count', 0)}"
    )
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

# ==================== ADMIN HANDLERS ====================

def handle_admin_command(message):
    """Handle /admin command"""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    if user_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Unauthorized")
        return
    
    if user_id in db["admin_sessions"] and db["admin_sessions"][user_id] > time.time():
        show_admin_panel(chat_id, user_id)
        return
    
    send_message(chat_id, "🔐 *Admin Login*\n\nPlease enter password:")
    global user_states
    user_states[str(user_id)] = {"action": "admin_login"}

def handle_admin_login(message, user_id, chat_id):
    """Process admin login"""
    global user_states
    
    password = message.get("text", "").strip()
    
    if password == ADMIN_PASSWORD:
        db["admin_sessions"][user_id] = time.time() + 3600
        save_data()
        send_message(chat_id, "✅ *Login successful!*")
        show_admin_panel(chat_id, user_id)
    else:
        send_message(chat_id, "❌ *Wrong password!*")
    
    user_states.pop(str(user_id), None)

def show_admin_panel(chat_id, user_id):
    """Display admin panel"""
    total_users = len(db["users"])
    verified = sum(1 for u in db["users"].values() if u.get("verified"))
    total_balance = sum(u.get("balance", 0) for u in db["users"].values())
    pending = len([w for w in db["withdrawals"].values() if w.get("status") == "pending"])
    uptime = int(time.time() - db["stats"]["start_time"])
    hours = uptime // 3600
    minutes = (uptime % 3600) // 60
    
    keyboard = {
        "inline_keyboard": [
            [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
            [{"text": "💰 Pending Withdrawals", "callback_data": "admin_withdrawals"}],
            [{"text": "🔍 Search User", "callback_data": "admin_search"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
            [{"text": "👥 Users List", "callback_data": "admin_users"}],
            [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
        ]
    }
    
    text = (
        f"👑 *Admin Panel*\n\n"
        f"📊 *Statistics*\n"
        f"• Users: {total_users} (✅ {verified})\n"
        f"• Balance: {format_refi(total_balance)}\n"
        f"• Pending withdrawals: {pending}\n"
        f"• Uptime: {hours}h {minutes}m"
    )
    
    send_message(chat_id, text, keyboard)

def handle_admin_stats(callback, user_id, chat_id, message_id):
    """Show detailed statistics"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    now = time.time()
    active_today = sum(1 for u in db["users"].values() if u.get("last_active", 0) > now - 86400)
    active_week = sum(1 for u in db["users"].values() if u.get("last_active", 0) > now - 604800)
    
    total_balance = sum(u.get("balance", 0) for u in db["users"].values())
    total_earned = sum(u.get("total_earned", 0) for u in db["users"].values())
    total_withdrawn = db["stats"].get("total_withdrawn", 0)
    
    text = (
        f"📊 *Detailed Statistics*\n\n"
        f"👥 *Users*\n"
        f"• Total: {len(db['users'])}\n"
        f"• Verified: {sum(1 for u in db['users'].values() if u.get('verified'))}\n"
        f"• Active today: {active_today}\n"
        f"• Active week: {active_week}\n\n"
        f"💰 *Financial*\n"
        f"• Total balance: {format_refi(total_balance)}\n"
        f"• Total earned: {format_refi(total_earned)}\n"
        f"• Total withdrawn: {format_refi(total_withdrawn)}\n\n"
        f"📈 *Referrals*\n"
        f"• Total: {sum(u.get('referrals_count', 0) for u in db['users'].values())}"
    )
    edit_message(chat_id, message_id, text)

def handle_admin_withdrawals(callback, user_id, chat_id, message_id):
    """Show pending withdrawals"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    pending = [w for w in db["withdrawals"].values() if w.get("status") == "pending"]
    
    if not pending:
        text = "✅ *No pending withdrawals*"
        edit_message(chat_id, message_id, text)
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    keyboard = []
    
    for w in pending[:5]:
        user = get_user(w["user_id"])
        name = user.get("first_name", "Unknown")
        text += (
            f"🆔 `{w['id'][:8]}...`\n"
            f"👤 {name}\n"
            f"💰 {format_refi(w['amount'])}\n\n"
        )
        keyboard.append([{"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}])
    
    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_back"}])
    edit_message(chat_id, message_id, text, {"inline_keyboard": keyboard})

def handle_process_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Show withdrawal details for processing"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    withdrawal = db["withdrawals"].get(request_id)
    if not withdrawal:
        answer_callback(callback["id"])
        return
    
    user = get_user(withdrawal["user_id"])
    
    text = (
        f"💰 *Withdrawal Details*\n\n"
        f"📝 Request: `{request_id}`\n"
        f"👤 User: {user.get('first_name', 'Unknown')} (@{user.get('username', '')})\n"
        f"🆔 ID: `{withdrawal['user_id']}`\n"
        f"💰 Amount: {format_refi(withdrawal['amount'])}\n"
        f"📮 Wallet: `{withdrawal['wallet']}`\n"
        f"📅 Created: {datetime.fromtimestamp(withdrawal['created_at']).strftime('%Y-%m-%d %H:%M')}"
    )
    
    keyboard = {
        "inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve_{request_id}"},
                {"text": "❌ Reject", "callback_data": f"reject_{request_id}"}
            ],
            [{"text": "🔙 Back", "callback_data": "admin_withdrawals"}]
        ]
    }
    edit_message(chat_id, message_id, text, keyboard)

def handle_approve_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Approve withdrawal"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    withdrawal = db["withdrawals"].get(request_id)
    if not withdrawal or withdrawal["status"] != "pending":
        answer_callback(callback["id"])
        return
    
    # Update status
    withdrawal["status"] = "approved"
    withdrawal["processed_at"] = time.time()
    withdrawal["processed_by"] = user_id
    db["stats"]["total_withdrawn"] = db["stats"].get("total_withdrawn", 0) + withdrawal["amount"]
    save_data()
    
    # Notify user
    try:
        send_message(
            int(withdrawal["user_id"]),
            f"✅ *Withdrawal Approved!*\n\n"
            f"Request ID: `{request_id[:8]}...`\n"
            f"Amount: {format_refi(withdrawal['amount'])}\n"
            f"Your withdrawal has been approved and will be processed shortly."
        )
    except Exception as e:
        logger.error(f"❌ User notification error: {e}")
    
    answer_callback(callback["id"], "✅ Approved")
    handle_admin_withdrawals(callback, user_id, chat_id, message_id)

def handle_reject_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Reject withdrawal and return funds"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    withdrawal = db["withdrawals"].get(request_id)
    if not withdrawal or withdrawal["status"] != "pending":
        answer_callback(callback["id"])
        return
    
    # Return funds to user
    user = get_user(withdrawal["user_id"])
    user["balance"] = user.get("balance", 0) + withdrawal["amount"]
    update_user(withdrawal["user_id"], balance=user["balance"])
    
    # Update status
    withdrawal["status"] = "rejected"
    withdrawal["processed_at"] = time.time()
    withdrawal["processed_by"] = user_id
    save_data()
    
    # Notify user
    try:
        send_message(
            int(withdrawal["user_id"]),
            f"❌ *Withdrawal Rejected*\n\n"
            f"Request ID: `{request_id[:8]}...`\n"
            f"Amount: {format_refi(withdrawal['amount'])}\n\n"
            f"The amount has been returned to your balance."
        )
    except Exception as e:
        logger.error(f"❌ User notification error: {e}")
    
    answer_callback(callback["id"], "❌ Rejected")
    handle_admin_withdrawals(callback, user_id, chat_id, message_id)

def handle_admin_search(callback, user_id, chat_id, message_id):
    """Initiate user search"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    text = "🔍 *Search User*\n\nSend the User ID or @username:"
    edit_message(chat_id, message_id, text)
    
    global user_states
    user_states[str(user_id)] = {"action": "admin_search"}

def handle_admin_search_input(message, user_id, chat_id):
    """Process search input"""
    global user_states
    
    query = message.get("text", "").strip()
    found = None
    
    if query.isdigit():
        found = get_user(query)
    else:
        found = get_user_by_username(query)
    
    if not found:
        send_message(chat_id, f"❌ User not found: {query}")
        user_states.pop(str(user_id), None)
        return
    
    text = (
        f"👤 *User Found*\n\n"
        f"ID: `{found['id']}`\n"
        f"Username: @{found.get('username', 'None')}\n"
        f"Name: {found.get('first_name', 'Unknown')}\n"
        f"Balance: {format_refi(found.get('balance', 0))}\n"
        f"Referrals: {found.get('referrals_count', 0)}\n"
        f"Verified: {'✅' if found.get('verified') else '❌'}\n"
        f"Wallet: {'✅' if found.get('wallet') else '❌'}"
    )
    send_message(chat_id, text)
    user_states.pop(str(user_id), None)

def handle_admin_broadcast(callback, user_id, chat_id, message_id):
    """Initiate broadcast"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    text = f"📢 *Broadcast*\n\nSend the message to broadcast to {len(db['users'])} users:"
    edit_message(chat_id, message_id, text)
    
    global user_states
    user_states[str(user_id)] = {"action": "admin_broadcast"}

def handle_admin_broadcast_input(message, user_id, chat_id):
    """Process broadcast input"""
    global user_states
    
    msg_text = message.get("text", "")
    if not msg_text:
        send_message(chat_id, "❌ Message cannot be empty")
        return
    
    send_message(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    
    sent = 0
    failed = 0
    
    for uid in db["users"].keys():
        try:
            send_message(int(uid), msg_text)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)
        except Exception as e:
            failed += 1
            logger.error(f"❌ Broadcast error to {uid}: {e}")
    
    result = f"✅ Broadcast complete: {sent} sent, {failed} failed"
    send_message(chat_id, result)
    user_states.pop(str(user_id), None)

def handle_admin_users(callback, user_id, chat_id, message_id):
    """Show users list"""
    if user_id not in ADMIN_IDS or user_id not in db["admin_sessions"]:
        return
    
    users_list = sorted(db["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    
    text = "👥 *Recent Users*\n\n"
    for u in users_list:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime("%m-%d")
        text += f"{verified} {name} {username} - {joined}\n"
    
    text += f"\n*Total: {len(db['users'])} users*"
    edit_message(chat_id, message_id, text)

def handle_admin_logout(callback, user_id, chat_id, message_id):
    """Logout from admin panel"""
    if user_id in db["admin_sessions"]:
        del db["admin_sessions"][user_id]
        save_data()
    
    answer_callback(callback["id"], "🔒 Logged out")
    
    user_data = get_user(user_id)
    text = f"🔒 *Logged out*\n\n💰 Balance: {format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

def handle_admin_back(callback, user_id, chat_id, message_id):
    """Back to admin panel"""
    show_admin_panel(chat_id, user_id)

# ==================== MAIN LOOP ====================

offset = 0
user_states = {}

def main():
    """Main polling loop"""
    global offset
    
    print("\n" + "="*60)
    print("🤖 REFi BOT - WEB SERVICE VERSION")
    print("="*60)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Welcome: {format_refi(WELCOME_BONUS)}")
    print(f"👥 Referral: {format_refi(REFERRAL_BONUS)}")
    print(f"💸 Min withdraw: {format_refi(MIN_WITHDRAW)}")
    print(f"👥 Users in DB: {len(db['users'])}")
    print("="*60 + "\n")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*60 + "\n")
    
    while True:
        try:
            url = f"{API_URL}/getUpdates"
            params = {
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"]
            }
            
            response = requests.get(url, params=params, timeout=35)
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    # Process message
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = str(msg["from"]["id"])
                        text = msg.get("text", "")
                        
                        # Check if user is banned
                        user_data = get_user(user_id)
                        if user_data.get("is_banned"):
                            send_message(chat_id, "⛔ You are banned from using this bot.")
                            offset = update["update_id"] + 1
                            continue
                        
                        # Handle commands
                        if text.startswith("/start"):
                            handle_start(msg)
                        elif text.startswith("/admin"):
                            handle_admin_command(msg)
                        elif text.startswith("/"):
                            send_message(chat_id, "❌ Unknown command. Use /start")
                        else:
                            # Handle state-based input
                            state = user_states.get(user_id, {}).get("action")
                            if state == "waiting_wallet":
                                handle_wallet_input(msg, user_id, chat_id)
                            elif state == "waiting_withdraw_amount":
                                handle_withdraw_amount(msg, user_id, chat_id)
                            elif state == "admin_login":
                                handle_admin_login(msg, int(user_id), chat_id)
                            elif state == "admin_search":
                                handle_admin_search_input(msg, int(user_id), chat_id)
                            elif state == "admin_broadcast":
                                handle_admin_broadcast_input(msg, int(user_id), chat_id)
                    
                    # Process callback query
                    elif "callback_query" in update:
                        cb = update["callback_query"]
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
                        elif data == "withdraw":
                            handle_withdraw(cb, user_id, chat_id, msg_id)
                        elif data == "set_wallet":
                            handle_set_wallet(cb, user_id, chat_id, msg_id)
                        elif data == "back":
                            handle_back(cb, user_id, chat_id, msg_id)
                        
                        # Admin callbacks
                        elif data == "admin_panel":
                            show_admin_panel(chat_id, user_id)
                        elif data == "admin_stats":
                            handle_admin_stats(cb, user_id, chat_id, msg_id)
                        elif data == "admin_withdrawals":
                            handle_admin_withdrawals(cb, user_id, chat_id, msg_id)
                        elif data == "admin_search":
                            handle_admin_search(cb, user_id, chat_id, msg_id)
                        elif data == "admin_broadcast":
                            handle_admin_broadcast(cb, user_id, chat_id, msg_id)
                        elif data == "admin_users":
                            handle_admin_users(cb, user_id, chat_id, msg_id)
                        elif data == "admin_logout":
                            handle_admin_logout(cb, user_id, chat_id, msg_id)
                        elif data == "admin_back":
                            handle_admin_back(cb, user_id, chat_id, msg_id)
                        elif data.startswith("process_"):
                            req_id = data[8:]
                            handle_process_withdrawal(cb, user_id, chat_id, msg_id, req_id)
                        elif data.startswith("approve_"):
                            req_id = data[8:]
                            handle_approve_withdrawal(cb, user_id, chat_id, msg_id, req_id)
                        elif data.startswith("reject_"):
                            req_id = data[7:]
                            handle_reject_withdrawal(cb, user_id, chat_id, msg_id, req_id)
                    
                    offset = update["update_id"] + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal error")

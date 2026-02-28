#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - COMPLETE FINAL VERSION                                         ║
║     Telegram Referral & Earn Bot with All Features                               ║
║                                                                                  ║
║     ✨ FEATURES:                                                                  ║
║     • Channel verification (3 channels)                                          ║
║     • Welcome bonus: 1,000,000 REFi (~$2.00)                                     ║
║     • Referral bonus: 1,000,000 REFi (~$2.00) per referral                       ║
║     • Unique referral codes for each user                                        ║
║     • Balance tracking with USD conversion                                       ║
║     • Wallet management system                                                   ║
║     • Withdrawal requests with admin approval                                    ║
║     • Full admin panel with statistics                                           ║
║     • User search functionality                                                  ║
║     • Broadcast messaging to all users                                           ║
║     • Pending withdrawals management (approve/reject)                            ║
║     • Bottom navigation menu                                                     ║
║     • Health check server for Render                                             ║
║                                                                                  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import time
import json
import logging
import random
import string
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== FIX PRINT BUFFERING ====================
# Ensure all prints appear immediately in logs
import functools
print = functools.partial(print, flush=True)

# ==================== REQUESTS ====================
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    os.system("pip install requests==2.31.0")
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry

# ==================== CONFIGURATION ====================
BOT_TOKEN = os.environ.get('BOT_TOKEN', "8720874613:AAE8nFWsJCX-8tAmfxis6UFgVUfPLGLt5pA")
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0  # 1M REFi = $2 USD

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

MAX_PENDING_WITHDRAWALS = 3
SESSION_TIMEOUT = 3600  # 1 hour

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== HTTP SESSION WITH RETRIES ====================
http_session = requests.Session()
retries = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
http_session.mount('https://', HTTPAdapter(max_retries=retries))
http_session.mount('http://', HTTPAdapter(max_retries=retries))

# ==================== DATABASE ====================
db_lock = threading.Lock()
db = {
    "users": {},
    "withdrawals": {},
    "admin_sessions": {},
    "stats": {
        "start_time": time.time(),
        "total_users": 0,
        "total_verified": 0,
        "total_withdrawals": 0,
        "total_withdrawn": 0,
        "total_referrals": 0
    }
}

def load_db():
    """Load database from file"""
    try:
        if os.path.exists("bot_data.json"):
            with open("bot_data.json", "r", encoding="utf-8") as f:
                loaded = json.load(f)
                db.update(loaded)
                logger.info(f"✅ Loaded {len(db['users'])} users, {len(db['withdrawals'])} withdrawals")
    except Exception as e:
        logger.error(f"❌ Load error: {e}")

def save_db():
    """Save database to file"""
    with db_lock:
        try:
            with open("bot_data.json", "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Save error: {e}")

load_db()

# ==================== USER FUNCTIONS ====================
def get_user(user_id):
    """Get or create user"""
    uid = str(user_id)
    with db_lock:
        if uid not in db["users"]:
            chars = string.ascii_uppercase + string.digits
            db["users"][uid] = {
                "id": uid,
                "username": "",
                "first_name": "",
                "last_name": "",
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
    """Update user data"""
    uid = str(user_id)
    with db_lock:
        if uid in db["users"]:
            db["users"][uid].update(kwargs)
            db["users"][uid]["last_active"] = time.time()
            save_db()

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

# ==================== WITHDRAWAL FUNCTIONS ====================
def create_withdrawal(user_id, amount, wallet):
    """Create withdrawal request"""
    rid = f"W{int(time.time())}{user_id}{random.randint(1000,9999)}"
    with db_lock:
        db["withdrawals"][rid] = {
            "id": rid,
            "user_id": str(user_id),
            "amount": amount,
            "wallet": wallet,
            "status": "pending",
            "created_at": time.time(),
            "processed_at": None,
            "processed_by": None,
            "tx_hash": None
        }
        db["stats"]["total_withdrawals"] += 1
        save_db()
    return rid

def get_withdrawal(rid):
    """Get withdrawal by ID"""
    return db["withdrawals"].get(rid)

def get_pending_withdrawals():
    """Get all pending withdrawals"""
    return [w for w in db["withdrawals"].values() if w.get("status") == "pending"]

def get_user_withdrawals(user_id, status=None):
    """Get user withdrawals"""
    uid = str(user_id)
    withdrawals = [w for w in db["withdrawals"].values() if w.get("user_id") == uid]
    if status:
        withdrawals = [w for w in withdrawals if w.get("status") == status]
    return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)

def process_withdrawal(rid, admin_id, status, tx_hash=None):
    """Process withdrawal (approve/reject)"""
    with db_lock:
        w = db["withdrawals"].get(rid)
        if not w or w["status"] != "pending":
            return False
        
        w["status"] = status
        w["processed_at"] = time.time()
        w["processed_by"] = admin_id
        w["tx_hash"] = tx_hash
        
        if status == "approved":
            db["stats"]["total_withdrawn"] += w["amount"]
        elif status == "rejected":
            # Return funds to user
            user = db["users"].get(w["user_id"])
            if user:
                user["balance"] += w["amount"]
        
        save_db()
        return True

# ==================== ADMIN SESSION FUNCTIONS ====================
def admin_login(admin_id):
    """Create admin session"""
    with db_lock:
        db["admin_sessions"][str(admin_id)] = time.time() + SESSION_TIMEOUT
        save_db()
        return True

def admin_logout(admin_id):
    """End admin session"""
    with db_lock:
        db["admin_sessions"].pop(str(admin_id), None)
        save_db()

def is_admin_logged_in(admin_id):
    """Check if admin has valid session"""
    with db_lock:
        session = db["admin_sessions"].get(str(admin_id))
        if not session:
            return False
        if session < time.time():
            db["admin_sessions"].pop(str(admin_id), None)
            save_db()
            return False
        return True

# ==================== STATISTICS ====================
def get_stats():
    """Get bot statistics"""
    users = db["users"].values()
    now = time.time()
    
    active_today = sum(1 for u in users if u.get("last_active", 0) > now - 86400)
    active_week = sum(1 for u in users if u.get("last_active", 0) > now - 604800)
    total_balance = sum(u.get("balance", 0) for u in users)
    total_earned = sum(u.get("total_earned", 0) for u in users)
    total_referrals = sum(u.get("referrals_count", 0) for u in users)
    
    top_referrer = max(users, key=lambda u: u.get("referrals_count", 0)) if users else None
    
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "banned": sum(1 for u in users if u.get("is_banned")),
        "active_today": active_today,
        "active_week": active_week,
        "total_balance": total_balance,
        "total_earned": total_earned,
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "pending_withdrawals": len(get_pending_withdrawals()),
        "total_referrals": total_referrals,
        "top_referrer": f"{top_referrer.get('first_name', '')} (@{top_referrer.get('username', '')}) - {top_referrer.get('referrals_count', 0)}" if top_referrer else "None",
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== UTILITIES ====================
def format_refi(refi):
    """Format REFi with USD value"""
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(wallet, chars=6):
    """Shorten wallet address"""
    if not wallet or len(wallet) < 10:
        return "Not set"
    return f"{wallet[:chars]}...{wallet[-chars:]}"

def is_valid_wallet(wallet):
    """Validate Ethereum wallet address"""
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
    """Get formatted date"""
    dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
    return dt.strftime('%Y-%m-%d %H:%M')

# ==================== KEYBOARDS ====================
def channels_keyboard():
    """Channel verification keyboard"""
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_keyboard(user):
    """Main menu keyboard"""
    kb = [
        [{"text": "💰 Balance", "callback_data": "bal"},
         {"text": "🔗 Referral", "callback_data": "ref"}],
        [{"text": "💸 Withdraw", "callback_data": "wd"},
         {"text": "📊 Stats", "callback_data": "stats"}]
    ]
    if not user.get("wallet"):
        kb.append([{"text": "👛 Set Wallet", "callback_data": "wallet"}])
    if user.get("is_admin"):
        kb.append([{"text": "👑 Admin", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

def back_keyboard():
    """Back button"""
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

def admin_keyboard():
    """Admin panel keyboard"""
    return {"inline_keyboard": [
        [{"text": "📊 Statistics", "callback_data": "astats"}],
        [{"text": "💰 Pending", "callback_data": "apending"}],
        [{"text": "🔍 Search", "callback_data": "asearch"}],
        [{"text": "📢 Broadcast", "callback_data": "abcast"}],
        [{"text": "👥 Users", "callback_data": "ausers"}],
        [{"text": "🔒 Logout", "callback_data": "alogout"}]
    ]}

def withdrawal_actions_keyboard(rid):
    """Withdrawal action buttons"""
    return {"inline_keyboard": [
        [{"text": "✅ Approve", "callback_data": f"app_{rid}"},
         {"text": "❌ Reject", "callback_data": f"rej_{rid}"}],
        [{"text": "🔙 Back", "callback_data": "apending"}]
    ]}

def user_actions_keyboard(user_id, is_banned, is_admin):
    """User management buttons"""
    kb = []
    if is_banned:
        kb.append([{"text": "✅ Unban", "callback_data": f"unban_{user_id}"}])
    else:
        kb.append([{"text": "🔨 Ban", "callback_data": f"ban_{user_id}"}])
    
    if is_admin:
        kb.append([{"text": "👤 Remove Admin", "callback_data": f"rmadmin_{user_id}"}])
    else:
        kb.append([{"text": "👑 Make Admin", "callback_data": f"mkadmin_{user_id}"}])
    
    kb.append([{"text": "🔙 Back", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

# ==================== TELEGRAM API FUNCTIONS ====================
def send_message(chat_id, text, keyboard=None):
    """Send message with error handling"""
    try:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = keyboard
        
        response = http_session.post(f"{API_URL}/sendMessage", json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Send failed: {response.text}")
        return response
    except Exception as e:
        logger.error(f"❌ Send exception: {e}")
        return None

def edit_message(chat_id, message_id, text, keyboard=None):
    """Edit message with error handling"""
    try:
        payload = {
            "chat_id": chat_id,
            "message_id": message_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = keyboard
        
        response = http_session.post(f"{API_URL}/editMessageText", json=payload, timeout=10)
        if response.status_code != 200:
            logger.error(f"❌ Edit failed: {response.text}")
        return response
    except Exception as e:
        logger.error(f"❌ Edit exception: {e}")
        return None

def answer_callback(callback_id):
    """Answer callback query"""
    try:
        http_session.post(f"{API_URL}/answerCallbackQuery", 
                          json={"callback_query_id": callback_id}, timeout=5)
    except Exception as e:
        logger.error(f"❌ Callback error: {e}")

def get_chat_member(chat_id, user_id):
    """Check channel membership"""
    try:
        response = http_session.get(f"{API_URL}/getChatMember", 
                                     params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        data = response.json()
        if data.get("ok"):
            return data.get("result", {}).get("status")
        return None
    except Exception as e:
        logger.error(f"❌ ChatMember error: {e}")
        return None

# ==================== MESSAGE HANDLERS ====================
user_states = {}

def handle_start(message):
    """Handle /start command"""
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = user["id"]
    text = message.get("text", "")
    
    logger.info(f"▶️ Start: {user_id}")
    
    # Check for referral
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
    
    # Get or create user
    user_data = get_user(user_id)
    update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    # Show main menu if verified
    if user_data.get("verified"):
        text = f"🎯 *Main Menu*\n💰 {format_refi(user_data.get('balance', 0))}"
        send_message(chat_id, text, main_keyboard(user_data))
        return
    
    # Show channel verification
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
    """Handle verify button"""
    # Check channels
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], user_id)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        text = "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit_message(chat_id, message_id, text, channels_keyboard())
        return
    
    # Verify user
    user_data = get_user(user_id)
    
    if user_data.get("verified"):
        text = f"✅ Already verified!\n{format_refi(user_data.get('balance', 0))}"
        edit_message(chat_id, message_id, text, main_keyboard(user_data))
        return
    
    # Add welcome bonus
    new_balance = user_data.get("balance", 0) + WELCOME_BONUS
    update_user(user_id,
                verified=True,
                verified_at=time.time(),
                balance=new_balance,
                total_earned=user_data.get("total_earned", 0) + WELCOME_BONUS)
    
    # Process referral
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
    
    text = f"✅ *Verified!*\n✨ Added {format_refi(WELCOME_BONUS)}\n💰 {format_refi(new_balance)}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))
    logger.info(f"✅ User {user_id} verified")

def handle_balance(callback, user_id, chat_id, message_id):
    """Show balance"""
    user_data = get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• {format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {format_refi(user_data.get('total_earned', 0))}\n"
        f"• Total withdrawn: {format_refi(user_data.get('total_withdrawn', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_referral(callback, user_id, chat_id, message_id):
    """Show referral link"""
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
    """Show statistics"""
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

def handle_withdraw(callback, user_id, chat_id, message_id):
    """Start withdrawal process"""
    user_data = get_user(user_id)
    
    if not user_data.get("verified"):
        edit_message(chat_id, message_id, "❌ Verify first!", back_keyboard())
        return
    
    if not user_data.get("wallet"):
        edit_message(chat_id, message_id, "⚠️ Set wallet first!", main_keyboard(user_data))
        return
    
    balance = user_data.get("balance", 0)
    if balance < MIN_WITHDRAW:
        edit_message(chat_id, message_id, 
                    f"⚠️ Min: {format_refi(MIN_WITHDRAW)}\nYour: {format_refi(balance)}", 
                    back_keyboard())
        return
    
    # Check pending withdrawals
    pending = get_user_withdrawals(user_id, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        edit_message(chat_id, message_id,
                    f"⚠️ You have {len(pending)} pending withdrawals\nMax: {MAX_PENDING_WITHDRAWALS}",
                    back_keyboard())
        return
    
    text = (
        f"💸 *Withdraw*\n\n"
        f"Balance: {format_refi(balance)}\n"
        f"Min: {format_refi(MIN_WITHDRAW)}\n"
        f"Wallet: {short_wallet(user_data['wallet'])}\n\n"
        f"Send amount:"
    )
    edit_message(chat_id, message_id, text)
    user_states[user_id] = "withdraw"

def handle_set_wallet(callback, user_id, chat_id, message_id):
    """Start wallet setup"""
    user_data = get_user(user_id)
    current = user_data.get("wallet", "Not set")
    if current != "Not set":
        current = short_wallet(current)
    
    text = (
        f"👛 *Set Wallet*\n\n"
        f"Current: {current}\n\n"
        f"Send ETH address (0x...):"
    )
    edit_message(chat_id, message_id, text)
    user_states[user_id] = "wallet"

def handle_back(callback, user_id, chat_id, message_id):
    """Back to main menu"""
    user_data = get_user(user_id)
    text = f"🎯 *Main Menu*\n💰 {format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

def handle_admin_panel(callback, user_id, chat_id, message_id):
    """Show admin panel"""
    if user_id not in ADMIN_IDS:
        return
    
    if not is_admin_logged_in(user_id):
        text = "🔐 *Please login first*\n\nUse /admin to login"
        edit_message(chat_id, message_id, text, main_keyboard(get_user(user_id)))
        return
    
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
    edit_message(chat_id, message_id, text, admin_keyboard())

# ==================== ADMIN HANDLERS ====================
def handle_admin_login(message):
    """Handle /admin command"""
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
    """Process admin login"""
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
    """Show detailed statistics"""
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
        f"• Balance: {format_refi(stats['total_balance'])}\n"
        f"• Total earned: {format_refi(stats['total_earned'])}\n"
        f"• Withdrawn: {format_refi(stats['total_withdrawn'])}\n"
        f"• Pending: {stats['pending_withdrawals']}\n\n"
        f"📈 *Referrals*\n"
        f"• Total: {stats['total_referrals']}\n"
        f"• Top: {stats['top_referrer']}\n\n"
        f"⏱️ *Uptime: {hours}h {minutes}m*"
    )
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_pending(callback, chat_id, message_id):
    """Show pending withdrawals"""
    pending = get_pending_withdrawals()
    
    if not pending:
        edit_message(chat_id, message_id, "✅ No pending withdrawals", admin_keyboard())
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    keyboard = {"inline_keyboard": []}
    
    for w in pending[:5]:
        user = get_user(int(w["user_id"]))
        name = user.get("first_name", "Unknown")
        text += (
            f"🆔 `{w['id'][:8]}...`\n"
            f"👤 {name}\n"
            f"💰 {format_refi(w['amount'])}\n"
            f"📅 {get_date(w['created_at'])}\n\n"
        )
        keyboard["inline_keyboard"].append([
            {"text": f"Process {w['id'][:8]}", "callback_data": f"proc_{w['id']}"}
        ])
    
    if len(pending) > 5:
        text += f"*... and {len(pending) - 5} more*\n\n"
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin"}])
    edit_message(chat_id, message_id, text, keyboard)

def handle_process_withdrawal(callback, chat_id, message_id, rid):
    """Show withdrawal details for processing"""
    w = get_withdrawal(rid)
    if not w:
        return
    
    user = get_user(int(w["user_id"]))
    
    text = (
        f"💰 *Withdrawal Details*\n\n"
        f"📝 Request: `{rid}`\n"
        f"👤 User: {user.get('first_name', 'Unknown')} (@{user.get('username', '')})\n"
        f"🆔 ID: `{w['user_id']}`\n"
        f"💰 Amount: {format_refi(w['amount'])}\n"
        f"📮 Wallet: `{w['wallet']}`\n"
        f"📅 Created: {get_date(w['created_at'])}"
    )
    edit_message(chat_id, message_id, text, withdrawal_actions_keyboard(rid))

def handle_approve_withdrawal(callback, admin_id, chat_id, message_id, rid):
    """Approve withdrawal"""
    if process_withdrawal(rid, admin_id, "approved"):
        # Notify user
        w = get_withdrawal(rid)
        if w:
            send_message(int(w["user_id"]),
                        f"✅ *Withdrawal Approved!*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_reject_withdrawal(callback, admin_id, chat_id, message_id, rid):
    """Reject withdrawal"""
    if process_withdrawal(rid, admin_id, "rejected"):
        # Notify user
        w = get_withdrawal(rid)
        if w:
            send_message(int(w["user_id"]),
                        f"❌ *Withdrawal Rejected*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_admin_search(callback, chat_id, message_id):
    """Initiate user search"""
    edit_message(chat_id, message_id, "🔍 *Send User ID or @username:*")
    user_states[callback["from"]["id"]] = "admin_search"

def handle_admin_search_input(text, admin_id, chat_id):
    """Process user search"""
    found = None
    if text.isdigit():
        found = get_user(int(text))
    else:
        found = get_user_by_username(text)
    
    if not found:
        send_message(chat_id, f"❌ User not found: {text}")
        return
    
    pending = len(get_user_withdrawals(int(found["id"]), "pending"))
    
    text = (
        f"👤 *User Found*\n\n"
        f"ID: `{found['id']}`\n"
        f"Username: @{found.get('username', 'None')}\n"
        f"Name: {found.get('first_name', 'Unknown')}\n"
        f"Balance: {format_refi(found.get('balance', 0))}\n"
        f"Referrals: {found.get('referrals_count', 0)}\n"
        f"Verified: {'✅' if found.get('verified') else '❌'}\n"
        f"Wallet: {short_wallet(found.get('wallet', ''))}\n"
        f"Pending withdrawals: {pending}"
    )
    send_message(chat_id, text, user_actions_keyboard(int(found["id"]), 
                                                       found.get("is_banned", False), 
                                                       found.get("is_admin", False)))

def handle_admin_broadcast(callback, chat_id, message_id):
    """Initiate broadcast"""
    edit_message(chat_id, message_id, 
                f"📢 *Broadcast*\n\nSend message to {len(db['users'])} users:")
    user_states[callback["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(text, admin_id, chat_id):
    """Process broadcast"""
    send_message(chat_id, f"📢 Broadcasting to {len(db['users'])} users...")
    
    sent = 0
    failed = 0
    
    for uid in db["users"].keys():
        try:
            send_message(int(uid), text)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)
        except:
            failed += 1
    
    send_message(chat_id, f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}")

def handle_admin_users(callback, chat_id, message_id):
    """Show recent users"""
    users_list = sorted(db["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    
    text = "👥 *Recent Users*\n\n"
    for u in users_list:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = get_date(u.get("joined_at", 0)).split()[0]
        text += f"{verified} {name} {username} - {joined}\n"
    
    text += f"\n*Total: {len(db['users'])} users*"
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_logout(callback, admin_id, chat_id, message_id):
    """Logout from admin panel"""
    admin_logout(admin_id)
    user_data = get_user(admin_id)
    text = f"🔒 *Logged out*\n\n💰 Balance: {format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data))

def handle_user_action(callback, admin_id, chat_id, message_id, action, target_id):
    """Handle user management actions"""
    target_user = get_user(target_id)
    
    if action == "ban":
        update_user(target_id, is_banned=True)
        send_message(chat_id, f"✅ User {target_id} banned")
    elif action == "unban":
        update_user(target_id, is_banned=False)
        send_message(chat_id, f"✅ User {target_id} unbanned")
    elif action == "make_admin":
        update_user(target_id, is_admin=True)
        send_message(chat_id, f"✅ User {target_id} is now admin")
    elif action == "remove_admin":
        update_user(target_id, is_admin=False)
        send_message(chat_id, f"✅ User {target_id} is no longer admin")
    
    # Refresh user info
    handle_admin_search_input(str(target_id), admin_id, chat_id)

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(text, user_id, chat_id):
    """Save wallet address"""
    if is_valid_wallet(text):
        update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = get_user(user_id)
        send_message(chat_id, f"✅ *Wallet saved!*\n{short_wallet(text)}", main_keyboard(user_data))
    else:
        send_message(chat_id, "❌ Invalid wallet! Must be 0x + 40 chars")

def handle_withdraw_input(text, user_id, chat_id):
    """Process withdrawal amount"""
    try:
        amount = int(text.replace(',', '').strip())
    except ValueError:
        send_message(chat_id, "❌ Invalid number")
        return
    
    user_data = get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send_message(chat_id, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
        return
    
    if amount > user_data.get("balance", 0):
        send_message(chat_id, f"❌ Insufficient balance")
        return
    
    # Check pending withdrawals
    pending = get_user_withdrawals(user_id, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        send_message(chat_id, f"❌ You have {len(pending)} pending withdrawals")
        return
    
    # Create withdrawal
    rid = create_withdrawal(user_id, amount, user_data["wallet"])
    update_user(user_id, balance=user_data["balance"] - amount)
    
    send_message(chat_id, f"✅ *Withdrawal requested!*\nID: {rid[:8]}...", main_keyboard(user_data))
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        send_message(admin_id,
                    f"💰 *New Withdrawal*\n\n"
                    f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                    f"Amount: {format_refi(amount)}\n"
                    f"Wallet: {user_data['wallet']}\n"
                    f"ID: `{rid}`")

# ==================== WEB SERVER FOR RENDER ====================
class HealthHandler(BaseHTTPRequestHandler):
    """Health check handler for Render"""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>🤖 REFi Bot</title>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: sans-serif; text-align: center; padding: 50px; 
               background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
               color: white; }}
        .status {{ display: inline-block; padding: 10px 20px; 
                  background: rgba(0,255,0,0.2); border-radius: 50px; }}
    </style>
</head>
<body>
    <h1>🤖 REFi Bot</h1>
    <div class="status">🟢 RUNNING</div>
    <p>@{BOT_USERNAME}</p>
    <p>Users: {stats['total_users']} | Verified: {stats['verified']}</p>
    <p><small>Uptime: {hours}h {minutes}m | {get_date()}</small></p>
</body>
</html>"""
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

def run_web_server():
    """Run web server in background"""
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"🌐 Web server on port {PORT}")
    server.serve_forever()

# Start web server
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()
logger.info("🌐 Web server thread started")

# ==================== CLEAR OLD SESSIONS ====================
logger.info("🔄 Clearing old sessions...")
try:
    http_session.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True}, timeout=10)
    http_session.get(f"{API_URL}/getUpdates", params={"offset": -1, "timeout": 0}, timeout=10)
    logger.info("✅ Sessions cleared")
except Exception as e:
    logger.error(f"❌ Error clearing sessions: {e}")

# ==================== MAIN BOT LOOP ====================
def main():
    """Main bot polling loop"""
    logger.info("🚀 Starting bot polling...")
    offset = 0
    
    while True:
        try:
            response = http_session.post(f"{API_URL}/getUpdates", json={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"]
            }, timeout=35)
            
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    # Process messages
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        text = msg.get("text", "")
                        
                        # Check if user is banned
                        user_data = get_user(user_id)
                        if user_data.get("is_banned"):
                            send_message(chat_id, "⛔ You are banned")
                            offset = update["update_id"] + 1
                            continue
                        
                        # Handle commands
                        if text == "/start":
                            handle_start(msg)
                        elif text == "/admin":
                            handle_admin_login(msg)
                        elif text.startswith("/"):
                            send_message(chat_id, "❌ Unknown command")
                        else:
                            # Handle state-based input
                            state = user_states.get(user_id)
                            if state == "wallet":
                                handle_wallet_input(text, user_id, chat_id)
                                user_states.pop(user_id, None)
                            elif state == "withdraw":
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
                    
                    # Process callback queries
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
                        elif data == "bal":
                            handle_balance(cb, user_id, chat_id, msg_id)
                        elif data == "ref":
                            handle_referral(cb, user_id, chat_id, msg_id)
                        elif data == "stats":
                            handle_stats(cb, user_id, chat_id, msg_id)
                        elif data == "wd":
                            handle_withdraw(cb, user_id, chat_id, msg_id)
                        elif data == "wallet":
                            handle_set_wallet(cb, user_id, chat_id, msg_id)
                        elif data == "back":
                            handle_back(cb, user_id, chat_id, msg_id)
                        elif data == "admin":
                            handle_admin_panel(cb, user_id, chat_id, msg_id)
                        
                        # Admin callbacks
                        elif data == "astats":
                            handle_admin_stats(cb, chat_id, msg_id)
                        elif data == "apending":
                            handle_admin_pending(cb, chat_id, msg_id)
                        elif data == "asearch":
                            handle_admin_search(cb, chat_id, msg_id)
                        elif data == "abcast":
                            handle_admin_broadcast(cb, chat_id, msg_id)
                        elif data == "ausers":
                            handle_admin_users(cb, chat_id, msg_id)
                        elif data == "alogout":
                            handle_admin_logout(cb, user_id, chat_id, msg_id)
                        elif data.startswith("proc_"):
                            rid = data[5:]
                            handle_process_withdrawal(cb, chat_id, msg_id, rid)
                        elif data.startswith("app_"):
                            rid = data[4:]
                            handle_approve_withdrawal(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("rej_"):
                            rid = data[4:]
                            handle_reject_withdrawal(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("ban_"):
                            target = int(data[4:])
                            handle_user_action(cb, user_id, chat_id, msg_id, "ban", target)
                        elif data.startswith("unban_"):
                            target = int(data[6:])
                            handle_user_action(cb, user_id, chat_id, msg_id, "unban", target)
                        elif data.startswith("mkadmin_"):
                            target = int(data[8:])
                            handle_user_action(cb, user_id, chat_id, msg_id, "make_admin", target)
                        elif data.startswith("rmadmin_"):
                            target = int(data[8:])
                            handle_user_action(cb, user_id, chat_id, msg_id, "remove_admin", target)
                    
                    offset = update["update_id"] + 1
            
            elif data.get("error_code") == 409:
                logger.warning("⚠️ Conflict detected, resetting...")
                http_session.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                time.sleep(5)
                offset = 0
                    
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

# ==================== START ====================
if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("🤖 REFi BOT - FINAL VERSION v15.0")
        print("="*70)
        print(f"📱 Bot: @{BOT_USERNAME}")
        print(f"👤 Admins: {ADMIN_IDS}")
        print(f"💰 Welcome: {format_refi(WELCOME_BONUS)}")
        print(f"👥 Users: {len(db['users'])}")
        print(f"🌐 Port: {PORT}")
        print("="*70 + "\n")
        
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        logger.exception("❌ Fatal error")
        print(f"\n❌ Fatal error: {e}")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - PREMIUM FINAL EDITION v17.0                                    ║
║     Telegram Referral & Earn Bot with Complete Features                          ║
║                                                                                  ║
║     ✨ ALL FEATURES:                                                              ║
║     • Channel verification system (3 channels)                                   ║
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
║     • User ban/unban system                                                      ║
║     • Admin promotion/removal                                                    ║
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
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Dict, Optional, List, Any, Tuple
from collections import defaultdict

# ==================== FIX PRINT BUFFERING ====================
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
class Config:
    """Centralized configuration management"""
    
    # Bot Core
    BOT_TOKEN = "8720874613:AAFMPJRNrmnte_CzmGxGXFxwbSEi_MsDjt0"
    BOT_USERNAME = "Realfinancepaybot"
    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    PORT = int(os.environ.get('PORT', 10000))
    
    # Admin Settings
    ADMIN_IDS = [1653918641]
    ADMIN_PASSWORD = "Ali97$"
    
    # Tokenomics (1M REFi = $2 USD)
    COIN_NAME = "REFi"
    WELCOME_BONUS = 1_000_000
    REFERRAL_BONUS = 1_000_000
    MIN_WITHDRAW = 5_000_000
    REFI_PER_MILLION = 2.0
    
    # Required Channels
    REQUIRED_CHANNELS = [
        {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
        {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
        {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
    ]
    
    # Limits & Restrictions
    MAX_PENDING_WITHDRAWALS = 3
    SESSION_TIMEOUT = 3600  # 1 hour
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    
    # Database
    DB_FILE = "bot_data.json"

# ==================== LOGGING ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# ==================== HTTP SESSION ====================
http_session = requests.Session()
retries = Retry(total=Config.MAX_RETRIES, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
http_session.mount('https://', HTTPAdapter(max_retries=retries))
http_session.mount('http://', HTTPAdapter(max_retries=retries))

# ==================== DATABASE ====================
class Database:
    """Thread-safe database with auto-save"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {
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
        self.load()
    
    def load(self):
        """Load data from file"""
        try:
            if os.path.exists(Config.DB_FILE):
                with open(Config.DB_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    with self.lock:
                        self.data.update(loaded)
                    logger.info(f"✅ Loaded {len(self.data['users'])} users, {len(self.data['withdrawals'])} withdrawals")
        except Exception as e:
            logger.error(f"❌ Load error: {e}")
    
    def save(self):
        """Save data to file"""
        with self.lock:
            try:
                with open(Config.DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"❌ Save error: {e}")
    
    def get_user(self, user_id: int) -> dict:
        """Get or create user"""
        uid = str(user_id)
        with self.lock:
            if uid not in self.data["users"]:
                chars = string.ascii_uppercase + string.digits
                self.data["users"][uid] = {
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
                    "is_admin": int(uid) in Config.ADMIN_IDS,
                    "is_banned": False,
                    "notes": ""
                }
                self.data["stats"]["total_users"] = len(self.data["users"])
                self.save()
            return self.data["users"][uid]
    
    def update_user(self, user_id: int, **kwargs):
        """Update user data"""
        uid = str(user_id)
        with self.lock:
            if uid in self.data["users"]:
                self.data["users"][uid].update(kwargs)
                self.data["users"][uid]["last_active"] = time.time()
                self.save()
    
    def get_user_by_code(self, code: str) -> Optional[dict]:
        """Find user by referral code"""
        for u in self.data["users"].values():
            if u.get("referral_code") == code:
                return u
        return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Find user by username"""
        username = username.lower().lstrip('@')
        for u in self.data["users"].values():
            if u.get("username", "").lower() == username:
                return u
        return None
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Add successful referral"""
        with self.lock:
            referrer = self.data["users"].get(str(referrer_id))
            referred = self.data["users"].get(str(referred_id))
            
            if not referrer or not referred:
                return False
            
            if str(referred_id) in referrer.get("referrals", {}):
                return False
            
            referrer["referrals"][str(referred_id)] = time.time()
            referrer["referrals_count"] += 1
            referrer["balance"] += Config.REFERRAL_BONUS
            referrer["total_earned"] += Config.REFERRAL_BONUS
            
            self.data["stats"]["total_referrals"] += 1
            self.save()
            return True
    
    def create_withdrawal(self, user_id: int, amount: int, wallet: str) -> str:
        """Create withdrawal request"""
        rid = f"W{int(time.time())}{user_id}{random.randint(1000,9999)}"
        with self.lock:
            self.data["withdrawals"][rid] = {
                "id": rid,
                "user_id": str(user_id),
                "amount": amount,
                "wallet": wallet,
                "status": "pending",
                "created_at": time.time(),
                "processed_at": None,
                "processed_by": None,
                "tx_hash": None,
                "notes": ""
            }
            self.data["stats"]["total_withdrawals"] += 1
            self.save()
        return rid
    
    def get_withdrawal(self, rid: str) -> Optional[dict]:
        """Get withdrawal by ID"""
        return self.data["withdrawals"].get(rid)
    
    def get_pending_withdrawals(self) -> List[dict]:
        """Get all pending withdrawals"""
        return [w for w in self.data["withdrawals"].values() if w.get("status") == "pending"]
    
    def get_user_withdrawals(self, user_id: int, status: str = None) -> List[dict]:
        """Get user withdrawals"""
        uid = str(user_id)
        withdrawals = [w for w in self.data["withdrawals"].values() if w.get("user_id") == uid]
        if status:
            withdrawals = [w for w in withdrawals if w.get("status") == status]
        return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)
    
    def process_withdrawal(self, rid: str, admin_id: int, status: str, tx_hash: str = None) -> bool:
        """Process withdrawal (approve/reject)"""
        with self.lock:
            w = self.data["withdrawals"].get(rid)
            if not w or w["status"] != "pending":
                return False
            
            w["status"] = status
            w["processed_at"] = time.time()
            w["processed_by"] = admin_id
            w["tx_hash"] = tx_hash
            
            if status == "approved":
                self.data["stats"]["total_withdrawn"] += w["amount"]
                user = self.data["users"].get(w["user_id"])
                if user:
                    user["total_withdrawn"] = user.get("total_withdrawn", 0) + w["amount"]
            elif status == "rejected":
                user = self.data["users"].get(w["user_id"])
                if user:
                    user["balance"] = user.get("balance", 0) + w["amount"]
            
            self.save()
            return True
    
    def admin_login(self, admin_id: int) -> bool:
        """Create admin session"""
        with self.lock:
            self.data["admin_sessions"][str(admin_id)] = time.time() + Config.SESSION_TIMEOUT
            self.save()
            return True
    
    def admin_logout(self, admin_id: int):
        """End admin session"""
        with self.lock:
            self.data["admin_sessions"].pop(str(admin_id), None)
            self.save()
    
    def is_admin_logged_in(self, admin_id: int) -> bool:
        """Check if admin has valid session"""
        with self.lock:
            session = self.data["admin_sessions"].get(str(admin_id))
            if not session:
                return False
            if session < time.time():
                self.data["admin_sessions"].pop(str(admin_id), None)
                self.save()
                return False
            return True
    
    def get_stats(self) -> dict:
        """Get bot statistics"""
        users = self.data["users"].values()
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
            "total_withdrawn": self.data["stats"].get("total_withdrawn", 0),
            "pending_withdrawals": len(self.get_pending_withdrawals()),
            "total_referrals": total_referrals,
            "top_referrer": f"{top_referrer.get('first_name', '')} (@{top_referrer.get('username', '')}) - {top_referrer.get('referrals_count', 0)}" if top_referrer else "None",
            "uptime": int(now - self.data["stats"].get("start_time", now))
        }

# Initialize database
db = Database()

# ==================== UTILITIES ====================
class Utils:
    """Utility functions"""
    
    @staticmethod
    def format_refi(refi: int) -> str:
        """Format REFi with USD value"""
        usd = (refi / 1_000_000) * Config.REFI_PER_MILLION
        return f"{refi:,} REFi (~${usd:.2f})"
    
    @staticmethod
    def short_wallet(wallet: str, chars: int = 6) -> str:
        """Shorten wallet address"""
        if not wallet or len(wallet) < 10:
            return "Not set"
        return f"{wallet[:chars]}...{wallet[-chars:]}"
    
    @staticmethod
    def is_valid_wallet(wallet: str) -> bool:
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
    
    @staticmethod
    def get_date(timestamp: float = None) -> str:
        """Get formatted date"""
        dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
        return dt.strftime('%Y-%m-%d %H:%M')
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape Markdown special characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

# ==================== KEYBOARDS ====================
class Keyboards:
    """Keyboard layouts"""
    
    @staticmethod
    def channels():
        """Channel verification keyboard"""
        kb = []
        for ch in Config.REQUIRED_CHANNELS:
            kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
        kb.append([{"text": "✅ VERIFY", "callback_data": "verify"}])
        return {"inline_keyboard": kb}
    
    @staticmethod
    def main_menu(user):
        """Main menu with bottom navigation"""
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
    
    @staticmethod
    def back():
        """Back button"""
        return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}
    
    @staticmethod
    def admin():
        """Admin panel"""
        return {"inline_keyboard": [
            [{"text": "📊 Statistics", "callback_data": "astats"}],
            [{"text": "💰 Pending", "callback_data": "apending"}],
            [{"text": "🔍 Search", "callback_data": "asearch"}],
            [{"text": "📢 Broadcast", "callback_data": "abcast"}],
            [{"text": "👥 Users", "callback_data": "ausers"}],
            [{"text": "🔒 Logout", "callback_data": "alogout"}]
        ]}
    
    @staticmethod
    def withdrawal_actions(rid):
        """Withdrawal action buttons"""
        return {"inline_keyboard": [
            [{"text": "✅ Approve", "callback_data": f"app_{rid}"},
             {"text": "❌ Reject", "callback_data": f"rej_{rid}"}],
            [{"text": "🔙 Back", "callback_data": "apending"}]
        ]}
    
    @staticmethod
    def user_actions(user_id, is_banned, is_admin):
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

# ==================== TELEGRAM API ====================
class Telegram:
    """Telegram API wrapper"""
    
    @classmethod
    def send_message(cls, chat_id, text, keyboard=None):
        """Send message"""
        try:
            payload = {
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            if keyboard:
                payload["reply_markup"] = keyboard
            
            response = http_session.post(f"{Config.API_URL}/sendMessage", json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ Send failed: {response.text}")
            return response
        except Exception as e:
            logger.error(f"❌ Send exception: {e}")
            return None
    
    @classmethod
    def edit_message(cls, chat_id, message_id, text, keyboard=None):
        """Edit message"""
        try:
            payload = {
                "chat_id": chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "Markdown"
            }
            if keyboard:
                payload["reply_markup"] = keyboard
            
            response = http_session.post(f"{Config.API_URL}/editMessageText", json=payload, timeout=10)
            if response.status_code != 200:
                logger.error(f"❌ Edit failed: {response.text}")
            return response
        except Exception as e:
            logger.error(f"❌ Edit exception: {e}")
            return None
    
    @classmethod
    def answer_callback(cls, callback_id):
        """Answer callback query"""
        try:
            http_session.post(f"{Config.API_URL}/answerCallbackQuery", 
                              json={"callback_query_id": callback_id}, timeout=5)
        except Exception as e:
            logger.error(f"❌ Callback error: {e}")
    
    @classmethod
    def get_chat_member(cls, chat_id, user_id):
        """Check channel membership"""
        try:
            response = http_session.get(f"{Config.API_URL}/getChatMember", 
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
        referrer = db.get_user_by_code(ref_code)
        if referrer and referrer["id"] != str(user_id):
            user_data = db.get_user(user_id)
            if not user_data.get("referred_by"):
                db.update_user(user_id, referred_by=referrer["id"])
                referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
                db.update_user(int(referrer["id"]), referral_clicks=referrer["referral_clicks"])
                logger.info(f"📋 Referral click: {referrer['id']} -> {user_id}")
    
    # Get or create user
    user_data = db.get_user(user_id)
    db.update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    # Show main menu if verified
    if user_data.get("verified"):
        text = f"🎯 *Main Menu*\n💰 {Utils.format_refi(user_data.get('balance', 0))}"
        Telegram.send_message(chat_id, text, Keyboards.main_menu(user_data))
        return
    
    # Show channel verification
    channels_text = "\n".join([f"• {ch['name']}" for ch in Config.REQUIRED_CHANNELS])
    text = (
        f"🎉 *Welcome to REFi Bot!*\n\n"
        f"💰 Welcome Bonus: {Utils.format_refi(Config.WELCOME_BONUS)}\n"
        f"👥 Referral Bonus: {Utils.format_refi(Config.REFERRAL_BONUS)} per friend\n\n"
        f"📢 *To start, you must join these channels:*\n{channels_text}\n\n"
        f"👇 Click VERIFY after joining"
    )
    Telegram.send_message(chat_id, text, Keyboards.channels())

def handle_verify(callback, user_id, chat_id, message_id):
    """Handle verify button"""
    # Check channels
    not_joined = []
    for ch in Config.REQUIRED_CHANNELS:
        status = Telegram.get_chat_member(ch["username"], user_id)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        text = "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        Telegram.edit_message(chat_id, message_id, text, Keyboards.channels())
        return
    
    # Verify user
    user_data = db.get_user(user_id)
    
    if user_data.get("verified"):
        text = f"✅ Already verified!\n{Utils.format_refi(user_data.get('balance', 0))}"
        Telegram.edit_message(chat_id, message_id, text, Keyboards.main_menu(user_data))
        return
    
    # Add welcome bonus
    new_balance = user_data.get("balance", 0) + Config.WELCOME_BONUS
    db.update_user(user_id,
                  verified=True,
                  verified_at=time.time(),
                  balance=new_balance,
                  total_earned=user_data.get("total_earned", 0) + Config.WELCOME_BONUS)
    
    # Process referral
    referred_by = user_data.get("referred_by")
    if referred_by:
        referrer = db.get_user(int(referred_by))
        if referrer:
            db.add_referral(int(referred_by), user_id)
            Telegram.send_message(int(referred_by), 
                                 f"🎉 *Friend Joined!*\n\nYou earned {Utils.format_refi(Config.REFERRAL_BONUS)}")
    
    text = f"✅ *Verified!*\n✨ Added {Utils.format_refi(Config.WELCOME_BONUS)}\n💰 {Utils.format_refi(new_balance)}"
    Telegram.edit_message(chat_id, message_id, text, Keyboards.main_menu(user_data))
    logger.info(f"✅ User {user_id} verified")

def handle_balance(callback, user_id, chat_id, message_id):
    """Show balance"""
    user_data = db.get_user(user_id)
    text = (
        f"💰 *Your Balance*\n\n"
        f"• {Utils.format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {Utils.format_refi(user_data.get('total_earned', 0))}\n"
        f"• Total withdrawn: {Utils.format_refi(user_data.get('total_withdrawn', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.back())

def handle_referral(callback, user_id, chat_id, message_id):
    """Show referral link"""
    user_data = db.get_user(user_id)
    link = f"https://t.me/{Config.BOT_USERNAME}?start={user_data.get('referral_code', '')}"
    earned = user_data.get('referrals_count', 0) * Config.REFERRAL_BONUS
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"• You earn: {Utils.format_refi(Config.REFERRAL_BONUS)} per friend\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
        f"• Earned: {Utils.format_refi(earned)}"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.back())

def handle_stats(callback, user_id, chat_id, message_id):
    """Show statistics"""
    user_data = db.get_user(user_id)
    joined = Utils.get_date(user_data.get("joined_at", 0))
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n"
        f"• Balance: {Utils.format_refi(user_data.get('balance', 0))}\n"
        f"• Referrals: {user_data.get('referrals_count', 0)}\n"
        f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
        f"• Wallet: {Utils.short_wallet(user_data.get('wallet', ''))}"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.back())

def handle_withdraw(callback, user_id, chat_id, message_id):
    """Start withdrawal process"""
    user_data = db.get_user(user_id)
    
    if not user_data.get("verified"):
        Telegram.edit_message(chat_id, message_id, "❌ Verify first!", Keyboards.back())
        return
    
    if not user_data.get("wallet"):
        Telegram.edit_message(chat_id, message_id, "⚠️ Set wallet first!", Keyboards.main_menu(user_data))
        return
    
    balance = user_data.get("balance", 0)
    if balance < Config.MIN_WITHDRAW:
        Telegram.edit_message(chat_id, message_id, 
                            f"⚠️ Min: {Utils.format_refi(Config.MIN_WITHDRAW)}\nYour: {Utils.format_refi(balance)}", 
                            Keyboards.back())
        return
    
    # Check pending withdrawals
    pending = db.get_user_withdrawals(user_id, "pending")
    if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
        Telegram.edit_message(chat_id, message_id,
                            f"⚠️ You have {len(pending)} pending withdrawals\nMax: {Config.MAX_PENDING_WITHDRAWALS}",
                            Keyboards.back())
        return
    
    text = (
        f"💸 *Withdraw*\n\n"
        f"Balance: {Utils.format_refi(balance)}\n"
        f"Min: {Utils.format_refi(Config.MIN_WITHDRAW)}\n"
        f"Wallet: {Utils.short_wallet(user_data['wallet'])}\n\n"
        f"Send amount:"
    )
    Telegram.edit_message(chat_id, message_id, text)
    user_states[user_id] = "withdraw"

def handle_set_wallet(callback, user_id, chat_id, message_id):
    """Start wallet setup"""
    user_data = db.get_user(user_id)
    current = user_data.get("wallet", "Not set")
    if current != "Not set":
        current = Utils.short_wallet(current)
    
    text = (
        f"👛 *Set Wallet*\n\n"
        f"Current: {current}\n\n"
        f"Send ETH address (0x...):"
    )
    Telegram.edit_message(chat_id, message_id, text)
    user_states[user_id] = "wallet"

def handle_back(callback, user_id, chat_id, message_id):
    """Back to main menu"""
    user_data = db.get_user(user_id)
    text = f"🎯 *Main Menu*\n💰 {Utils.format_refi(user_data.get('balance', 0))}"
    Telegram.edit_message(chat_id, message_id, text, Keyboards.main_menu(user_data))

def handle_admin_panel(callback, user_id, chat_id, message_id):
    """Show admin panel"""
    if user_id not in Config.ADMIN_IDS:
        return
    
    if not db.is_admin_logged_in(user_id):
        text = "🔐 *Please login first*\n\nUse /admin to login"
        Telegram.edit_message(chat_id, message_id, text, Keyboards.main_menu(db.get_user(user_id)))
        return
    
    stats = db.get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    
    text = (
        f"👑 *Admin Panel*\n\n"
        f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
        f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
        f"• Pending: {stats['pending_withdrawals']}\n"
        f"• Uptime: {hours}h {minutes}m"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.admin())

# ==================== ADMIN HANDLERS ====================
def handle_admin_login(message):
    """Handle /admin command"""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    if user_id not in Config.ADMIN_IDS:
        Telegram.send_message(chat_id, "⛔ Unauthorized")
        return
    
    if db.is_admin_logged_in(user_id):
        stats = db.get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *Admin Panel*\n\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
            f"• Pending: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        Telegram.send_message(chat_id, text, Keyboards.admin())
        return
    
    Telegram.send_message(chat_id, "🔐 *Admin Login*\n\nEnter password:")
    user_states[user_id] = "admin_login"

def handle_admin_login_input(text, user_id, chat_id):
    """Process admin login"""
    if text == Config.ADMIN_PASSWORD:
        db.admin_login(user_id)
        Telegram.send_message(chat_id, "✅ Login successful!")
        
        stats = db.get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *Admin Panel*\n\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
            f"• Pending: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        Telegram.send_message(chat_id, text, Keyboards.admin())
    else:
        Telegram.send_message(chat_id, "❌ Wrong password!")

def handle_admin_stats(callback, chat_id, message_id):
    """Show detailed statistics"""
    stats = db.get_stats()
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
        f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
        f"• Total earned: {Utils.format_refi(stats['total_earned'])}\n"
        f"• Withdrawn: {Utils.format_refi(stats['total_withdrawn'])}\n"
        f"• Pending: {stats['pending_withdrawals']}\n\n"
        f"📈 *Referrals*\n"
        f"• Total: {stats['total_referrals']}\n"
        f"• Top: {stats['top_referrer']}\n\n"
        f"⏱️ *Uptime: {hours}h {minutes}m*"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.admin())

def handle_admin_pending(callback, chat_id, message_id):
    """Show pending withdrawals"""
    pending = db.get_pending_withdrawals()
    
    if not pending:
        Telegram.edit_message(chat_id, message_id, "✅ No pending withdrawals", Keyboards.admin())
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    keyboard = {"inline_keyboard": []}
    
    for w in pending[:5]:
        user = db.get_user(int(w["user_id"]))
        name = user.get("first_name", "Unknown")
        text += (
            f"🆔 `{w['id'][:8]}...`\n"
            f"👤 {name}\n"
            f"💰 {Utils.format_refi(w['amount'])}\n"
            f"📅 {Utils.get_date(w['created_at'])}\n\n"
        )
        keyboard["inline_keyboard"].append([
            {"text": f"Process {w['id'][:8]}", "callback_data": f"proc_{w['id']}"}
        ])
    
    if len(pending) > 5:
        text += f"*... and {len(pending) - 5} more*\n\n"
    
    keyboard["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin"}])
    Telegram.edit_message(chat_id, message_id, text, keyboard)

def handle_process_withdrawal(callback, chat_id, message_id, rid):
    """Show withdrawal details for processing"""
    w = db.get_withdrawal(rid)
    if not w:
        return
    
    user = db.get_user(int(w["user_id"]))
    
    text = (
        f"💰 *Withdrawal Details*\n\n"
        f"📝 Request: `{rid}`\n"
        f"👤 User: {user.get('first_name', 'Unknown')} (@{user.get('username', '')})\n"
        f"🆔 ID: `{w['user_id']}`\n"
        f"💰 Amount: {Utils.format_refi(w['amount'])}\n"
        f"📮 Wallet: `{w['wallet']}`\n"
        f"📅 Created: {Utils.get_date(w['created_at'])}"
    )
    Telegram.edit_message(chat_id, message_id, text, Keyboards.withdrawal_actions(rid))

def handle_approve_withdrawal(callback, admin_id, chat_id, message_id, rid):
    """Approve withdrawal"""
    if db.process_withdrawal(rid, admin_id, "approved"):
        w = db.get_withdrawal(rid)
        if w:
            Telegram.send_message(int(w["user_id"]),
                                f"✅ *Withdrawal Approved!*\n\n"
                                f"Request: `{rid[:8]}...`\n"
                                f"Amount: {Utils.format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_reject_withdrawal(callback, admin_id, chat_id, message_id, rid):
    """Reject withdrawal"""
    if db.process_withdrawal(rid, admin_id, "rejected"):
        w = db.get_withdrawal(rid)
        if w:
            Telegram.send_message(int(w["user_id"]),
                                f"❌ *Withdrawal Rejected*\n\n"
                                f"Request: `{rid[:8]}...`\n"
                                f"Amount: {Utils.format_refi(w['amount'])}")
    handle_admin_pending(callback, chat_id, message_id)

def handle_admin_search(callback, chat_id, message_id):
    """Initiate user search"""
    Telegram.edit_message(chat_id, message_id, "🔍 *Send User ID or @username:*")
    user_states[callback["from"]["id"]] = "admin_search"

def handle_admin_search_input(text, admin_id, chat_id):
    """Process user search"""
    found = None
    if text.isdigit():
        found = db.get_user(int(text))
    else:
        found = db.get_user_by_username(text)
    
    if not found:
        Telegram.send_message(chat_id, f"❌ User not found: {text}")
        return
    
    pending = len(db.get_user_withdrawals(int(found["id"]), "pending"))
    
    text = (
        f"👤 *User Found*\n\n"
        f"ID: `{found['id']}`\n"
        f"Username: @{found.get('username', 'None')}\n"
        f"Name: {found.get('first_name', 'Unknown')}\n"
        f"Balance: {Utils.format_refi(found.get('balance', 0))}\n"
        f"Referrals: {found.get('referrals_count', 0)}\n"
        f"Verified: {'✅' if found.get('verified') else '❌'}\n"
        f"Wallet: {Utils.short_wallet(found.get('wallet', ''))}\n"
        f"Pending withdrawals: {pending}"
    )
    Telegram.send_message(chat_id, text, Keyboards.user_actions(int(found["id"]), 
                                                                 found.get("is_banned", False), 
                                                                 found.get("is_admin", False)))

def handle_admin_broadcast(callback, chat_id, message_id):
    """Initiate broadcast"""
    Telegram.edit_message(chat_id, message_id, 
                        f"📢 *Broadcast*\n\nSend message to {len(db.data['users'])} users:")
    user_states[callback["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(text, admin_id, chat_id):
    """Process broadcast"""
    Telegram.send_message(chat_id, f"📢 Broadcasting to {len(db.data['users'])} users...")
    
    sent = 0
    failed = 0
    
    for uid in db.data["users"].keys():
        try:
            Telegram.send_message(int(uid), text)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)
        except:
            failed += 1
    
    Telegram.send_message(chat_id, f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}")

def handle_admin_users(callback, chat_id, message_id):
    """Show recent users"""
    users_list = sorted(db.data["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    
    text = "👥 *Recent Users*\n\n"
    for u in users_list:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = Utils.get_date(u.get("joined_at", 0)).split()[0]
        text += f"{verified} {name} {username} - {joined}\n"
    
    text += f"\n*Total: {len(db.data['users'])} users*"
    Telegram.edit_message(chat_id, message_id, text, Keyboards.admin())

def handle_admin_logout(callback, admin_id, chat_id, message_id):
    """Logout from admin panel"""
    db.admin_logout(admin_id)
    user_data = db.get_user(admin_id)
    text = f"🔒 *Logged out*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
    Telegram.edit_message(chat_id, message_id, text, Keyboards.main_menu(user_data))

def handle_user_action(callback, admin_id, chat_id, message_id, action, target_id):
    """Handle user management actions"""
    target_user = db.get_user(target_id)
    
    if action == "ban":
        db.update_user(target_id, is_banned=True)
        Telegram.send_message(chat_id, f"✅ User {target_id} banned")
    elif action == "unban":
        db.update_user(target_id, is_banned=False)
        Telegram.send_message(chat_id, f"✅ User {target_id} unbanned")
    elif action == "make_admin":
        db.update_user(target_id, is_admin=True)
        Telegram.send_message(chat_id, f"✅ User {target_id} is now admin")
    elif action == "remove_admin":
        db.update_user(target_id, is_admin=False)
        Telegram.send_message(chat_id, f"✅ User {target_id} is no longer admin")
    
    # Refresh user info
    handle_admin_search_input(str(target_id), admin_id, chat_id)

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(text, user_id, chat_id):
    """Save wallet address"""
    if Utils.is_valid_wallet(text):
        db.update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = db.get_user(user_id)
        Telegram.send_message(chat_id, f"✅ *Wallet saved!*\n{Utils.short_wallet(text)}", 
                            Keyboards.main_menu(user_data))
    else:
        Telegram.send_message(chat_id, "❌ Invalid wallet! Must be 0x + 40 chars")

def handle_withdraw_input(text, user_id, chat_id):
    """Process withdrawal amount"""
    try:
        amount = int(text.replace(',', '').strip())
    except ValueError:
        Telegram.send_message(chat_id, "❌ Invalid number")
        return
    
    user_data = db.get_user(user_id)
    
    if amount < Config.MIN_WITHDRAW:
        Telegram.send_message(chat_id, f"❌ Min is {Utils.format_refi(Config.MIN_WITHDRAW)}")
        return
    
    if amount > user_data.get("balance", 0):
        Telegram.send_message(chat_id, f"❌ Insufficient balance")
        return
    
    # Check pending withdrawals
    pending = db.get_user_withdrawals(user_id, "pending")
    if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
        Telegram.send_message(chat_id, f"❌ You have {len(pending)} pending withdrawals")
        return
    
    # Create withdrawal
    rid = db.create_withdrawal(user_id, amount, user_data["wallet"])
    db.update_user(user_id, balance=user_data["balance"] - amount)
    
    Telegram.send_message(chat_id, f"✅ *Withdrawal requested!*\nID: {rid[:8]}...", 
                         Keyboards.main_menu(user_data))
    
    # Notify admins
    for admin_id in Config.ADMIN_IDS:
        Telegram.send_message(admin_id,
                            f"💰 *New Withdrawal*\n\n"
                            f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                            f"Amount: {Utils.format_refi(amount)}\n"
                            f"Wallet: {user_data['wallet']}\n"
                            f"ID: `{rid}`")

# ==================== WEB SERVER FOR RENDER ====================
class HealthHandler(BaseHTTPRequestHandler):
    """Health check handler"""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        stats = db.get_stats()
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
    <p>@{Config.BOT_USERNAME}</p>
    <p>Users: {stats['total_users']} | Verified: {stats['verified']}</p>
    <p><small>Uptime: {hours}h {minutes}m | {Utils.get_date()}</small></p>
</body>
</html>"""
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        pass

# ==================== START WEB SERVER ====================
web_thread = threading.Thread(target=lambda: HTTPServer(('0.0.0.0', Config.PORT), HealthHandler).serve_forever(), daemon=True)
web_thread.start()
logger.info(f"🌐 Web server on port {Config.PORT}")

# ==================== CLEAR OLD SESSIONS ====================
logger.info("🔄 Clearing old sessions...")
try:
    http_session.post(f"{Config.API_URL}/deleteWebhook", json={"drop_pending_updates": True}, timeout=10)
    http_session.get(f"{Config.API_URL}/getUpdates", params={"offset": -1, "timeout": 0}, timeout=10)
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
            response = http_session.post(f"{Config.API_URL}/getUpdates", json={
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
                        user_data = db.get_user(user_id)
                        if user_data.get("is_banned"):
                            Telegram.send_message(chat_id, "⛔ You are banned")
                            offset = update["update_id"] + 1
                            continue
                        
                        # Handle commands
                        if text == "/start":
                            handle_start(msg)
                        elif text == "/admin":
                            handle_admin_login(msg)
                        elif text.startswith("/"):
                            Telegram.send_message(chat_id, "❌ Unknown command")
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
                        
                        Telegram.answer_callback(cb["id"])
                        
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
                http_session.post(f"{Config.API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                time.sleep(5)
                offset = 0
                    
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

# ==================== START ====================
if __name__ == "__main__":
    try:
        print("\n" + "="*70)
        print("🤖 REFi BOT - PREMIUM FINAL EDITION v17.0")
        print("="*70)
        print(f"📱 Bot: @{Config.BOT_USERNAME}")
        print(f"👤 Admins: {Config.ADMIN_IDS}")
        print(f"💰 Welcome: {Utils.format_refi(Config.WELCOME_BONUS)}")
        print(f"👥 Users: {len(db.data['users'])}")
        print(f"🌐 Port: {Config.PORT}")
        print("="*70 + "\n")
        
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped")
    except Exception as e:
        logger.exception("❌ Fatal error")
        print(f"\n❌ Fatal error: {e}")

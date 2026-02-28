#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - PROFESSIONAL COMPLETE EDITION v12.0.0                          ║
║     Telegram Referral & Earn Bot with All Features                               ║
║     Python: 3.14.3 | Platform: Render Web Service (FREE)                         ║
║                                                                                  ║
║     ✨ COMPLETE FEATURES:                                                         ║
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
from typing import Dict, Optional, List, Any, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict
import signal

# ==================== REQUESTS SETUP ====================
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    os.system("pip install requests==2.31.0")
    import requests

# ==================== CONFIGURATION ====================

class Config:
    """🎯 Professional Configuration Management"""
    
    # Bot Core
    BOT_TOKEN = "8720874613:AAE8nFWsJCX-8tAmfxis6UFgVUfPLGLt5pA"
    BOT_USERNAME = "Realfinancepaybot"
    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
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
    
    # Limits & Restrictions
    MAX_PENDING_WITHDRAWALS = 3
    SESSION_TIMEOUT = 3600  # 1 hour
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    PORT = int(os.environ.get('PORT', 10000))
    
    # Database
    DB_FILE = "bot_data.json"

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== REQUEST SESSION ====================

def create_session():
    """🔌 Create requests session with retry strategy"""
    session = requests.Session()
    retries = Retry(
        total=Config.MAX_RETRIES,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504]
    )
    session.mount('https://', HTTPAdapter(max_retries=retries))
    session.mount('http://', HTTPAdapter(max_retries=retries))
    return session

http_session = create_session()

# ==================== DATABASE ====================

class Database:
    """💾 Thread-safe database with auto-save"""
    
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
        """📂 Load data from file"""
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
        """💾 Save data to file"""
        try:
            with self.lock:
                with open(Config.DB_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Save error: {e}")
    
    def get_user(self, user_id: int) -> dict:
        """👤 Get or create user"""
        uid = str(user_id)
        with self.lock:
            if uid not in self.data["users"]:
                self.data["users"][uid] = {
                    "id": uid,
                    "username": "",
                    "first_name": "",
                    "last_name": "",
                    "language": "en",
                    "joined_at": time.time(),
                    "last_active": time.time(),
                    "balance": 0,
                    "total_earned": 0,
                    "total_withdrawn": 0,
                    "referral_code": self._generate_code(),
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
                    "daily_referrals": {},
                    "daily_withdrawals": 0,
                    "last_withdrawal_date": None,
                    "notes": ""
                }
                self.data["stats"]["total_users"] = len(self.data["users"])
                self.save()
            return self.data["users"][uid]
    
    def update_user(self, user_id: int, **kwargs):
        """📝 Update user data"""
        uid = str(user_id)
        with self.lock:
            if uid in self.data["users"]:
                self.data["users"][uid].update(kwargs)
                self.data["users"][uid]["last_active"] = time.time()
                self.save()
    
    def _generate_code(self) -> str:
        """🔑 Generate unique referral code"""
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=8))
            if not any(u.get("referral_code") == code for u in self.data["users"].values()):
                return code
    
    def get_user_by_code(self, code: str) -> Optional[dict]:
        """🔍 Find user by referral code"""
        for u in self.data["users"].values():
            if u.get("referral_code") == code:
                return u
        return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """🔍 Find user by username"""
        username = username.lower().lstrip('@')
        for u in self.data["users"].values():
            if u.get("username", "").lower() == username:
                return u
        return None
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """🤝 Add successful referral"""
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
            
            today = datetime.now().strftime('%Y-%m-%d')
            referrer["daily_referrals"][today] = referrer["daily_referrals"].get(today, 0) + 1
            
            self.data["stats"]["total_referrals"] += 1
            self.save()
            return True
    
    def create_withdrawal(self, user_id: int, amount: int, wallet: str) -> str:
        """💸 Create withdrawal request"""
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
        """🔍 Get withdrawal by ID"""
        return self.data["withdrawals"].get(rid)
    
    def get_pending_withdrawals(self) -> List[dict]:
        """⏳ Get all pending withdrawals"""
        return [w for w in self.data["withdrawals"].values() if w.get("status") == "pending"]
    
    def get_user_withdrawals(self, user_id: int, status: str = None) -> List[dict]:
        """📋 Get user withdrawals"""
        uid = str(user_id)
        withdrawals = [w for w in self.data["withdrawals"].values() if w.get("user_id") == uid]
        if status:
            withdrawals = [w for w in withdrawals if w.get("status") == status]
        return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)
    
    def process_withdrawal(self, rid: str, admin_id: int, status: str, tx_hash: str = None) -> bool:
        """✅❌ Process withdrawal"""
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
                    user["total_withdrawn"] += w["amount"]
                    user["daily_withdrawals"] += w["amount"]
                    user["last_withdrawal_date"] = datetime.now().strftime('%Y-%m-%d')
            elif status == "rejected":
                user = self.data["users"].get(w["user_id"])
                if user:
                    user["balance"] += w["amount"]
            
            self.save()
            return True
    
    def admin_login(self, admin_id: int) -> bool:
        """🔐 Create admin session"""
        with self.lock:
            self.data["admin_sessions"][str(admin_id)] = time.time() + Config.SESSION_TIMEOUT
            self.save()
            return True
    
    def admin_logout(self, admin_id: int):
        """🔒 End admin session"""
        with self.lock:
            self.data["admin_sessions"].pop(str(admin_id), None)
            self.save()
    
    def is_admin_logged_in(self, admin_id: int) -> bool:
        """✅ Check if admin has valid session"""
        with self.lock:
            session = self.data["admin_sessions"].get(str(admin_id))
            if not session:
                return False
            if session < time.time():
                del self.data["admin_sessions"][str(admin_id)]
                self.save()
                return False
            return True
    
    def get_stats(self) -> dict:
        """📊 Get bot statistics"""
        users = self.data["users"].values()
        now = time.time()
        
        # Calculate active users
        active_today = sum(1 for u in users if u.get("last_active", 0) > now - 86400)
        active_week = sum(1 for u in users if u.get("last_active", 0) > now - 604800)
        
        # Calculate totals
        total_balance = sum(u.get("balance", 0) for u in users)
        total_earned = sum(u.get("total_earned", 0) for u in users)
        total_referrals = sum(u.get("referrals_count", 0) for u in users)
        
        # Find top referrer
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
    """🛠️ Utility functions"""
    
    @staticmethod
    def format_refi(refi: int) -> str:
        """Format REFi with USD value"""
        usd = (refi / 1_000_000) * Config.REFI_PER_MILLION
        return f"{refi:,} REFi (~${usd:.2f})"
    
    @staticmethod
    def short_wallet(wallet: str, chars: int = 6) -> str:
        """Shorten wallet address for display"""
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
    def get_today() -> str:
        """Get today's date"""
        return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape Markdown special characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text

# ==================== KEYBOARDS ====================

class Keyboards:
    """🎨 Professional Keyboard Layouts"""
    
    @staticmethod
    def channels() -> dict:
        """📢 Channel verification keyboard"""
        keyboard = []
        for ch in Config.REQUIRED_CHANNELS:
            keyboard.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
        keyboard.append([{"text": "✅ VERIFY MEMBERSHIP", "callback_data": "verify"}])
        return {"inline_keyboard": keyboard}
    
    @staticmethod
    def main_menu(user: dict) -> dict:
        """🎯 Main menu with bottom navigation"""
        keyboard = [
            [   # Row 1
                {"text": "💰 Balance", "callback_data": "balance"},
                {"text": "🔗 Referral", "callback_data": "referral"}
            ],
            [   # Row 2
                {"text": "💸 Withdraw", "callback_data": "withdraw"},
                {"text": "📊 Stats", "callback_data": "stats"}
            ]
        ]
        
        # Row 3: Conditional buttons
        row3 = []
        if not user.get("wallet"):
            row3.append({"text": "👛 Set Wallet", "callback_data": "set_wallet"})
        if user.get("is_admin"):
            row3.append({"text": "👑 Admin Panel", "callback_data": "admin_panel"})
        if row3:
            keyboard.append(row3)
        
        return {"inline_keyboard": keyboard}
    
    @staticmethod
    def back() -> dict:
        """🔙 Back button"""
        return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "back"}]]}
    
    @staticmethod
    def admin() -> dict:
        """👑 Admin panel"""
        return {"inline_keyboard": [
            [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
            [{"text": "💰 Pending Withdrawals", "callback_data": "admin_pending"}],
            [{"text": "🔍 Search User", "callback_data": "admin_search"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
            [{"text": "👥 Users List", "callback_data": "admin_users"}],
            [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
        ]}
    
    @staticmethod
    def withdrawal_actions(rid: str) -> dict:
        """💰 Withdrawal action buttons"""
        return {"inline_keyboard": [
            [
                {"text": "✅ Approve", "callback_data": f"approve_{rid}"},
                {"text": "❌ Reject", "callback_data": f"reject_{rid}"}
            ],
            [{"text": "🔙 Back", "callback_data": "admin_pending"}]
        ]}
    
    @staticmethod
    def user_actions(user_id: int, is_banned: bool, is_admin: bool) -> dict:
        """👤 User management buttons"""
        keyboard = []
        
        if is_banned:
            keyboard.append([{"text": "✅ Unban User", "callback_data": f"unban_{user_id}"}])
        else:
            keyboard.append([{"text": "🔨 Ban User", "callback_data": f"ban_{user_id}"}])
        
        if is_admin:
            keyboard.append([{"text": "👤 Remove Admin", "callback_data": f"remove_admin_{user_id}"}])
        else:
            keyboard.append([{"text": "👑 Make Admin", "callback_data": f"make_admin_{user_id}"}])
        
        keyboard.append([{"text": "🔙 Back", "callback_data": "admin_panel"}])
        
        return {"inline_keyboard": keyboard}

# ==================== TELEGRAM API ====================

class TelegramAPI:
    """📱 Telegram API Wrapper"""
    
    @classmethod
    def _request(cls, method: str, json: dict = None, params: dict = None) -> Optional[dict]:
        """Make API request"""
        url = f"{Config.API_URL}/{method}"
        try:
            if params:
                response = http_session.get(url, params=params, timeout=Config.REQUEST_TIMEOUT)
            else:
                response = http_session.post(url, json=json, timeout=Config.REQUEST_TIMEOUT)
            data = response.json()
            if data.get("ok"):
                return data.get("result")
            else:
                logger.error(f"❌ Telegram API error: {data.get('description')}")
                return None
        except Exception as e:
            logger.error(f"❌ Request error: {e}")
            return None
    
    @classmethod
    def send_message(cls, chat_id: int, text: str, keyboard: dict = None) -> Optional[dict]:
        """Send message"""
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = keyboard
        return cls._request("sendMessage", json=payload)
    
    @classmethod
    def edit_message(cls, chat_id: int, msg_id: int, text: str, keyboard: dict = None) -> Optional[dict]:
        """Edit message"""
        payload = {
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        if keyboard:
            payload["reply_markup"] = keyboard
        return cls._request("editMessageText", json=payload)
    
    @classmethod
    def answer_callback(cls, callback_id: str, text: str = None) -> Optional[dict]:
        """Answer callback query"""
        payload = {"callback_query_id": callback_id}
        if text:
            payload["text"] = text
        return cls._request("answerCallbackQuery", json=payload)
    
    @classmethod
    def get_chat_member(cls, chat_id: str, user_id: int) -> Optional[str]:
        """Get chat member status"""
        params = {"chat_id": chat_id, "user_id": user_id}
        result = cls._request("getChatMember", params=params)
        return result.get("status") if result else None

# ==================== MESSAGE TEMPLATES ====================

class Messages:
    """💬 Message templates"""
    
    WELCOME = (
        "🎉 *Welcome to REFi Bot!*\n\n"
        "💰 *Welcome Bonus:* {welcome}\n"
        "👥 *Referral Bonus:* {referral} per friend\n\n"
        "📢 *To start, you must join these channels:*\n{channels}\n\n"
        "👇 Click VERIFY after joining"
    )
    
    VERIFY_SUCCESS = (
        "✅ *Verification Successful!*\n\n"
        "✨ Added {welcome} to your balance\n"
        "💰 Current: {balance}\n\n"
        "👇 Use the buttons below to navigate"
    )
    
    VERIFY_FAILED = (
        "❌ *Verification Failed*\n\n"
        "You haven't joined these channels yet:\n{not_joined}\n\n"
        "Please join them and try again."
    )
    
    MAIN_MENU = (
        "🎯 *Main Menu*\n\n"
        "💰 Balance: {balance}\n"
        "👥 Referrals: {referrals}"
    )
    
    BALANCE = (
        "💰 *Your Balance*\n\n"
        "• {balance}\n"
        "• Total earned: {total_earned}\n"
        "• Total withdrawn: {total_withdrawn}\n"
        "• Referrals: {referrals}"
    )
    
    REFERRAL = (
        "🔗 *Your Referral Link*\n\n"
        "`{link}`\n\n"
        "🎁 *Rewards*\n"
        "• You earn: {referral} per friend\n"
        "• Friend gets: {welcome}\n\n"
        "📊 *Stats*\n"
        "• Clicks: {clicks}\n"
        "• Successful: {successful}\n"
        "• Earned: {earned}"
    )
    
    STATS = (
        "📊 *Your Statistics*\n\n"
        "👤 *User Info*\n"
        "• ID: `{user_id}`\n"
        "• Joined: {joined}\n\n"
        "💰 *Financial*\n"
        "• Balance: {balance}\n"
        "• Total earned: {total_earned}\n"
        "• Withdrawn: {total_withdrawn}\n\n"
        "👥 *Referrals*\n"
        "• Count: {referrals}\n"
        "• Clicks: {clicks}\n\n"
        "✅ *Status*\n"
        "• Verified: {verified}\n"
        "• Wallet: {wallet}"
    )
    
    SET_WALLET = (
        "👛 *Set Withdrawal Wallet*\n\n"
        "Current wallet: {wallet}\n\n"
        "Please enter your Ethereum wallet address.\n"
        "It must start with `0x` and be 42 characters long.\n\n"
        "Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
    )
    
    WALLET_SUCCESS = (
        "✅ *Wallet saved successfully!*\n\n"
        "Wallet: {wallet}\n\n"
        "You can now withdraw your REFi tokens."
    )
    
    WITHDRAW = (
        "💸 *Withdraw*\n\n"
        "Balance: {balance}\n"
        "Minimum: {min_withdraw}\n"
        "Wallet: {wallet}\n\n"
        "Send the amount you want to withdraw:"
    )
    
    WITHDRAW_NO_WALLET = (
        "⚠️ *You need to set a wallet first!*\n\n"
        "Please use the 👛 Set Wallet button to add your wallet address."
    )
    
    WITHDRAW_BELOW_MIN = (
        "⚠️ *Minimum withdrawal: {min_withdraw}*\n"
        "Your balance: {balance}\n\n"
        "You need {needed} more to withdraw."
    )
    
    WITHDRAW_PENDING_LIMIT = (
        "⚠️ You have {count} pending withdrawals.\n"
        "Max allowed: {max_count}"
    )
    
    WITHDRAW_SUCCESS = (
        "✅ *Withdrawal Request Submitted!*\n\n"
        "📝 Request ID: `{request_id}`\n"
        "💰 Amount: {amount}\n\n"
        "⏳ Status: *Pending Review*"
    )
    
    ADMIN_PANEL = (
        "👑 *Admin Panel*\n\n"
        "📊 *Statistics*\n"
        "• Users: {total_users} (✅ {verified})\n"
        "• Balance: {total_balance}\n"
        "• Pending withdrawals: {pending_withdrawals}\n"
        "• Uptime: {uptime}"
    )
    
    ADMIN_STATS = (
        "📊 *Detailed Statistics*\n\n"
        "👥 *Users*\n"
        "• Total: {total_users}\n"
        "• Verified: {verified}\n"
        "• Banned: {banned}\n"
        "• Active today: {active_today}\n"
        "• Active week: {active_week}\n\n"
        "💰 *Financial*\n"
        "• Total balance: {total_balance}\n"
        "• Total earned: {total_earned}\n"
        "• Total withdrawn: {total_withdrawn}\n"
        "• Pending withdrawals: {pending_withdrawals}\n\n"
        "📈 *Referrals*\n"
        "• Total: {total_referrals}\n"
        "• Top referrer: {top_referrer}\n\n"
        "⏱️ *Uptime: {uptime}*"
    )

# ==================== HANDLERS ====================

class Handlers:
    """🎯 Professional Handlers"""
    
    # User states
    user_states = {}
    
    @classmethod
    def start(cls, message: dict):
        """🚀 /start command"""
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
        
        # Get/create user
        user_data = db.get_user(user_id)
        db.update_user(user_id, 
                      username=user.get("username", ""),
                      first_name=user.get("first_name", ""))
        
        # Show main menu if verified
        if user_data.get("verified"):
            text = Messages.MAIN_MENU.format(
                balance=Utils.format_refi(user_data.get('balance', 0)),
                referrals=user_data.get('referrals_count', 0)
            )
            TelegramAPI.send_message(chat_id, text, Keyboards.main_menu(user_data))
            return
        
        # Show channel verification
        channels = "\n".join([f"• {ch['name']}" for ch in Config.REQUIRED_CHANNELS])
        text = Messages.WELCOME.format(
            welcome=Utils.format_refi(Config.WELCOME_BONUS),
            referral=Utils.format_refi(Config.REFERRAL_BONUS),
            channels=channels
        )
        TelegramAPI.send_message(chat_id, text, Keyboards.channels())
    
    @classmethod
    def verify(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """✅ Verify membership"""
        # Check channels
        not_joined = []
        for ch in Config.REQUIRED_CHANNELS:
            status = TelegramAPI.get_chat_member(ch["username"], user_id)
            if status not in ["member", "administrator", "creator"]:
                not_joined.append(ch["name"])
        
        if not_joined:
            text = Messages.VERIFY_FAILED.format(not_joined="\n".join([f"• {ch}" for ch in not_joined]))
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.channels())
            return
        
        # Verify user
        user_data = db.get_user(user_id)
        
        if user_data.get("verified"):
            text = Messages.MAIN_MENU.format(
                balance=Utils.format_refi(user_data.get('balance', 0)),
                referrals=user_data.get('referrals_count', 0)
            )
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(user_data))
            return
        
        # Add welcome bonus
        new_balance = user_data.get("balance", 0) + Config.WELCOME_BONUS
        db.update_user(user_id,
                      verified=True,
                      verified_at=time.time(),
                      balance=new_balance,
                      total_earned=user_data.get("total_earned", 0) + Config.WELCOME_BONUS)
        
        # Process referral
        if user_data.get("referred_by"):
            referrer = db.get_user(int(user_data["referred_by"]))
            if referrer:
                db.add_referral(int(user_data["referred_by"]), user_id)
                try:
                    TelegramAPI.send_message(
                        int(user_data["referred_by"]),
                        f"🎉 *Friend Joined!*\n\n"
                        f"{user_data.get('first_name', 'Someone')} joined using your link!\n"
                        f"✨ You earned {Utils.format_refi(Config.REFERRAL_BONUS)}"
                    )
                except:
                    pass
        
        text = Messages.VERIFY_SUCCESS.format(
            welcome=Utils.format_refi(Config.WELCOME_BONUS),
            balance=Utils.format_refi(new_balance)
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(user_data))
        logger.info(f"✅ User {user_id} verified")
    
    @classmethod
    def balance(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💰 Show balance"""
        user_data = db.get_user(user_id)
        text = Messages.BALANCE.format(
            balance=Utils.format_refi(user_data.get('balance', 0)),
            total_earned=Utils.format_refi(user_data.get('total_earned', 0)),
            total_withdrawn=Utils.format_refi(user_data.get('total_withdrawn', 0)),
            referrals=user_data.get('referrals_count', 0)
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.back())
    
    @classmethod
    def referral(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔗 Show referral link"""
        user_data = db.get_user(user_id)
        link = f"https://t.me/{Config.BOT_USERNAME}?start={user_data.get('referral_code', '')}"
        earned = user_data.get('referrals_count', 0) * Config.REFERRAL_BONUS
        
        text = Messages.REFERRAL.format(
            link=link,
            referral=Utils.format_refi(Config.REFERRAL_BONUS),
            welcome=Utils.format_refi(Config.WELCOME_BONUS),
            clicks=user_data.get('referral_clicks', 0),
            successful=user_data.get('referrals_count', 0),
            earned=Utils.format_refi(earned)
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.back())
    
    @classmethod
    def stats(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """📊 Show statistics"""
        user_data = db.get_user(user_id)
        joined = Utils.get_date(user_data.get("joined_at", 0))
        
        text = Messages.STATS.format(
            user_id=user_id,
            joined=joined,
            balance=Utils.format_refi(user_data.get('balance', 0)),
            total_earned=Utils.format_refi(user_data.get('total_earned', 0)),
            total_withdrawn=Utils.format_refi(user_data.get('total_withdrawn', 0)),
            referrals=user_data.get('referrals_count', 0),
            clicks=user_data.get('referral_clicks', 0),
            verified='✅' if user_data.get('verified') else '❌',
            wallet=Utils.short_wallet(user_data.get('wallet', ''))
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.back())
    
    @classmethod
    def withdraw(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💸 Start withdrawal process"""
        user_data = db.get_user(user_id)
        
        if not user_data.get("verified"):
            TelegramAPI.edit_message(chat_id, msg_id, "❌ You must verify first!", Keyboards.back())
            return
        
        if not user_data.get("wallet"):
            text = Messages.WITHDRAW_NO_WALLET
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(user_data))
            return
        
        balance = user_data.get("balance", 0)
        if balance < Config.MIN_WITHDRAW:
            needed = Config.MIN_WITHDRAW - balance
            text = Messages.WITHDRAW_BELOW_MIN.format(
                min_withdraw=Utils.format_refi(Config.MIN_WITHDRAW),
                balance=Utils.format_refi(balance),
                needed=Utils.format_refi(needed)
            )
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.back())
            return
        
        # Check pending withdrawals
        pending = db.get_user_withdrawals(user_id, "pending")
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            text = Messages.WITHDRAW_PENDING_LIMIT.format(
                count=len(pending),
                max_count=Config.MAX_PENDING_WITHDRAWALS
            )
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.back())
            return
        
        text = Messages.WITHDRAW.format(
            balance=Utils.format_refi(balance),
            min_withdraw=Utils.format_refi(Config.MIN_WITHDRAW),
            wallet=Utils.short_wallet(user_data['wallet'])
        )
        TelegramAPI.edit_message(chat_id, msg_id, text)
        
        # Set state
        cls.user_states[user_id] = {"action": "withdraw_amount"}
    
    @classmethod
    def set_wallet(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """👛 Start wallet setup"""
        user_data = db.get_user(user_id)
        current = user_data.get("wallet", "Not set")
        if current != "Not set":
            current = Utils.short_wallet(current)
        
        text = Messages.SET_WALLET.format(wallet=current)
        TelegramAPI.edit_message(chat_id, msg_id, text)
        
        # Set state
        cls.user_states[user_id] = {"action": "wallet"}
    
    @classmethod
    def back(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔙 Back to main menu"""
        user_data = db.get_user(user_id)
        text = Messages.MAIN_MENU.format(
            balance=Utils.format_refi(user_data.get('balance', 0)),
            referrals=user_data.get('referrals_count', 0)
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(user_data))
    
    @classmethod
    def admin_panel(cls, callback: dict, user_id: int, chat_id: int, msg_id: int):
        """👑 Admin panel access"""
        if user_id not in Config.ADMIN_IDS:
            TelegramAPI.answer_callback(callback["id"], "⛔ Unauthorized")
            return
        
        if not db.is_admin_logged_in(user_id):
            text = "🔐 *Please login first*\n\nUse /admin command to login."
            TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(db.get_user(user_id)))
            return
        
        stats = db.get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        
        text = Messages.ADMIN_PANEL.format(
            total_users=stats['total_users'],
            verified=stats['verified'],
            total_balance=Utils.format_refi(stats['total_balance']),
            pending_withdrawals=stats['pending_withdrawals'],
            uptime=f"{hours}h {minutes}m"
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.admin())
    
    # ==================== ADMIN HANDLERS ====================
    
    @classmethod
    def admin_login(cls, message: dict):
        """👑 Admin login command"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if user_id not in Config.ADMIN_IDS:
            TelegramAPI.send_message(chat_id, "⛔ Unauthorized")
            return
        
        if db.is_admin_logged_in(user_id):
            stats = db.get_stats()
            hours = stats['uptime'] // 3600
            minutes = (stats['uptime'] % 3600) // 60
            
            text = Messages.ADMIN_PANEL.format(
                total_users=stats['total_users'],
                verified=stats['verified'],
                total_balance=Utils.format_refi(stats['total_balance']),
                pending_withdrawals=stats['pending_withdrawals'],
                uptime=f"{hours}h {minutes}m"
            )
            TelegramAPI.send_message(chat_id, text, Keyboards.admin())
            return
        
        TelegramAPI.send_message(chat_id, "🔐 *Admin Login*\n\nPlease enter password:")
        cls.user_states[user_id] = {"action": "admin_login"}
    
    @classmethod
    def handle_admin_login(cls, text: str, user_id: int, chat_id: int):
        """✅ Process admin login"""
        if text == Config.ADMIN_PASSWORD:
            db.admin_login(user_id)
            TelegramAPI.send_message(chat_id, "✅ Login successful!")
            
            stats = db.get_stats()
            hours = stats['uptime'] // 3600
            minutes = (stats['uptime'] % 3600) // 60
            
            text = Messages.ADMIN_PANEL.format(
                total_users=stats['total_users'],
                verified=stats['verified'],
                total_balance=Utils.format_refi(stats['total_balance']),
                pending_withdrawals=stats['pending_withdrawals'],
                uptime=f"{hours}h {minutes}m"
            )
            TelegramAPI.send_message(chat_id, text, Keyboards.admin())
        else:
            TelegramAPI.send_message(chat_id, "❌ Wrong password!")
    
    @classmethod
    def admin_stats(cls, callback: dict, chat_id: int, msg_id: int):
        """📊 Show detailed statistics"""
        stats = db.get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        
        text = Messages.ADMIN_STATS.format(
            total_users=stats['total_users'],
            verified=stats['verified'],
            banned=stats['banned'],
            active_today=stats['active_today'],
            active_week=stats['active_week'],
            total_balance=Utils.format_refi(stats['total_balance']),
            total_earned=Utils.format_refi(stats['total_earned']),
            total_withdrawn=Utils.format_refi(stats['total_withdrawn']),
            pending_withdrawals=stats['pending_withdrawals'],
            total_referrals=stats['total_referrals'],
            top_referrer=stats['top_referrer'],
            uptime=f"{hours}h {minutes}m"
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.admin())
    
    @classmethod
    def admin_pending(cls, callback: dict, chat_id: int, msg_id: int):
        """💰 Show pending withdrawals"""
        pending = db.get_pending_withdrawals()
        
        if not pending:
            TelegramAPI.edit_message(chat_id, msg_id, "✅ No pending withdrawals", Keyboards.admin())
            return
        
        text = "💰 *Pending Withdrawals*\n\n"
        keyboard = {"inline_keyboard": []}
        
        for w in pending[:5]:
            user = db.get_user(int(w["user_id"]))
            name = user.get("first_name", "Unknown")
            username = f"@{user.get('username', '')}" if user.get('username') else "No username"
            
            text += (
                f"🆔 `{w['id'][:8]}...`\n"
                f"👤 {name} ({username})\n"
                f"💰 {Utils.format_refi(w['amount'])}\n"
                f"📅 {Utils.get_date(w['created_at'])}\n\n"
            )
            keyboard["inline_keyboard"].append([
                {"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}
            ])
        
        if len(pending) > 5:
            text += f"*... and {len(pending) - 5} more*\n\n"
        
        keyboard["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin_panel"}])
        TelegramAPI.edit_message(chat_id, msg_id, text, keyboard)
    
    @classmethod
    def admin_process(cls, callback: dict, chat_id: int, msg_id: int, rid: str):
        """⚙️ Process withdrawal"""
        w = db.get_withdrawal(rid)
        if not w:
            TelegramAPI.answer_callback(callback["id"], "❌ Not found")
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
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.withdrawal_actions(rid))
    
    @classmethod
    def admin_approve(cls, callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """✅ Approve withdrawal"""
        if db.process_withdrawal(rid, admin_id, "approved"):
            TelegramAPI.answer_callback(callback["id"], "✅ Approved")
            
            # Notify user
            w = db.get_withdrawal(rid)
            if w:
                try:
                    TelegramAPI.send_message(
                        int(w["user_id"]),
                        f"✅ *Withdrawal Approved!*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {Utils.format_refi(w['amount'])}\n\n"
                        f"Your withdrawal has been approved."
                    )
                except:
                    pass
        cls.admin_pending(callback, chat_id, msg_id)
    
    @classmethod
    def admin_reject(cls, callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """❌ Reject withdrawal"""
        if db.process_withdrawal(rid, admin_id, "rejected"):
            TelegramAPI.answer_callback(callback["id"], "❌ Rejected")
            
            # Notify user
            w = db.get_withdrawal(rid)
            if w:
                try:
                    TelegramAPI.send_message(
                        int(w["user_id"]),
                        f"❌ *Withdrawal Rejected*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {Utils.format_refi(w['amount'])}\n\n"
                        f"The amount has been returned to your balance."
                    )
                except:
                    pass
        cls.admin_pending(callback, chat_id, msg_id)
    
    @classmethod
    def admin_search(cls, callback: dict, chat_id: int, msg_id: int):
        """🔍 Search user"""
        TelegramAPI.edit_message(chat_id, msg_id, "🔍 *Send User ID or @username:*")
        cls.user_states[callback["from"]["id"]] = {"action": "admin_search"}
    
    @classmethod
    def handle_admin_search(cls, text: str, admin_id: int, chat_id: int):
        """🔍 Process user search"""
        found = None
        if text.isdigit():
            found = db.get_user(int(text))
        else:
            username = text.lstrip('@').lower()
            found = db.get_user_by_username(username)
        
        if not found:
            TelegramAPI.send_message(chat_id, f"❌ User not found: {text}")
            return
        
        text = Messages.ADMIN_USER_INFO.format(
            user_id=found['id'],
            username=found.get('username', 'None'),
            first_name=found.get('first_name', 'Unknown'),
            last_name=found.get('last_name', ''),
            language=found.get('language', 'en'),
            joined_at=Utils.get_date(found.get('joined_at', 0)),
            last_active=Utils.get_date(found.get('last_active', 0)),
            balance=Utils.format_refi(found.get('balance', 0)),
            balance_usd=Utils.refi_to_usd(found.get('balance', 0)),
            total_earned=Utils.format_refi(found.get('total_earned', 0)),
            total_earned_usd=Utils.refi_to_usd(found.get('total_earned', 0)),
            total_withdrawn=Utils.format_refi(found.get('total_withdrawn', 0)),
            total_withdrawn_usd=Utils.refi_to_usd(found.get('total_withdrawn', 0)),
            pending_withdrawals=len(db.get_user_withdrawals(int(found['id']), "pending")),
            referrals_count=found.get('referrals_count', 0),
            referral_code=found.get('referral_code', ''),
            referred_by=found.get('referred_by', 'Direct'),
            referral_clicks=found.get('referral_clicks', 0),
            verified='✅' if found.get('verified') else '❌',
            wallet=found.get('wallet', 'Not set'),
            admin='✅' if found.get('is_admin') else '❌',
            banned='✅' if found.get('is_banned') else '❌'
        )
        TelegramAPI.send_message(chat_id, text, Keyboards.user_actions(int(found['id']), found.get('is_banned', False), found.get('is_admin', False)))
    
    @classmethod
    def admin_broadcast(cls, callback: dict, chat_id: int, msg_id: int):
        """📢 Broadcast message"""
        TelegramAPI.edit_message(chat_id, msg_id, 
            f"📢 *Broadcast*\n\nSend message to {len(db.data['users'])} users:")
        cls.user_states[callback["from"]["id"]] = {"action": "admin_broadcast"}
    
    @classmethod
    def handle_admin_broadcast(cls, text: str, admin_id: int, chat_id: int):
        """📢 Process broadcast"""
        TelegramAPI.send_message(chat_id, f"📢 Broadcasting to {len(db.data['users'])} users...")
        
        sent = 0
        failed = 0
        
        for uid in db.data["users"].keys():
            try:
                TelegramAPI.send_message(int(uid), text)
                sent += 1
                if sent % 10 == 0:
                    time.sleep(0.5)
            except:
                failed += 1
        
        TelegramAPI.send_message(chat_id,
            f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}",
            Keyboards.admin())
    
    @classmethod
    def admin_users(cls, callback: dict, chat_id: int, msg_id: int):
        """👥 Show users list"""
        users_list = sorted(db.data["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
        
        text = "👥 *Recent Users*\n\n"
        for u in users_list:
            name = u.get("first_name", "Unknown")
            username = f"@{u.get('username', '')}" if u.get('username') else "No username"
            verified = "✅" if u.get("verified") else "❌"
            joined = Utils.get_date(u.get("joined_at", 0)).split()[0]
            text += f"{verified} {name} {username} - {joined}\n"
        
        text += f"\n*Total: {len(db.data['users'])} users*"
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.admin())
    
    @classmethod
    def admin_logout(cls, callback: dict, admin_id: int, chat_id: int, msg_id: int):
        """🔒 Admin logout"""
        db.admin_logout(admin_id)
        TelegramAPI.answer_callback(callback["id"], "🔒 Logged out")
        
        user_data = db.get_user(admin_id)
        text = Messages.MAIN_MENU.format(
            balance=Utils.format_refi(user_data.get('balance', 0)),
            referrals=user_data.get('referrals_count', 0)
        )
        TelegramAPI.edit_message(chat_id, msg_id, text, Keyboards.main_menu(user_data))
    
    @classmethod
    def admin_user_action(cls, callback: dict, admin_id: int, chat_id: int, msg_id: int, action: str, target_id: int):
        """👤 Handle user management actions"""
        target_user = db.get_user(target_id)
        if not target_user:
            TelegramAPI.answer_callback(callback["id"], "❌ User not found")
            return
        
        if action == "ban":
            db.update_user(target_id, is_banned=True)
            message = f"✅ User {target_id} has been banned."
            logger.info(f"🔨 User {target_id} banned by {admin_id}")
        elif action == "unban":
            db.update_user(target_id, is_banned=False)
            message = f"✅ User {target_id} has been unbanned."
            logger.info(f"✅ User {target_id} unbanned by {admin_id}")
        elif action == "make_admin":
            db.update_user(target_id, is_admin=True)
            message = f"✅ User {target_id} is now an admin."
            logger.info(f"👑 User {target_id} made admin by {admin_id}")
        elif action == "remove_admin":
            db.update_user(target_id, is_admin=False)
            message = f"✅ User {target_id} is no longer an admin."
            logger.info(f"👤 User {target_id} removed from admin by {admin_id}")
        else:
            return
        
        TelegramAPI.answer_callback(callback["id"], message)
        
        # Refresh user info
        cls.handle_admin_search(str(target_id), admin_id, chat_id)
    
    # ==================== INPUT HANDLERS ====================
    
    @classmethod
    def handle_wallet(cls, text: str, user_id: int, chat_id: int):
        """✅ Save wallet address"""
        if not Utils.is_valid_wallet(text):
            TelegramAPI.send_message(chat_id, 
                "❌ *Invalid wallet address*\n\n"
                "Must start with 0x and be 42 characters long.\n"
                "Please try again.")
            return
        
        db.update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = db.get_user(user_id)
        
        TelegramAPI.send_message(chat_id,
            Messages.WALLET_SUCCESS.format(wallet=Utils.short_wallet(text)),
            Keyboards.main_menu(user_data))
        logger.info(f"👛 Wallet set for user {user_id}")
    
    @classmethod
    def handle_withdraw_amount(cls, text: str, user_id: int, chat_id: int):
        """✅ Process withdrawal amount"""
        try:
            amount = int(text.replace(',', '').strip())
        except ValueError:
            TelegramAPI.send_message(chat_id, "❌ Please enter a valid number.")
            return
        
        user_data = db.get_user(user_id)
        
        if amount < Config.MIN_WITHDRAW:
            TelegramAPI.send_message(chat_id, f"❌ Minimum amount is {Utils.format_refi(Config.MIN_WITHDRAW)}")
            return
        
        if amount > user_data.get("balance", 0):
            TelegramAPI.send_message(chat_id, f"❌ Insufficient balance. You have {Utils.format_refi(user_data.get('balance', 0))}")
            return
        
        # Check pending withdrawals
        pending = db.get_user_withdrawals(user_id, "pending")
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            TelegramAPI.send_message(chat_id, 
                f"❌ You already have {len(pending)} pending withdrawals.\n"
                f"Max allowed: {Config.MAX_PENDING_WITHDRAWALS}")
            return
        
        # Create withdrawal
        rid = db.create_withdrawal(user_id, amount, user_data["wallet"])
        db.update_user(user_id, balance=user_data["balance"] - amount)
        
        TelegramAPI.send_message(chat_id,
            Messages.WITHDRAW_SUCCESS.format(
                request_id=rid[:8],
                amount=Utils.format_refi(amount)
            ),
            Keyboards.main_menu(user_data))
        logger.info(f"💰 Withdrawal created: {rid} for {amount} REFi")
        
        # Notify admins
        for admin_id in Config.ADMIN_IDS:
            try:
                TelegramAPI.send_message(admin_id,
                    f"💰 *New Withdrawal Request*\n\n"
                    f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                    f"ID: `{user_id}`\n"
                    f"Amount: {Utils.format_refi(amount)}\n"
                    f"Wallet: {user_data['wallet']}\n\n"
                    f"Request ID: `{rid}`")
            except:
                pass

# ==================== WEB SERVER ====================

class HealthHandler(BaseHTTPRequestHandler):
    """🏥 Health check handler"""
    
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
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            min-height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .container {{
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            padding: 2rem;
            border-radius: 20px;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        h1 {{ font-size: 2.5rem; margin-bottom: 1rem; }}
        .status {{
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 50px;
            background: rgba(0, 255, 0, 0.2);
            border: 1px solid rgba(0, 255, 0, 0.5);
            margin: 1rem 0;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 1rem;
            margin-top: 2rem;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.1);
            padding: 1rem;
            border-radius: 10px;
        }}
        .stat-value {{ font-size: 1.5rem; font-weight: bold; }}
        .stat-label {{ font-size: 0.9rem; opacity: 0.8; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 REFi Bot</h1>
        <div class="status">🟢 ONLINE</div>
        <p>@{Config.BOT_USERNAME}</p>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-value">{stats['total_users']}</div>
                <div class="stat-label">Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['verified']}</div>
                <div class="stat-label">Verified</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats['pending_withdrawals']}</div>
                <div class="stat-label">Pending</div>
            </div>
        </div>
        
        <p style="margin-top: 2rem; font-size: 0.8rem; opacity: 0.5;">
            Uptime: {hours}h {minutes}m | {Utils.get_date()}
        </p>
    </div>
</body>
</html>"""
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        return

def run_web_server():
    """🌐 Run web server"""
    server = HTTPServer(('0.0.0.0', Config.PORT), HealthHandler)
    logger.info(f"🌐 Web server running on port {Config.PORT}")
    server.serve_forever()

# Start web server in background thread
web_thread = threading.Thread(target=run_web_server, daemon=True)
web_thread.start()
logger.info("🌐 Web server thread started")

# ==================== MAIN POLLING LOOP ====================

offset = 0
bot_running = True

def main():
    """🚀 Main polling loop"""
    global offset, bot_running
    
    print("\n" + "="*80)
    print("🤖 REFi BOT - PROFESSIONAL COMPLETE EDITION v12.0.0")
    print("="*80)
    print(f"📱 Bot: @{Config.BOT_USERNAME}")
    print(f"👤 Admins: {Config.ADMIN_IDS}")
    print(f"💰 Welcome Bonus: {Utils.format_refi(Config.WELCOME_BONUS)}")
    print(f"👥 Referral Bonus: {Utils.format_refi(Config.REFERRAL_BONUS)}")
    print(f"💸 Minimum Withdraw: {Utils.format_refi(Config.MIN_WITHDRAW)}")
    print(f"👥 Users in Database: {len(db.data['users'])}")
    print(f"🌐 Web Server Port: {Config.PORT}")
    print("="*80 + "\n")
    
    logger.info("🚀 Starting bot polling...")
    
    while bot_running:
        try:
            response = http_session.post(
                f"{Config.API_URL}/getUpdates",
                json={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message", "callback_query"]
                },
                timeout=35
            )
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    update_id = update["update_id"]
                    
                    # Process messages
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        text = msg.get("text", "")
                        
                        # Check if user is banned
                        user_data = db.get_user(user_id)
                        if user_data.get("is_banned"):
                            TelegramAPI.send_message(chat_id, "⛔ You are banned from using this bot.")
                            offset = update_id + 1
                            continue
                        
                        # Handle commands
                        if text == "/start":
                            Handlers.start(msg)
                        elif text == "/admin":
                            Handlers.admin_login(msg)
                        elif text.startswith("/"):
                            TelegramAPI.send_message(chat_id, "❌ Unknown command. Use /start")
                        else:
                            # Handle state-based input
                            state = Handlers.user_states.get(user_id, {}).get("action")
                            if state == "wallet":
                                Handlers.handle_wallet(text, user_id, chat_id)
                                Handlers.user_states.pop(user_id, None)
                            elif state == "withdraw_amount":
                                Handlers.handle_withdraw_amount(text, user_id, chat_id)
                                Handlers.user_states.pop(user_id, None)
                            elif state == "admin_login":
                                Handlers.handle_admin_login(text, user_id, chat_id)
                                Handlers.user_states.pop(user_id, None)
                            elif state == "admin_search":
                                Handlers.handle_admin_search(text, user_id, chat_id)
                                Handlers.user_states.pop(user_id, None)
                            elif state == "admin_broadcast":
                                Handlers.handle_admin_broadcast(text, user_id, chat_id)
                                Handlers.user_states.pop(user_id, None)
                    
                    # Process callback queries
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        data = cb.get("data", "")
                        user_id = cb["from"]["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        msg_id = cb["message"]["message_id"]
                        
                        TelegramAPI.answer_callback(cb["id"])
                        
                        # User callbacks
                        if data == "verify":
                            Handlers.verify(cb, user_id, chat_id, msg_id)
                        elif data == "back":
                            Handlers.back(cb, user_id, chat_id, msg_id)
                        elif data == "balance":
                            Handlers.balance(cb, user_id, chat_id, msg_id)
                        elif data == "referral":
                            Handlers.referral(cb, user_id, chat_id, msg_id)
                        elif data == "stats":
                            Handlers.stats(cb, user_id, chat_id, msg_id)
                        elif data == "withdraw":
                            Handlers.withdraw(cb, user_id, chat_id, msg_id)
                        elif data == "set_wallet":
                            Handlers.set_wallet(cb, user_id, chat_id, msg_id)
                        elif data == "admin_panel":
                            Handlers.admin_panel(cb, user_id, chat_id, msg_id)
                        
                        # Admin callbacks
                        elif data == "admin_stats":
                            Handlers.admin_stats(cb, chat_id, msg_id)
                        elif data == "admin_pending":
                            Handlers.admin_pending(cb, chat_id, msg_id)
                        elif data == "admin_search":
                            Handlers.admin_search(cb, chat_id, msg_id)
                        elif data == "admin_broadcast":
                            Handlers.admin_broadcast(cb, chat_id, msg_id)
                        elif data == "admin_users":
                            Handlers.admin_users(cb, chat_id, msg_id)
                        elif data == "admin_logout":
                            Handlers.admin_logout(cb, user_id, chat_id, msg_id)
                        elif data.startswith("process_"):
                            rid = data[8:]
                            Handlers.admin_process(cb, chat_id, msg_id, rid)
                        elif data.startswith("approve_"):
                            rid = data[8:]
                            Handlers.admin_approve(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("reject_"):
                            rid = data[7:]
                            Handlers.admin_reject(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("ban_"):
                            target_id = int(data[4:])
                            Handlers.admin_user_action(cb, user_id, chat_id, msg_id, "ban", target_id)
                        elif data.startswith("unban_"):
                            target_id = int(data[6:])
                            Handlers.admin_user_action(cb, user_id, chat_id, msg_id, "unban", target_id)
                        elif data.startswith("make_admin_"):
                            target_id = int(data[11:])
                            Handlers.admin_user_action(cb, user_id, chat_id, msg_id, "make_admin", target_id)
                        elif data.startswith("remove_admin_"):
                            target_id = int(data[13:])
                            Handlers.admin_user_action(cb, user_id, chat_id, msg_id, "remove_admin", target_id)
                    
                    offset = update_id + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

# ==================== SIGNAL HANDLERS ====================

def signal_handler(sig, frame):
    """Handle shutdown signals"""
    global bot_running
    logger.info("🛑 Shutting down bot...")
    bot_running = False
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# ==================== ENTRY POINT ====================

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        bot_running = False
    except Exception as e:
        logger.exception("❌ Fatal error")
        print(f"\n❌ Fatal error: {e}")

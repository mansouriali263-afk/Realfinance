#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - PROFESSIONAL EDITION v7.0.0                                    ║
║     Telegram Referral & Earn Bot with Bottom Navigation                          ║
║     Python: 3.14.3 | Platform: Render/Koyeb/Railway                              ║
║                                                                                  ║
║     Features:                                                                    ║
║     • Channel verification with floating buttons                                 ║
║     • Bottom navigation menu after verification                                  ║
║     • Referral system with unique codes                                          ║
║     • Balance with USD conversion (1M REFi = $2)                                 ║
║     • Withdrawal system with wallet validation                                   ║
║     • Complete admin panel with statistics                                       ║
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
from typing import Dict, Optional, List, Any, Tuple
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==================== REQUESTS SETUP ====================
try:
    import requests
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError:
    print("📦 Installing requests...")
    os.system("pip install requests==2.31.0")
    import requests

# ==================== CONFIGURATION ====================

class Config:
    """🎯 Professional Configuration Management"""
    
    # Bot Core
    BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
    BOT_USERNAME = "Realfinancepaybot"
    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    # Admin
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
    
    # Limits
    MAX_PENDING_WITHDRAWALS = 3
    SESSION_TIMEOUT = 3600  # 1 hour
    REQUEST_TIMEOUT = 15
    MAX_RETRIES = 3
    HEALTH_CHECK_PORT = int(os.environ.get('PORT', 10000))
    
    # Database
    DB_FILE = "bot_data.json"

# ==================== LOGGING ====================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ==================== HEALTH CHECK SERVER ====================

class HealthCheckHandler(BaseHTTPRequestHandler):
    """🏥 Health check server for Render"""
    
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        
        stats = db.get_stats() if 'db' in globals() else {}
        
        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>🤖 REFi Bot Status</title>
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
                <div class="stat-value">{stats.get('total_users', 0)}</div>
                <div class="stat-label">Users</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('verified', 0)}</div>
                <div class="stat-label">Verified</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">{stats.get('pending_withdrawals', 0)}</div>
                <div class="stat-label">Pending</div>
            </div>
        </div>
        
        <p style="margin-top: 2rem; font-size: 0.8rem; opacity: 0.5;">
            {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
        </p>
    </div>
</body>
</html>"""
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        return

# Start health server in background thread
def run_health_server():
    try:
        server = HTTPServer(('0.0.0.0', Config.HEALTH_CHECK_PORT), HealthCheckHandler)
        logger.info(f"🏥 Health check server running on port {Config.HEALTH_CHECK_PORT}")
        server.serve_forever()
    except Exception as e:
        logger.error(f"❌ Health server error: {e}")

threading.Thread(target=run_health_server, daemon=True).start()
logger.info("🏥 Health check server started")

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
                    "last_withdrawal_date": None
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
                "tx_hash": None
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
        
        return {
            "total_users": len(users),
            "verified": sum(1 for u in users if u.get("verified")),
            "banned": sum(1 for u in users if u.get("is_banned")),
            "active_today": sum(1 for u in users if u.get("last_active", 0) > now - 86400),
            "active_week": sum(1 for u in users if u.get("last_active", 0) > now - 604800),
            "total_balance": sum(u.get("balance", 0) for u in users),
            "total_earned": sum(u.get("total_earned", 0) for u in users),
            "total_withdrawn": self.data["stats"].get("total_withdrawn", 0),
            "pending_withdrawals": len(self.get_pending_withdrawals()),
            "total_referrals": self.data["stats"].get("total_referrals", 0),
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

# ==================== BOTTOM NAVIGATION ====================

class BottomNavigation:
    """🎯 Professional Bottom Navigation System"""
    
    @staticmethod
    def channels() -> dict:
        """📢 Channel verification as floating buttons"""
        keyboard = []
        for ch in Config.REQUIRED_CHANNELS:
            keyboard.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
        keyboard.append([{"text": "✅ VERIFY NOW", "callback_data": "verify"}])
        return {"inline_keyboard": keyboard}
    
    @staticmethod
    def main_menu(user: dict) -> dict:
        """🎯 Main menu with bottom navigation"""
        keyboard = [
            [   # Row 1
                {"text": "💰 Balance", "callback_data": "menu_balance"},
                {"text": "🔗 Referral", "callback_data": "menu_referral"}
            ],
            [   # Row 2
                {"text": "💸 Withdraw", "callback_data": "menu_withdraw"},
                {"text": "📊 Stats", "callback_data": "menu_stats"}
            ]
        ]
        
        # Row 3: Conditional buttons
        row3 = []
        if not user.get("wallet"):
            row3.append({"text": "👛 Set Wallet", "callback_data": "menu_wallet"})
        if user.get("is_admin") and user.get("wallet"):
            row3.append({"text": "👑 Admin", "callback_data": "menu_admin"})
        if row3:
            keyboard.append(row3)
        
        return {"inline_keyboard": keyboard}
    
    @staticmethod
    def back() -> dict:
        """🔙 Back button only"""
        return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "menu_back"}]]}
    
    @staticmethod
    def admin() -> dict:
        """👑 Admin panel"""
        return {"inline_keyboard": [
            [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
            [{"text": "💰 Pending Withdrawals", "callback_data": "admin_pending"}],
            [{"text": "🔍 Search User", "callback_data": "admin_search"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
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

# ==================== TELEGRAM API ====================

class Telegram:
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
            return data.get("result") if data.get("ok") else None
        except Exception as e:
            logger.error(f"❌ Telegram API error: {e}")
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

# ==================== HANDLERS ====================

class Handlers:
    """🎯 Professional Handlers"""
    
    @staticmethod
    def start(message: dict):
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
        
        # Get/create user
        user_data = db.get_user(user_id)
        db.update_user(user_id, 
                      username=user.get("username", ""),
                      first_name=user.get("first_name", ""))
        
        # Show main menu if verified
        if user_data.get("verified"):
            text = f"🎯 *Main Menu*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
            Telegram.send_message(chat_id, text, BottomNavigation.main_menu(user_data))
            return
        
        # Show channel verification
        channels = "\n".join([f"• {ch['name']}" for ch in Config.REQUIRED_CHANNELS])
        text = (
            f"🎉 *Welcome to REFi Bot!*\n\n"
            f"💰 Welcome Bonus: {Utils.format_refi(Config.WELCOME_BONUS)}\n"
            f"👥 Referral Bonus: {Utils.format_refi(Config.REFERRAL_BONUS)} per friend\n\n"
            f"📢 *To start, you must join these channels:*\n{channels}\n\n"
            f"👇 Click VERIFY after joining"
        )
        Telegram.send_message(chat_id, text, BottomNavigation.channels())
    
    @staticmethod
    def verify(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """✅ Verify membership"""
        # Check channels
        not_joined = []
        for ch in Config.REQUIRED_CHANNELS:
            status = Telegram.get_chat_member(ch["username"], user_id)
            if status not in ["member", "administrator", "creator"]:
                not_joined.append(ch["name"])
        
        if not_joined:
            text = "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.channels())
            return
        
        # Verify user
        user_data = db.get_user(user_id)
        
        if user_data.get("verified"):
            text = f"✅ Already verified!\n\n{Utils.format_refi(user_data.get('balance', 0))}"
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
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
                    Telegram.send_message(
                        int(user_data["referred_by"]),
                        f"🎉 *Friend Joined!*\n\n"
                        f"{user_data.get('first_name', 'Someone')} joined using your link!\n"
                        f"✨ You earned {Utils.format_refi(Config.REFERRAL_BONUS)}"
                    )
                except:
                    pass
        
        text = (
            f"✅ *Verification Successful!*\n\n"
            f"✨ Added {Utils.format_refi(Config.WELCOME_BONUS)} to your balance\n"
            f"💰 Current: {Utils.format_refi(new_balance)}\n\n"
            f"👇 Use the buttons below to navigate"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
        logger.info(f"✅ User {user_id} verified")
    
    @staticmethod
    def menu_balance(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💰 Balance"""
        user_data = db.get_user(user_id)
        text = (
            f"💰 *Your Balance*\n\n"
            f"• {Utils.format_refi(user_data.get('balance', 0))}\n"
            f"• Total earned: {Utils.format_refi(user_data.get('total_earned', 0))}\n"
            f"• Total withdrawn: {Utils.format_refi(user_data.get('total_withdrawn', 0))}\n"
            f"• Referrals: {user_data.get('referrals_count', 0)}"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_referral(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔗 Referral"""
        user_data = db.get_user(user_id)
        link = f"https://t.me/{Config.BOT_USERNAME}?start={user_data.get('referral_code', '')}"
        earned = user_data.get('referrals_count', 0) * Config.REFERRAL_BONUS
        
        text = (
            f"🔗 *Your Referral Link*\n\n"
            f"`{link}`\n\n"
            f"🎁 *Rewards*\n"
            f"• You earn: {Utils.format_refi(Config.REFERRAL_BONUS)} per friend\n"
            f"• Friend gets: {Utils.format_refi(Config.WELCOME_BONUS)}\n\n"
            f"📊 *Stats*\n"
            f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
            f"• Successful: {user_data.get('referrals_count', 0)}\n"
            f"• Earned: {Utils.format_refi(earned)}"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_stats(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """📊 Stats"""
        user_data = db.get_user(user_id)
        joined = datetime.fromtimestamp(user_data.get("joined_at", 0)).strftime("%Y-%m-%d %H:%M")
        
        text = (
            f"📊 *Your Statistics*\n\n"
            f"👤 *User Info*\n"
            f"• ID: `{user_id}`\n"
            f"• Joined: {joined}\n\n"
            f"💰 *Financial*\n"
            f"• Balance: {Utils.format_refi(user_data.get('balance', 0))}\n"
            f"• Total earned: {Utils.format_refi(user_data.get('total_earned', 0))}\n"
            f"• Withdrawn: {Utils.format_refi(user_data.get('total_withdrawn', 0))}\n\n"
            f"👥 *Referrals*\n"
            f"• Count: {user_data.get('referrals_count', 0)}\n"
            f"• Clicks: {user_data.get('referral_clicks', 0)}\n\n"
            f"✅ *Status*\n"
            f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
            f"• Wallet: {Utils.short_wallet(user_data.get('wallet', ''))}"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_withdraw(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💸 Withdraw"""
        user_data = db.get_user(user_id)
        
        if not user_data.get("verified"):
            text = "❌ *You must verify first!*\n\nSend /start to begin."
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
            return
        
        if not user_data.get("wallet"):
            text = (
                "⚠️ *You need to set a wallet first!*\n\n"
                "Please use the 👛 Set Wallet button to add your wallet address."
            )
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
            return
        
        balance = user_data.get("balance", 0)
        if balance < Config.MIN_WITHDRAW:
            needed = Config.MIN_WITHDRAW - balance
            text = (
                f"⚠️ *Minimum withdrawal: {Utils.format_refi(Config.MIN_WITHDRAW)}*\n"
                f"Your balance: {Utils.format_refi(balance)}\n\n"
                f"You need {Utils.format_refi(needed)} more to withdraw."
            )
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
            return
        
        # Check pending withdrawals
        pending = db.get_user_withdrawals(user_id, "pending")
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            text = f"⚠️ You have {len(pending)} pending withdrawals.\nMax allowed: {Config.MAX_PENDING_WITHDRAWALS}"
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
            return
        
        text = (
            f"💸 *Withdraw*\n\n"
            f"Balance: {Utils.format_refi(balance)}\n"
            f"Minimum: {Utils.format_refi(Config.MIN_WITHDRAW)}\n"
            f"Wallet: {Utils.short_wallet(user_data['wallet'])}\n\n"
            f"Send the amount you want to withdraw:"
        )
        Telegram.edit_message(chat_id, msg_id, text)
        
        # Set state
        global user_states
        user_states[user_id] = {"action": "withdraw_amount"}
    
    @staticmethod
    def menu_wallet(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """👛 Set wallet"""
        user_data = db.get_user(user_id)
        text = (
            f"👛 *Set Withdrawal Wallet*\n\n"
            f"Current wallet: {user_data.get('wallet', 'Not set')}\n\n"
            f"Please enter your Ethereum wallet address.\n"
            f"It must start with `0x` and be 42 characters long.\n\n"
            f"Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
        )
        Telegram.edit_message(chat_id, msg_id, text)
        
        # Set state
        global user_states
        user_states[user_id] = {"action": "wallet"}
    
    @staticmethod
    def menu_back(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔙 Back to main menu"""
        user_data = db.get_user(user_id)
        text = f"🎯 *Main Menu*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def menu_admin(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """👑 Admin panel access"""
        if user_id not in Config.ADMIN_IDS:
            Telegram.answer_callback(callback["id"], "⛔ Unauthorized")
            return
        
        if not db.is_admin_logged_in(user_id):
            text = "🔐 *Please login first*\n\nUse /admin command to login."
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(db.get_user(user_id)))
            return
        
        stats = db.get_stats()
        h = stats['uptime'] // 3600
        m = (stats['uptime'] % 3600) // 60
        
        text = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
            f"• Uptime: {h}h {m}m"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.admin())
    
    # ==================== ADMIN HANDLERS ====================
    
    @staticmethod
    def admin_login(message: dict):
        """👑 Admin login command"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if user_id not in Config.ADMIN_IDS:
            Telegram.send_message(chat_id, "⛔ Unauthorized")
            return
        
        if db.is_admin_logged_in(user_id):
            stats = db.get_stats()
            h = stats['uptime'] // 3600
            m = (stats['uptime'] % 3600) // 60
            text = (
                f"👑 *Admin Panel*\n\n"
                f"📊 *Statistics*\n"
                f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
                f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
                f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
                f"• Uptime: {h}h {m}m"
            )
            Telegram.send_message(chat_id, text, BottomNavigation.admin())
            return
        
        Telegram.send_message(chat_id, "🔐 *Admin Login*\n\nPlease enter password:")
        global user_states
        user_states[user_id] = {"action": "admin_login"}
    
    @staticmethod
    def handle_admin_login(text: str, user_id: int, chat_id: int):
        """✅ Process admin login"""
        if text == Config.ADMIN_PASSWORD:
            db.admin_login(user_id)
            Telegram.send_message(chat_id, "✅ Login successful!")
            
            stats = db.get_stats()
            h = stats['uptime'] // 3600
            m = (stats['uptime'] % 3600) // 60
            text = (
                f"👑 *Admin Panel*\n\n"
                f"📊 *Statistics*\n"
                f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
                f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
                f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
                f"• Uptime: {h}h {m}m"
            )
            Telegram.send_message(chat_id, text, BottomNavigation.admin())
        else:
            Telegram.send_message(chat_id, "❌ Wrong password!")
    
    @staticmethod
    def admin_stats(callback: dict, chat_id: int, msg_id: int):
        """📊 Show detailed statistics"""
        stats = db.get_stats()
        now = time.time()
        
        h = stats['uptime'] // 3600
        m = (stats['uptime'] % 3600) // 60
        
        text = (
            f"📊 *Detailed Statistics*\n\n"
            f"👥 *Users*\n"
            f"• Total: {stats['total_users']}\n"
            f"• Verified: {stats['verified']}\n"
            f"• Banned: {stats['banned']}\n"
            f"• Active today: {stats['active_today']}\n"
            f"• Active week: {stats['active_week']}\n\n"
            f"💰 *Financial*\n"
            f"• Total balance: {Utils.format_refi(stats['total_balance'])}\n"
            f"• Total earned: {Utils.format_refi(stats['total_earned'])}\n"
            f"• Total withdrawn: {Utils.format_refi(stats['total_withdrawn'])}\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n\n"
            f"📈 *Referrals*\n"
            f"• Total: {stats['total_referrals']}\n\n"
            f"⏱️ *Uptime: {h}h {m}m*"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.admin())
    
    @staticmethod
    def admin_pending(callback: dict, chat_id: int, msg_id: int):
        """💰 Show pending withdrawals"""
        pending = db.get_pending_withdrawals()
        
        if not pending:
            Telegram.edit_message(chat_id, msg_id, "✅ No pending withdrawals", BottomNavigation.admin())
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
                {"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}
            ])
        
        if len(pending) > 5:
            text += f"*... and {len(pending) - 5} more*\n\n"
        
        keyboard["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin_back"}])
        Telegram.edit_message(chat_id, msg_id, text, keyboard)
    
    @staticmethod
    def admin_process(callback: dict, chat_id: int, msg_id: int, rid: str):
        """⚙️ Process withdrawal"""
        w = db.get_withdrawal(rid)
        if not w:
            Telegram.answer_callback(callback["id"], "❌ Not found")
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
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.withdrawal_actions(rid))
    
    @staticmethod
    def admin_approve(callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """✅ Approve withdrawal"""
        if db.process_withdrawal(rid, admin_id, "approved"):
            Telegram.answer_callback(callback["id"], "✅ Approved")
            
            # Notify user
            w = db.get_withdrawal(rid)
            if w:
                try:
                    Telegram.send_message(
                        int(w["user_id"]),
                        f"✅ *Withdrawal Approved!*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {Utils.format_refi(w['amount'])}\n\n"
                        f"Your withdrawal has been approved."
                    )
                except:
                    pass
        Handlers.admin_pending(callback, chat_id, msg_id)
    
    @staticmethod
    def admin_reject(callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """❌ Reject withdrawal"""
        if db.process_withdrawal(rid, admin_id, "rejected"):
            Telegram.answer_callback(callback["id"], "❌ Rejected")
            
            # Notify user
            w = db.get_withdrawal(rid)
            if w:
                try:
                    Telegram.send_message(
                        int(w["user_id"]),
                        f"❌ *Withdrawal Rejected*\n\n"
                        f"Request: `{rid[:8]}...`\n"
                        f"Amount: {Utils.format_refi(w['amount'])}\n\n"
                        f"The amount has been returned to your balance."
                    )
                except:
                    pass
        Handlers.admin_pending(callback, chat_id, msg_id)
    
    @staticmethod
    def admin_search(callback: dict, chat_id: int, msg_id: int):
        """🔍 Search user"""
        Telegram.edit_message(chat_id, msg_id, "🔍 *Send User ID or @username:*")
        global user_states
        user_states[callback["from"]["id"]] = {"action": "admin_search"}
    
    @staticmethod
    def handle_admin_search(text: str, admin_id: int, chat_id: int):
        """🔍 Process user search"""
        found = None
        if text.isdigit():
            found = db.get_user(int(text))
        else:
            username = text.lstrip('@').lower()
            found = db.get_user_by_username(username)
        
        if not found:
            Telegram.send_message(chat_id, f"❌ User not found: {text}")
            return
        
        stats = db.get_stats()
        text = (
            f"👤 *User Found*\n\n"
            f"ID: `{found['id']}`\n"
            f"Username: @{found.get('username', 'None')}\n"
            f"Name: {found.get('first_name', 'Unknown')}\n"
            f"Balance: {Utils.format_refi(found.get('balance', 0))}\n"
            f"Referrals: {found.get('referrals_count', 0)}\n"
            f"Verified: {'✅' if found.get('verified') else '❌'}\n"
            f"Wallet: {Utils.short_wallet(found.get('wallet', ''))}"
        )
        Telegram.send_message(chat_id, text, BottomNavigation.admin())
    
    @staticmethod
    def admin_broadcast(callback: dict, chat_id: int, msg_id: int):
        """📢 Broadcast message"""
        Telegram.edit_message(chat_id, msg_id, 
            f"📢 *Broadcast*\n\nSend message to {len(db.data['users'])} users:")
        global user_states
        user_states[callback["from"]["id"]] = {"action": "admin_broadcast"}
    
    @staticmethod
    def handle_admin_broadcast(text: str, admin_id: int, chat_id: int):
        """📢 Process broadcast"""
        status_msg = Telegram.send_message(chat_id, "📢 Broadcasting...")
        
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
        
        Telegram.send_message(chat_id,
            f"✅ *Broadcast Complete*\n\nSent: {sent}\nFailed: {failed}",
            BottomNavigation.admin())
    
    @staticmethod
    def admin_logout(callback: dict, admin_id: int, chat_id: int, msg_id: int):
        """🔒 Admin logout"""
        db.admin_logout(admin_id)
        Telegram.answer_callback(callback["id"], "🔒 Logged out")
        
        user_data = db.get_user(admin_id)
        text = f"🔒 *Logged out*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def admin_back(callback: dict, chat_id: int, msg_id: int):
        """🔙 Back to admin panel"""
        stats = db.get_stats()
        h = stats['uptime'] // 3600
        m = (stats['uptime'] % 3600) // 60
        
        text = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {Utils.format_refi(stats['total_balance'])}\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
            f"• Uptime: {h}h {m}m"
        )
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.admin())
    
    # ==================== INPUT HANDLERS ====================
    
    @staticmethod
    def handle_wallet(text: str, user_id: int, chat_id: int):
        """✅ Save wallet address"""
        if not Utils.is_valid_wallet(text):
            Telegram.send_message(chat_id, 
                "❌ *Invalid wallet address*\n\n"
                "Must start with 0x and be 42 characters long.\n"
                "Please try again.")
            return
        
        db.update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = db.get_user(user_id)
        
        Telegram.send_message(chat_id,
            f"✅ *Wallet saved successfully!*\n\n"
            f"Wallet: {Utils.short_wallet(text)}",
            BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def handle_withdraw_amount(text: str, user_id: int, chat_id: int):
        """✅ Process withdrawal amount"""
        try:
            amount = int(text.replace(',', '').strip())
        except ValueError:
            Telegram.send_message(chat_id, "❌ Please enter a valid number.")
            return
        
        user_data = db.get_user(user_id)
        
        if amount < Config.MIN_WITHDRAW:
            Telegram.send_message(chat_id, f"❌ Minimum amount is {Utils.format_refi(Config.MIN_WITHDRAW)}")
            return
        
        if amount > user_data.get("balance", 0):
            Telegram.send_message(chat_id, f"❌ Insufficient balance. You have {Utils.format_refi(user_data.get('balance', 0))}")
            return
        
        # Create withdrawal
        rid = db.create_withdrawal(user_id, amount, user_data["wallet"])
        db.update_user(user_id, balance=user_data["balance"] - amount)
        
        Telegram.send_message(chat_id,
            f"✅ *Withdrawal Request Submitted!*\n\n"
            f"📝 Request ID: `{rid[:8]}...`\n"
            f"💰 Amount: {Utils.format_refi(amount)}\n\n"
            f"⏳ Status: *Pending Review*",
            BottomNavigation.main_menu(user_data))
        
        # Notify admins
        for admin_id in Config.ADMIN_IDS:
            try:
                Telegram.send_message(admin_id,
                    f"💰 *New Withdrawal Request*\n\n"
                    f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                    f"ID: `{user_id}`\n"
                    f"Amount: {Utils.format_refi(amount)}\n"
                    f"Wallet: {user_data['wallet']}\n\n"
                    f"Request ID: `{rid}`")
            except:
                pass

# ==================== MAIN POLLING LOOP ====================

user_states = {}
offset = 0

def main():
    """🚀 Main polling loop"""
    global offset
    
    print("\n" + "="*70)
    print("🤖 REFi BOT - PROFESSIONAL EDITION v7.0.0")
    print("="*70)
    print(f"📱 Bot: @{Config.BOT_USERNAME}")
    print(f"👤 Admins: {Config.ADMIN_IDS}")
    print(f"💰 Welcome: {Utils.format_refi(Config.WELCOME_BONUS)}")
    print(f"👥 Referral: {Utils.format_refi(Config.REFERRAL_BONUS)}")
    print(f"💸 Min Withdraw: {Utils.format_refi(Config.MIN_WITHDRAW)}")
    print(f"👥 Users in DB: {len(db.data['users'])}")
    print(f"🏥 Health: http://0.0.0.0:{Config.HEALTH_CHECK_PORT}")
    print("="*70 + "\n")
    
    while True:
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
                            Telegram.send_message(chat_id, "⛔ You are banned from using this bot.")
                            offset = update_id + 1
                            continue
                        
                        # Handle commands
                        if text == "/start":
                            Handlers.start(msg)
                        elif text == "/admin":
                            Handlers.admin_login(msg)
                        elif text.startswith("/"):
                            Telegram.send_message(chat_id, "❌ Unknown command. Use /start")
                        else:
                            # Handle state-based input
                            state = user_states.get(user_id, {}).get("action")
                            if state == "wallet":
                                Handlers.handle_wallet(text, user_id, chat_id)
                                user_states.pop(user_id, None)
                            elif state == "withdraw_amount":
                                Handlers.handle_withdraw_amount(text, user_id, chat_id)
                                user_states.pop(user_id, None)
                            elif state == "admin_login":
                                Handlers.handle_admin_login(text, user_id, chat_id)
                                user_states.pop(user_id, None)
                            elif state == "admin_search":
                                Handlers.handle_admin_search(text, user_id, chat_id)
                                user_states.pop(user_id, None)
                            elif state == "admin_broadcast":
                                Handlers.handle_admin_broadcast(text, user_id, chat_id)
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
                            Handlers.verify(cb, user_id, chat_id, msg_id)
                        elif data == "menu_back":
                            Handlers.menu_back(cb, user_id, chat_id, msg_id)
                        elif data == "menu_balance":
                            Handlers.menu_balance(cb, user_id, chat_id, msg_id)
                        elif data == "menu_referral":
                            Handlers.menu_referral(cb, user_id, chat_id, msg_id)
                        elif data == "menu_stats":
                            Handlers.menu_stats(cb, user_id, chat_id, msg_id)
                        elif data == "menu_withdraw":
                            Handlers.menu_withdraw(cb, user_id, chat_id, msg_id)
                        elif data == "menu_wallet":
                            Handlers.menu_wallet(cb, user_id, chat_id, msg_id)
                        elif data == "menu_admin":
                            Handlers.menu_admin(cb, user_id, chat_id, msg_id)
                        
                        # Admin callbacks
                        elif data == "admin_stats":
                            Handlers.admin_stats(cb, chat_id, msg_id)
                        elif data == "admin_pending":
                            Handlers.admin_pending(cb, chat_id, msg_id)
                        elif data == "admin_search":
                            Handlers.admin_search(cb, chat_id, msg_id)
                        elif data == "admin_broadcast":
                            Handlers.admin_broadcast(cb, chat_id, msg_id)
                        elif data == "admin_logout":
                            Handlers.admin_logout(cb, user_id, chat_id, msg_id)
                        elif data == "admin_back":
                            Handlers.admin_back(cb, chat_id, msg_id)
                        elif data.startswith("process_"):
                            rid = data[8:]
                            Handlers.admin_process(cb, chat_id, msg_id, rid)
                        elif data.startswith("approve_"):
                            rid = data[8:]
                            Handlers.admin_approve(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("reject_"):
                            rid = data[7:]
                            Handlers.admin_reject(cb, user_id, chat_id, msg_id, rid)
                    
                    offset = update_id + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

# ==================== ENTRY POINT ====================

# For Gunicorn compatibility
app = None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.exception("❌ Fatal error")
        print(f"\n❌ Fatal error: {e}")

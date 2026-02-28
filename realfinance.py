#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔═══════════════════════════════════════════════════════════════╗
║     🤖 REFi BOT - PROFESSIONAL EDITION v6.0.0                 ║
║     Telegram Referral & Earn Bot with Bottom Navigation       ║
║     Python: 3.14.3 | Platform: Render/Koyeb/Railway           ║
╚═══════════════════════════════════════════════════════════════╝
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
from typing import Dict, Optional, List, Any
from http.server import HTTPServer, BaseHTTPRequestHandler

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
    BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
    BOT_USERNAME = "Realfinancepaybot"
    API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
    
    # Admin
    ADMIN_IDS = [1653918641]
    ADMIN_PASSWORD = "Ali97$"
    
    # Tokenomics
    COIN_NAME = "REFi"
    WELCOME_BONUS = 1_000_000
    REFERRAL_BONUS = 1_000_000
    MIN_WITHDRAW = 5_000_000
    REFI_PER_MILLION = 2.0
    
    # Channels
    REQUIRED_CHANNELS = [
        {"name": "REFi Distribution", "username": "@Realfinance_REFI", 
         "link": "https://t.me/Realfinance_REFI"},
        {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", 
         "link": "https://t.me/Airdrop_MasterVIP"},
        {"name": "Daily Airdrop", "username": "@Daily_AirdropX", 
         "link": "https://t.me/Daily_AirdropX"}
    ]
    
    # Limits
    MAX_PENDING_WITHDRAWALS = 3
    SESSION_TIMEOUT = 3600
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
<head><title>REFi Bot</title>
<style>
body {{ font-family: -apple-system, BlinkMacSystemFont, sans-serif; 
       background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
       color: white; min-height: 100vh; margin: 0; 
       display: flex; justify-content: center; align-items: center; }}
.container {{ text-align: center; background: rgba(255,255,255,0.1); 
            backdrop-filter: blur(10px); padding: 2rem; border-radius: 20px; }}
.status {{ display: inline-block; padding: 0.5rem 1rem; 
           background: rgba(0,255,0,0.2); border-radius: 50px; }}
</style></head>
<body>
<div class="container">
    <h1>🤖 REFi Bot</h1>
    <div class="status">🟢 ONLINE</div>
    <p>@{Config.BOT_USERNAME}</p>
    <p>Users: {stats.get('total_users', 0)} | Verified: {stats.get('verified', 0)}</p>
</div>
</body>
</html>"""
        
        self.wfile.write(html.encode('utf-8'))
    
    def log_message(self, format, *args):
        return

# Start health server
threading.Thread(target=lambda: HTTPServer(
    ('0.0.0.0', Config.HEALTH_CHECK_PORT), HealthCheckHandler
).serve_forever(), daemon=True).start()
logger.info(f"🏥 Health server on port {Config.HEALTH_CHECK_PORT}")

# ==================== DATABASE ====================

class Database:
    """💾 Thread-safe database"""
    
    def __init__(self):
        self.lock = threading.Lock()
        self.data = {
            "users": {},
            "withdrawals": {},
            "admin_sessions": {},
            "stats": {"start_time": time.time()}
        }
        self.load()
    
    def load(self):
        try:
            with open(Config.DB_FILE, 'r') as f:
                self.data.update(json.load(f))
            logger.info(f"✅ Loaded {len(self.data['users'])} users")
        except: pass
    
    def save(self):
        try:
            with open(Config.DB_FILE, 'w') as f:
                json.dump(self.data, f, indent=2)
        except: pass
    
    def get_user(self, user_id: int) -> dict:
        with self.lock:
            uid = str(user_id)
            if uid not in self.data["users"]:
                self.data["users"][uid] = {
                    "id": uid,
                    "username": "",
                    "first_name": "",
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
                    "wallet": None,
                    "is_admin": int(uid) in Config.ADMIN_IDS
                }
                self.save()
            return self.data["users"][uid]
    
    def update_user(self, user_id: int, **kwargs):
        with self.lock:
            uid = str(user_id)
            if uid in self.data["users"]:
                self.data["users"][uid].update(kwargs)
                self.data["users"][uid]["last_active"] = time.time()
                self.save()
    
    def _generate_code(self) -> str:
        chars = string.ascii_uppercase + string.digits
        while True:
            code = ''.join(random.choices(chars, k=8))
            if not any(u.get("referral_code") == code for u in self.data["users"].values()):
                return code
    
    def get_user_by_code(self, code: str) -> Optional[dict]:
        for u in self.data["users"].values():
            if u.get("referral_code") == code:
                return u
        return None
    
    def get_pending_withdrawals(self) -> List[dict]:
        return [w for w in self.data["withdrawals"].values() if w.get("status") == "pending"]
    
    def create_withdrawal(self, user_id: int, amount: int, wallet: str) -> str:
        rid = f"W{int(time.time())}{user_id}{random.randint(100,999)}"
        with self.lock:
            self.data["withdrawals"][rid] = {
                "id": rid, "user_id": str(user_id), "amount": amount,
                "wallet": wallet, "status": "pending", "created_at": time.time()
            }
            self.save()
        return rid
    
    def process_withdrawal(self, rid: str, admin_id: int, status: str) -> bool:
        with self.lock:
            w = self.data["withdrawals"].get(rid)
            if not w or w["status"] != "pending":
                return False
            w["status"] = status
            w["processed_at"] = time.time()
            if status == "rejected":
                user = self.get_user(int(w["user_id"]))
                user["balance"] += w["amount"]
            self.save()
        return True
    
    def get_stats(self) -> dict:
        users = self.data["users"].values()
        return {
            "total_users": len(users),
            "verified": sum(1 for u in users if u.get("verified")),
            "total_balance": sum(u.get("balance", 0) for u in users),
            "pending_withdrawals": len(self.get_pending_withdrawals()),
            "uptime": int(time.time() - self.data["stats"].get("start_time", time.time()))
        }

db = Database()

# ==================== UTILITIES ====================

class Utils:
    @staticmethod
    def format_refi(refi: int) -> str:
        usd = (refi / 1_000_000) * Config.REFI_PER_MILLION
        return f"{refi:,} REFi (~${usd:.2f})"
    
    @staticmethod
    def short_wallet(wallet: str) -> str:
        return f"{wallet[:6]}...{wallet[-4:]}" if wallet and len(wallet) > 10 else "Not set"
    
    @staticmethod
    def is_valid_wallet(wallet: str) -> bool:
        return wallet and wallet.startswith('0x') and len(wallet) == 42

# ==================== BOTTOM NAVIGATION ====================

class BottomNavigation:
    """🎯 Professional Bottom Navigation System"""
    
    @staticmethod
    def main_menu(user: dict) -> dict:
        """🎯 Main menu with bottom navigation"""
        return {
            "inline_keyboard": [
                # Row 1: Balance & Referral
                [
                    {"text": "💰 Balance", "callback_data": "menu_balance"},
                    {"text": "🔗 Referral", "callback_data": "menu_referral"}
                ],
                # Row 2: Withdraw & Stats
                [
                    {"text": "💸 Withdraw", "callback_data": "menu_withdraw"},
                    {"text": "📊 Stats", "callback_data": "menu_stats"}
                ],
                # Row 3: Wallet (if not set) or Admin
                (
                    [{"text": "👛 Set Wallet", "callback_data": "menu_wallet"}]
                    if not user.get("wallet")
                    else [{"text": "👑 Admin", "callback_data": "menu_admin"}] 
                    if user.get("is_admin")
                    else []
                )
            ]
        }
    
    @staticmethod
    def channels() -> dict:
        """📢 Channel verification as floating buttons"""
        keyboard = []
        for ch in Config.REQUIRED_CHANNELS:
            keyboard.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
        keyboard.append([{"text": "✅ VERIFY NOW", "callback_data": "verify"}])
        return {"inline_keyboard": keyboard}
    
    @staticmethod
    def back() -> dict:
        """🔙 Back button"""
        return {"inline_keyboard": [[{"text": "🔙 Back to Menu", "callback_data": "menu_back"}]]}
    
    @staticmethod
    def admin() -> dict:
        """👑 Admin panel"""
        return {"inline_keyboard": [
            [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
            [{"text": "💰 Pending", "callback_data": "admin_pending"}],
            [{"text": "🔍 Search", "callback_data": "admin_search"}],
            [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
            [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
        ]}

# ==================== TELEGRAM API ====================

class Telegram:
    """📱 Telegram API Wrapper"""
    
    session = requests.Session()
    retries = Retry(total=3, backoff_factor=1)
    session.mount('https://', HTTPAdapter(max_retries=retries))
    
    @classmethod
    def _request(cls, method: str, json: dict = None) -> Optional[dict]:
        try:
            r = cls.session.post(f"{Config.API_URL}/{method}", json=json, timeout=15)
            return r.json().get("result") if r.json().get("ok") else None
        except: return None
    
    @classmethod
    def send_message(cls, chat_id: int, text: str, keyboard: dict = None) -> Optional[dict]:
        return cls._request("sendMessage", {
            "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
            "reply_markup": keyboard
        })
    
    @classmethod
    def edit_message(cls, chat_id: int, msg_id: int, text: str, keyboard: dict = None) -> Optional[dict]:
        return cls._request("editMessageText", {
            "chat_id": chat_id, "message_id": msg_id, "text": text,
            "parse_mode": "Markdown", "reply_markup": keyboard
        })
    
    @classmethod
    def answer_callback(cls, callback_id: str) -> Optional[dict]:
        return cls._request("answerCallbackQuery", {"callback_query_id": callback_id})
    
    @classmethod
    def get_chat_member(cls, chat_id: str, user_id: int) -> Optional[str]:
        try:
            r = cls.session.get(f"{Config.API_URL}/getChatMember", 
                               params={"chat_id": chat_id, "user_id": user_id}, timeout=10)
            return r.json().get("result", {}).get("status") if r.json().get("ok") else None
        except: return None

# ==================== HANDLERS ====================

class Handlers:
    """🎯 Professional Handlers"""
    
    @staticmethod
    def start(message: dict):
        """🚀 /start command"""
        chat_id = message["chat"]["id"]
        user = message["from"]
        user_id = user["id"]
        args = message.get("text", "").split()
        
        logger.info(f"▶️ Start: {user_id}")
        
        # Check referral
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
        db.update_user(user_id, username=user.get("username", ""), first_name=user.get("first_name", ""))
        
        # Show main menu if verified
        if user_data.get("verified"):
            text = f"🎯 *Main Menu*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
            Telegram.send_message(chat_id, text, BottomNavigation.main_menu(user_data))
            return
        
        # Show channel verification
        channels = "\n".join([f"• {ch['name']}" for ch in Config.REQUIRED_CHANNELS])
        text = (
            f"🎉 *Welcome to REFi Bot!*\n\n"
            f"💰 Welcome: {Utils.format_refi(Config.WELCOME_BONUS)}\n"
            f"👥 Referral: {Utils.format_refi(Config.REFERRAL_BONUS)}/friend\n\n"
            f"📢 Join:\n{channels}\n\n"
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
        db.update_user(user_id, verified=True, verified_at=time.time(),
                      balance=new_balance, total_earned=user_data.get("total_earned", 0) + Config.WELCOME_BONUS)
        
        # Process referral
        if user_data.get("referred_by"):
            referrer = db.get_user(int(user_data["referred_by"]))
            if referrer:
                referrer["balance"] += Config.REFERRAL_BONUS
                referrer["total_earned"] += Config.REFERRAL_BONUS
                referrer["referrals_count"] += 1
                referrer["referrals"][str(user_id)] = time.time()
                db.update_user(int(user_data["referred_by"]), 
                              balance=referrer["balance"],
                              total_earned=referrer["total_earned"],
                              referrals_count=referrer["referrals_count"],
                              referrals=referrer["referrals"])
                
                Telegram.send_message(int(user_data["referred_by"]),
                    f"🎉 *Friend Joined!*\n\nYou earned {Utils.format_refi(Config.REFERRAL_BONUS)}")
        
        text = (f"✅ *Verified!*\n\n✨ Added {Utils.format_refi(Config.WELCOME_BONUS)}\n"
                f"💰 Balance: {Utils.format_refi(new_balance)}")
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def menu_balance(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💰 Balance"""
        user_data = db.get_user(user_id)
        text = (f"💰 *Your Balance*\n\n"
                f"• {Utils.format_refi(user_data.get('balance', 0))}\n"
                f"• Total earned: {Utils.format_refi(user_data.get('total_earned', 0))}\n"
                f"• Referrals: {user_data.get('referrals_count', 0)}")
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_referral(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔗 Referral"""
        user_data = db.get_user(user_id)
        link = f"https://t.me/{Config.BOT_USERNAME}?start={user_data.get('referral_code', '')}"
        earned = user_data.get('referrals_count', 0) * Config.REFERRAL_BONUS
        
        text = (f"🔗 *Your Link*\n\n`{link}`\n\n"
                f"• You earn: {Utils.format_refi(Config.REFERRAL_BONUS)}/friend\n"
                f"• Friend gets: {Utils.format_refi(Config.WELCOME_BONUS)}\n"
                f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
                f"• Earned: {Utils.format_refi(earned)}")
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_stats(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """📊 Stats"""
        user_data = db.get_user(user_id)
        joined = datetime.fromtimestamp(user_data.get("joined_at", 0)).strftime("%Y-%m-%d")
        
        text = (f"📊 *Your Stats*\n\n"
                f"• Joined: {joined}\n"
                f"• Balance: {Utils.format_refi(user_data.get('balance', 0))}\n"
                f"• Total earned: {Utils.format_refi(user_data.get('total_earned', 0))}\n"
                f"• Referrals: {user_data.get('referrals_count', 0)}\n"
                f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
                f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
                f"• Wallet: {Utils.short_wallet(user_data.get('wallet', ''))}")
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
    
    @staticmethod
    def menu_withdraw(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """💸 Withdraw"""
        user_data = db.get_user(user_id)
        
        if not user_data.get("verified"):
            Telegram.edit_message(chat_id, msg_id, "❌ Verify first!", BottomNavigation.back())
            return
        
        if not user_data.get("wallet"):
            text = "⚠️ *Set wallet first!*\n\nUse 👛 Set Wallet button"
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
            return
        
        balance = user_data.get("balance", 0)
        if balance < Config.MIN_WITHDRAW:
            text = (f"⚠️ *Minimum: {Utils.format_refi(Config.MIN_WITHDRAW)}*\n"
                    f"Your balance: {Utils.format_refi(balance)}")
            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.back())
            return
        
        text = (f"💸 *Withdraw*\n\n"
                f"Balance: {Utils.format_refi(balance)}\n"
                f"Min: {Utils.format_refi(Config.MIN_WITHDRAW)}\n"
                f"Wallet: {Utils.short_wallet(user_data['wallet'])}\n\n"
                f"Send amount:")
        Telegram.edit_message(chat_id, msg_id, text)
        
        # Store state
        global user_states
        user_states[user_id] = {"action": "withdraw_amount"}
    
    @staticmethod
    def menu_wallet(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """👛 Set wallet"""
        user_data = db.get_user(user_id)
        text = (f"👛 *Set Wallet*\n\n"
                f"Current: {user_data.get('wallet', 'Not set')}\n\n"
                f"Send your Ethereum address (0x...):")
        Telegram.edit_message(chat_id, msg_id, text)
        
        global user_states
        user_states[user_id] = {"action": "wallet"}
    
    @staticmethod
    def menu_back(callback: dict, user_id: int, chat_id: int, msg_id: int):
        """🔙 Back to main menu"""
        user_data = db.get_user(user_id)
        text = f"🎯 *Main Menu*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}"
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def admin_login(message: dict):
        """👑 Admin login"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        if user_id not in Config.ADMIN_IDS:
            Telegram.send_message(chat_id, "⛔ Unauthorized")
            return
        
        Telegram.send_message(chat_id, "🔐 *Enter password:*")
        global user_states
        user_states[user_id] = {"action": "admin_login"}
    
    @staticmethod
    def handle_admin_login(text: str, user_id: int, chat_id: int):
        """✅ Admin login verification"""
        if text == Config.ADMIN_PASSWORD:
            db.data["admin_sessions"][str(user_id)] = time.time() + Config.SESSION_TIMEOUT
            db.save()
            
            stats = db.get_stats()
            text = (f"👑 *Admin Panel*\n\n"
                    f"Users: {stats['total_users']} | Verified: {stats['verified']}\n"
                    f"Balance: {Utils.format_refi(stats['total_balance'])}\n"
                    f"Pending: {stats['pending_withdrawals']}")
            Telegram.send_message(chat_id, text, BottomNavigation.admin())
        else:
            Telegram.send_message(chat_id, "❌ Wrong password!")
    
    @staticmethod
    def handle_wallet(text: str, user_id: int, chat_id: int):
        """✅ Save wallet"""
        if not Utils.is_valid_wallet(text):
            Telegram.send_message(chat_id, "❌ *Invalid wallet*\n\nMust be 0x + 40 hex chars")
            return
        
        db.update_user(user_id, wallet=text, wallet_set_at=time.time())
        user_data = db.get_user(user_id)
        Telegram.send_message(chat_id, 
            f"✅ *Wallet saved!*\n\n{Utils.short_wallet(text)}",
            BottomNavigation.main_menu(user_data))
    
    @staticmethod
    def handle_withdraw_amount(text: str, user_id: int, chat_id: int):
        """✅ Process withdrawal"""
        try:
            amount = int(text.replace(',', ''))
        except:
            Telegram.send_message(chat_id, "❌ Invalid amount")
            return
        
        user_data = db.get_user(user_id)
        
        if amount < Config.MIN_WITHDRAW:
            Telegram.send_message(chat_id, f"❌ Min: {Utils.format_refi(Config.MIN_WITHDRAW)}")
            return
        
        if amount > user_data.get("balance", 0):
            Telegram.send_message(chat_id, f"❌ Balance: {Utils.format_refi(user_data.get('balance', 0))}")
            return
        
        # Create withdrawal
        rid = db.create_withdrawal(user_id, amount, user_data["wallet"])
        db.update_user(user_id, balance=user_data["balance"] - amount)
        
        Telegram.send_message(chat_id,
            f"✅ *Withdrawal requested!*\n\nID: `{rid[:8]}...`\nAmount: {Utils.format_refi(amount)}",
            BottomNavigation.main_menu(user_data))
        
        # Notify admins
        for admin_id in Config.ADMIN_IDS:
            Telegram.send_message(admin_id,
                f"💰 *New Withdrawal*\n\nUser: {user_id}\nAmount: {Utils.format_refi(amount)}")
    
    @staticmethod
    def admin_stats(callback: dict, chat_id: int, msg_id: int):
        """📊 Admin stats"""
        stats = db.get_stats()
        h, m = stats['uptime'] // 3600, (stats['uptime'] % 3600) // 60
        
        text = (f"📊 *Statistics*\n\n"
                f"Users: {stats['total_users']} (✅ {stats['verified']})\n"
                f"Balance: {Utils.format_refi(stats['total_balance'])}\n"
                f"Pending: {stats['pending_withdrawals']}\n"
                f"Uptime: {h}h {m}m")
        Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.admin())
    
    @staticmethod
    def admin_pending(callback: dict, chat_id: int, msg_id: int):
        """💰 Pending withdrawals"""
        pending = db.get_pending_withdrawals()
        
        if not pending:
            Telegram.edit_message(chat_id, msg_id, "✅ No pending withdrawals", BottomNavigation.admin())
            return
        
        keyboard = {"inline_keyboard": []}
        text = "💰 *Pending Withdrawals*\n\n"
        
        for w in pending[:5]:
            text += f"• `{w['id'][:8]}`: {Utils.format_refi(w['amount'])}\n"
            keyboard["inline_keyboard"].append([
                {"text": f"Process {w['id'][:8]}", "callback_data": f"process_{w['id']}"}
            ])
        
        keyboard["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin_back"}])
        Telegram.edit_message(chat_id, msg_id, text, keyboard)
    
    @staticmethod
    def admin_process(callback: dict, chat_id: int, msg_id: int, rid: str):
        """⚙️ Process withdrawal"""
        w = db.data["withdrawals"].get(rid)
        if not w:
            return
        
        text = (f"💰 *Withdrawal*\n\n"
                f"ID: {rid}\nUser: {w['user_id']}\n"
                f"Amount: {Utils.format_refi(w['amount'])}\n"
                f"Wallet: {w['wallet']}")
        
        keyboard = {"inline_keyboard": [
            [{"text": "✅ Approve", "callback_data": f"approve_{rid}"},
             {"text": "❌ Reject", "callback_data": f"reject_{rid}"}],
            [{"text": "🔙 Back", "callback_data": "admin_pending"}]
        ]}
        Telegram.edit_message(chat_id, msg_id, text, keyboard)
    
    @staticmethod
    def admin_approve(callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """✅ Approve withdrawal"""
        if db.process_withdrawal(rid, admin_id, "approved"):
            Telegram.answer_callback(callback["id"], "✅ Approved")
        Handlers.admin_pending(callback, chat_id, msg_id)
    
    @staticmethod
    def admin_reject(callback: dict, admin_id: int, chat_id: int, msg_id: int, rid: str):
        """❌ Reject withdrawal"""
        if db.process_withdrawal(rid, admin_id, "rejected"):
            Telegram.answer_callback(callback["id"], "❌ Rejected")
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
            for u in db.data["users"].values():
                if u.get("username", "").lower() == username:
                    found = u
                    break
        
        if not found:
            Telegram.send_message(chat_id, f"❌ User not found: {text}")
            return
        
        stats = db.get_stats()
        text = (f"👤 *User Found*\n\n"
                f"ID: `{found['id']}`\n"
                f"Username: @{found.get('username', 'None')}\n"
                f"Name: {found.get('first_name', 'Unknown')}\n"
                f"Balance: {Utils.format_refi(found.get('balance', 0))}\n"
                f"Referrals: {found.get('referrals_count', 0)}\n"
                f"Verified: {'✅' if found.get('verified') else '❌'}\n"
                f"Wallet: {Utils.short_wallet(found.get('wallet', ''))}")
        
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
        db.data["admin_sessions"].pop(str(admin_id), None)
        db.save()
        
        user_data = db.get_user(admin_id)
        Telegram.answer_callback(callback["id"], "🔒 Logged out")
        Telegram.edit_message(chat_id, msg_id, 
            f"🔒 *Logged out*\n\n💰 Balance: {Utils.format_refi(user_data.get('balance', 0))}",
            BottomNavigation.main_menu(user_data))

# ==================== MAIN POLLING LOOP ====================

user_states = {}
offset = 0

def main():
    """🚀 Main polling loop"""
    global offset
    
    print("\n" + "="*60)
    print("🤖 REFi BOT - PROFESSIONAL EDITION v6.0.0")
    print("="*60)
    print(f"📱 Bot: @{Config.BOT_USERNAME}")
    print(f"👤 Admins: {Config.ADMIN_IDS}")
    print(f"💰 Welcome: {Utils.format_refi(Config.WELCOME_BONUS)}")
    print(f"👥 Users: {len(db.data['users'])}")
    print("="*60 + "\n")
    
    while True:
        try:
            r = requests.post(
                f"{Config.API_URL}/getUpdates",
                json={
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message", "callback_query"]
                },
                timeout=35
            )
            data = r.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    # Process messages
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = msg["from"]["id"]
                        text = msg.get("text", "")
                        
                        # Handle commands
                        if text == "/start":
                            Handlers.start(msg)
                        elif text == "/admin":
                            Handlers.admin_login(msg)
                        elif text.startswith("/"):
                            Telegram.send_message(chat_id, "❌ Unknown command")
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
                        
                        # Route callbacks
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
                            stats = db.get_stats()
                            text = (f"👑 *Admin Panel*\n\n"
                                    f"Users: {stats['total_users']} | Verified: {stats['verified']}\n"
                                    f"Balance: {Utils.format_refi(stats['total_balance'])}\n"
                                    f"Pending: {stats['pending_withdrawals']}")
                            Telegram.edit_message(chat_id, msg_id, text, BottomNavigation.admin())
                        elif data.startswith("process_"):
                            rid = data[8:]
                            Handlers.admin_process(cb, chat_id, msg_id, rid)
                        elif data.startswith("approve_"):
                            rid = data[8:]
                            Handlers.admin_approve(cb, user_id, chat_id, msg_id, rid)
                        elif data.startswith("reject_"):
                            rid = data[7:]
                            Handlers.admin_reject(cb, user_id, chat_id, msg_id, rid)
                    
                    offset = update["update_id"] + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"❌ Polling error: {e}")
            time.sleep(5)

# ==================== ENTRY POINT ====================

# For Gunicorn (Render/Koyeb compatibility)
app = None

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        logger.exception("❌ Fatal error")
        print(f"\n❌ Fatal: {e}")

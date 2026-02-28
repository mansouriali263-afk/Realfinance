#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
============================================================
🤖 REFi BOT - COMPLETE VERSION WITH ALL FEATURES
============================================================
Python version: 3.14.3
Token: 8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs

✅ Channel verification (3 channels)
✅ Referral system with unique codes
✅ Balance display in REFi and USD (1M REFi = $2)
✅ Withdrawal system with wallet validation
✅ Full admin panel with statistics
✅ Broadcast to all users
✅ User search
✅ Approve/reject withdrawals
============================================================
"""

import requests
import time
import json
import logging
import random
import string
from datetime import datetime
from typing import Dict, List, Optional, Any

# ==================== CONFIGURATION ====================

BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"

# Tokenomics
COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000  # 1,000,000 REFi welcome bonus
REFERRAL_BONUS = 1_000_000  # 1,000,000 REFi per referral
MIN_WITHDRAW = 5_000_000  # Minimum 5,000,000 REFi to withdraw
REFI_PER_MILLION = 2.0  # 1 million REFi = $2 USD

# Required channels
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

# ==================== LOGGING ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================

class Database:
    """Simple database using JSON file"""
    
    def __init__(self):
        self.users = {}  # user_id -> user data
        self.withdrawals = {}  # request_id -> withdrawal data
        self.admin_sessions = {}  # admin_id -> expiry
        self.stats = {
            "total_users": 0,
            "total_verified": 0,
            "total_withdrawals": 0,
            "total_withdrawn": 0,
            "total_referrals": 0,
            "start_time": time.time()
        }
        self.load()
    
    def load(self):
        """Load data from file"""
        try:
            with open("bot_data.json", "r") as f:
                data = json.load(f)
                self.users = data.get("users", {})
                self.withdrawals = data.get("withdrawals", {})
                self.stats = data.get("stats", self.stats)
            logger.info(f"✅ Loaded {len(self.users)} users, {len(self.withdrawals)} withdrawals")
        except FileNotFoundError:
            logger.info("📁 No existing data file, starting fresh")
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
    
    def save(self):
        """Save data to file"""
        try:
            data = {
                "users": self.users,
                "withdrawals": self.withdrawals,
                "stats": self.stats
            }
            with open("bot_data.json", "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"❌ Error saving data: {e}")
    
    def get_user(self, user_id: str) -> dict:
        """Get user by ID, create if not exists"""
        user_id = str(user_id)
        if user_id not in self.users:
            self.users[user_id] = {
                "id": user_id,
                "username": "",
                "first_name": "",
                "joined_at": time.time(),
                "last_active": time.time(),
                "balance": 0,
                "total_earned": 0,
                "total_withdrawn": 0,
                "referral_code": self.generate_code(user_id),
                "referred_by": None,
                "referrals_count": 0,
                "referrals": {},
                "referral_clicks": 0,
                "verified": False,
                "verified_at": None,
                "wallet": None,
                "is_admin": int(user_id) in ADMIN_IDS,
                "is_banned": False,
                "pending_withdrawals": []
            }
            self.stats["total_users"] = len(self.users)
            self.save()
        return self.users[user_id]
    
    def update_user(self, user_id: str, **kwargs):
        """Update user data"""
        user_id = str(user_id)
        if user_id in self.users:
            self.users[user_id].update(kwargs)
            self.users[user_id]["last_active"] = time.time()
            self.save()
    
    def generate_code(self, user_id: str) -> str:
        """Generate unique referral code"""
        chars = string.ascii_uppercase + string.digits
        code = ''.join(random.choices(chars, k=8))
        # Check uniqueness
        for u in self.users.values():
            if u.get("referral_code") == code:
                return self.generate_code(user_id)
        return code
    
    def get_user_by_code(self, code: str) -> Optional[dict]:
        """Find user by referral code"""
        for user in self.users.values():
            if user.get("referral_code") == code:
                return user
        return None
    
    def get_user_by_username(self, username: str) -> Optional[dict]:
        """Find user by username"""
        username = username.lower().lstrip('@')
        for user in self.users.values():
            if user.get("username", "").lower() == username:
                return user
        return None
    
    def add_referral(self, referrer_id: str, referred_id: str):
        """Add a successful referral"""
        referrer = self.get_user(referrer_id)
        referred = self.get_user(referred_id)
        
        if not referrer or not referred:
            return False
        
        if str(referred_id) in referrer.get("referrals", {}):
            return False
        
        # Update referrer
        referrer["referrals"][str(referred_id)] = time.time()
        referrer["referrals_count"] = referrer.get("referrals_count", 0) + 1
        referrer["balance"] = referrer.get("balance", 0) + REFERRAL_BONUS
        referrer["total_earned"] = referrer.get("total_earned", 0) + REFERRAL_BONUS
        
        self.update_user(referrer_id, 
                        referrals=referrer["referrals"],
                        referrals_count=referrer["referrals_count"],
                        balance=referrer["balance"],
                        total_earned=referrer["total_earned"])
        
        self.stats["total_referrals"] += 1
        self.save()
        return True
    
    def create_withdrawal(self, user_id: str, amount: int, wallet: str) -> str:
        """Create withdrawal request"""
        request_id = f"W{int(time.time())}{user_id}{random.randint(100,999)}"
        
        withdrawal = {
            "id": request_id,
            "user_id": user_id,
            "amount": amount,
            "wallet": wallet,
            "status": "pending",
            "created_at": time.time(),
            "processed_at": None
        }
        
        self.withdrawals[request_id] = withdrawal
        self.stats["total_withdrawals"] += 1
        self.save()
        return request_id
    
    def get_withdrawal(self, request_id: str) -> Optional[dict]:
        """Get withdrawal by ID"""
        return self.withdrawals.get(request_id)
    
    def get_pending_withdrawals(self) -> List[dict]:
        """Get all pending withdrawals"""
        return [w for w in self.withdrawals.values() if w["status"] == "pending"]
    
    def get_user_withdrawals(self, user_id: str) -> List[dict]:
        """Get user withdrawals"""
        return [w for w in self.withdrawals.values() if w["user_id"] == user_id]
    
    def process_withdrawal(self, request_id: str, admin_id: int, status: str, tx_hash: str = None):
        """Process withdrawal (approve/reject)"""
        withdrawal = self.get_withdrawal(request_id)
        if not withdrawal:
            return False
        
        withdrawal["status"] = status
        withdrawal["processed_at"] = time.time()
        withdrawal["processed_by"] = admin_id
        withdrawal["tx_hash"] = tx_hash
        
        if status == "approved":
            self.stats["total_withdrawn"] += withdrawal["amount"]
        
        self.save()
        return True
    
    def admin_login(self, admin_id: int) -> bool:
        """Create admin session"""
        self.admin_sessions[admin_id] = time.time() + SESSION_TIMEOUT
        return True
    
    def admin_logout(self, admin_id: int):
        """End admin session"""
        self.admin_sessions.pop(admin_id, None)
    
    def is_admin_logged_in(self, admin_id: int) -> bool:
        """Check if admin has valid session"""
        if admin_id not in self.admin_sessions:
            return False
        if self.admin_sessions[admin_id] < time.time():
            del self.admin_sessions[admin_id]
            return False
        return True
    
    def get_stats(self) -> dict:
        """Get bot statistics"""
        total_balance = sum(u.get("balance", 0) for u in self.users.values())
        verified = sum(1 for u in self.users.values() if u.get("verified", False))
        pending = len(self.get_pending_withdrawals())
        
        return {
            "total_users": len(self.users),
            "verified": verified,
            "unverified": len(self.users) - verified,
            "total_balance": total_balance,
            "total_balance_usd": self.refi_to_usd(total_balance),
            "total_withdrawals": self.stats["total_withdrawals"],
            "total_withdrawn": self.stats["total_withdrawn"],
            "total_withdrawn_usd": self.refi_to_usd(self.stats["total_withdrawn"]),
            "pending_withdrawals": pending,
            "total_referrals": self.stats["total_referrals"],
            "uptime": int(time.time() - self.stats["start_time"])
        }
    
    def refi_to_usd(self, refi: int) -> float:
        """Convert REFi to USD (1M = $2)"""
        return (refi / 1_000_000) * REFI_PER_MILLION
    
    def format_refi(self, refi: int) -> str:
        """Format REFi with USD value"""
        usd = self.refi_to_usd(refi)
        return f"{refi:,} {COIN_NAME} (~${usd:.2f})"

# Initialize database
db = Database()

# ==================== TELEGRAM API FUNCTIONS ====================

def send_message(chat_id, text, reply_markup=None, parse_mode="Markdown"):
    """Send message via Telegram API"""
    url = f"{API_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        return response.json()
    except Exception as e:
        logger.error(f"Send error: {e}")
        return None

def edit_message(chat_id, message_id, text, reply_markup=None, parse_mode="Markdown"):
    """Edit message"""
    url = f"{API_URL}/editMessageText"
    payload = {
        "chat_id": chat_id,
        "message_id": message_id,
        "text": text,
        "parse_mode": parse_mode
    }
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Edit error: {e}")

def answer_callback(callback_id, text=None):
    """Answer callback query"""
    url = f"{API_URL}/answerCallbackQuery"
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Callback error: {e}")

def get_chat_member(chat_id, user_id):
    """Check if user is member of channel"""
    url = f"{API_URL}/getChatMember"
    params = {
        "chat_id": chat_id,
        "user_id": user_id
    }
    try:
        response = requests.get(url, params=params, timeout=10)
        data = response.json()
        if data.get("ok"):
            return data.get("result", {}).get("status")
        return None
    except Exception as e:
        logger.error(f"GetChatMember error: {e}")
        return None

# ==================== KEYBOARDS ====================

def channels_keyboard():
    """Keyboard for channel verification"""
    keyboard = []
    for ch in REQUIRED_CHANNELS:
        keyboard.append([{
            "text": f"📢 Join {ch['name']}",
            "url": ch['link']
        }])
    keyboard.append([{
        "text": "✅ Verify Membership",
        "callback_data": "verify"
    }])
    return {"inline_keyboard": keyboard}

def main_keyboard(is_admin=False):
    """Main menu keyboard"""
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
    if is_admin:
        keyboard.append([{"text": "👑 Admin Panel", "callback_data": "admin_panel"}])
    return {"inline_keyboard": keyboard}

def back_keyboard():
    """Back button only"""
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

def admin_keyboard():
    """Admin panel keyboard"""
    keyboard = [
        [{"text": "📊 Statistics", "callback_data": "admin_stats"}],
        [{"text": "💰 Pending Withdrawals", "callback_data": "admin_withdrawals"}],
        [{"text": "🔍 Search User", "callback_data": "admin_search"}],
        [{"text": "📢 Broadcast", "callback_data": "admin_broadcast"}],
        [{"text": "👥 Users List", "callback_data": "admin_users"}],
        [{"text": "🔒 Logout", "callback_data": "admin_logout"}]
    ]
    return {"inline_keyboard": keyboard}

def withdrawal_action_keyboard(request_id):
    """Withdrawal action buttons for admin"""
    keyboard = [
        [
            {"text": "✅ Approve", "callback_data": f"approve_{request_id}"},
            {"text": "❌ Reject", "callback_data": f"reject_{request_id}"}
        ],
        [{"text": "🔙 Back", "callback_data": "admin_withdrawals"}]
    ]
    return {"inline_keyboard": keyboard}

# ==================== HANDLERS ====================

def handle_start(message):
    """Handle /start command"""
    chat_id = message["chat"]["id"]
    user = message["from"]
    user_id = str(user["id"])
    args = message.get("text", "").split()
    
    logger.info(f"Start from {user_id}")
    
    # Get or create user
    user_data = db.get_user(user_id)
    db.update_user(user_id,
                  username=user.get("username", ""),
                  first_name=user.get("first_name", ""))
    
    # Check for referral
    if len(args) > 1 and not user_data.get("referred_by"):
        ref_code = args[1]
        referrer = db.get_user_by_code(ref_code)
        if referrer and referrer["id"] != user_id:
            db.update_user(user_id, referred_by=referrer["id"])
            
            # Update referral clicks
            referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
            db.update_user(referrer["id"], 
                          referral_clicks=referrer["referral_clicks"])
    
    # If already verified, show main menu
    if user_data.get("verified"):
        text = (
            f"🎯 *Main Menu*\n\n"
            f"💰 Balance: {db.format_refi(user_data.get('balance', 0))}\n"
            f"👥 Referrals: {user_data.get('referrals_count', 0)}"
        )
        send_message(chat_id, text, main_keyboard(user_data.get("is_admin", False)))
        return
    
    # Show channel verification
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    text = (
        f"🎉 *Welcome to {COIN_NAME} Bot!*\n\n"
        f"💰 *Welcome Bonus:* {db.format_refi(WELCOME_BONUS)}\n"
        f"👥 *Referral Bonus:* {db.format_refi(REFERRAL_BONUS)} per friend\n\n"
        f"📢 *To start, you must join these channels:*\n{channels_text}\n\n"
        f"👇 Click 'Verify' after joining"
    )
    send_message(chat_id, text, channels_keyboard())

def handle_verify(callback, user_id, chat_id, message_id):
    """Handle verify button"""
    # Check channel membership
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], int(user_id))
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        text = f"❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit_message(chat_id, message_id, text, channels_keyboard())
        return
    
    # Verify user
    user_data = db.get_user(user_id)
    if user_data.get("verified"):
        text = f"✅ *Already verified!*\n\n{db.format_refi(user_data.get('balance', 0))}"
        edit_message(chat_id, message_id, text, main_keyboard(user_data.get("is_admin", False)))
        return
    
    # Add welcome bonus
    new_balance = user_data.get("balance", 0) + WELCOME_BONUS
    db.update_user(user_id,
                  verified=True,
                  verified_at=time.time(),
                  balance=new_balance,
                  total_earned=user_data.get("total_earned", 0) + WELCOME_BONUS)
    
    # Process referral if exists
    referred_by = user_data.get("referred_by")
    if referred_by:
        db.add_referral(referred_by, user_id)
        # Notify referrer
        try:
            referrer_data = db.get_user(referred_by)
            send_message(
                int(referred_by),
                f"🎉 *Friend Joined!*\n\n"
                f"{user_data.get('first_name', 'Someone')} joined using your link!\n"
                f"✨ You earned {db.format_refi(REFERRAL_BONUS)}"
            )
        except:
            pass
    
    # Success message
    text = (
        f"✅ *Verification Successful!*\n\n"
        f"✨ Added {db.format_refi(WELCOME_BONUS)} to your balance\n"
        f"💰 Current: {db.format_refi(new_balance)}\n\n"
        f"👥 Share your link and earn {db.format_refi(REFERRAL_BONUS)} per friend!"
    )
    edit_message(chat_id, message_id, text, main_keyboard(user_data.get("is_admin", False)))

def handle_balance(callback, user_id, chat_id, message_id):
    """Handle balance button"""
    user_data = db.get_user(user_id)
    ref_earned = user_data.get("referrals_count", 0) * REFERRAL_BONUS
    
    text = (
        f"💰 *Your Balance*\n\n"
        f"• Current: {db.format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {db.format_refi(user_data.get('total_earned', 0))}\n"
        f"• Total withdrawn: {db.format_refi(user_data.get('total_withdrawn', 0))}\n\n"
        f"📊 *Referrals*\n"
        f"• Count: {user_data.get('referrals_count', 0)}\n"
        f"• Earned: {db.format_refi(ref_earned)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_referral(callback, user_id, chat_id, message_id):
    """Handle referral button"""
    user_data = db.get_user(user_id)
    bot_username = "Realfinancepaybot"
    link = f"https://t.me/{bot_username}?start={user_data.get('referral_code', '')}"
    
    text = (
        f"🔗 *Your Referral Link*\n\n"
        f"`{link}`\n\n"
        f"🎁 *Rewards*\n"
        f"• You get: {db.format_refi(REFERRAL_BONUS)} per referral\n"
        f"• Friend gets: {db.format_refi(WELCOME_BONUS)}\n\n"
        f"📊 *Stats*\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n"
        f"• Successful: {user_data.get('referrals_count', 0)}\n"
        f"• Earned: {db.format_refi(user_data.get('referrals_count', 0) * REFERRAL_BONUS)}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_stats(callback, user_id, chat_id, message_id):
    """Handle stats button"""
    user_data = db.get_user(user_id)
    joined = datetime.fromtimestamp(user_data.get("joined_at", 0)).strftime("%Y-%m-%d")
    
    text = (
        f"📊 *Your Statistics*\n\n"
        f"👤 *User Info*\n"
        f"• ID: `{user_id}`\n"
        f"• Joined: {joined}\n\n"
        f"💰 *Financial*\n"
        f"• Balance: {db.format_refi(user_data.get('balance', 0))}\n"
        f"• Total earned: {db.format_refi(user_data.get('total_earned', 0))}\n"
        f"• Withdrawn: {db.format_refi(user_data.get('total_withdrawn', 0))}\n\n"
        f"👥 *Referrals*\n"
        f"• Total: {user_data.get('referrals_count', 0)}\n"
        f"• Clicks: {user_data.get('referral_clicks', 0)}\n\n"
        f"✅ *Status*\n"
        f"• Verified: {'✅' if user_data.get('verified') else '❌'}\n"
        f"• Wallet: {'✅ Set' if user_data.get('wallet') else '❌ Not set'}"
    )
    edit_message(chat_id, message_id, text, back_keyboard())

def handle_withdraw(callback, user_id, chat_id, message_id):
    """Handle withdraw button"""
    user_data = db.get_user(user_id)
    
    if not user_data.get("verified"):
        text = "❌ *You must verify first!*\n\nSend /start to begin."
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    # Check pending withdrawals
    pending = [w for w in db.get_user_withdrawals(user_id) if w["status"] == "pending"]
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        text = f"⚠️ *You have {len(pending)} pending withdrawals.*\nMax allowed: {MAX_PENDING_WITHDRAWALS}"
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    balance = user_data.get("balance", 0)
    if balance < MIN_WITHDRAW:
        needed = MIN_WITHDRAW - balance
        text = (
            f"⚠️ *Minimum withdrawal: {db.format_refi(MIN_WITHDRAW)}*\n"
            f"Your balance: {db.format_refi(balance)}\n\n"
            f"You need {db.format_refi(needed)} more to withdraw."
        )
        edit_message(chat_id, message_id, text, back_keyboard())
        return
    
    text = (
        f"💸 *Withdrawal*\n\n"
        f"Balance: {db.format_refi(balance)}\n"
        f"Min: {db.format_refi(MIN_WITHDRAW)}\n\n"
        f"Send the amount you want to withdraw:"
    )
    edit_message(chat_id, message_id, text)
    
    # Store state
    global user_states
    user_states[user_id] = {"action": "waiting_amount"}

def handle_withdraw_amount(message, user_id, chat_id):
    """Handle withdrawal amount input"""
    global user_states
    
    try:
        amount = int(message.get("text", "").replace(",", "").strip())
    except:
        send_message(chat_id, "❌ Please enter a valid number.")
        return
    
    user_data = db.get_user(user_id)
    
    if amount < MIN_WITHDRAW:
        send_message(chat_id, f"❌ Minimum amount is {db.format_refi(MIN_WITHDRAW)}")
        return
    
    if amount > user_data.get("balance", 0):
        send_message(chat_id, f"❌ Insufficient balance. You have {db.format_refi(user_data.get('balance', 0))}")
        return
    
    # Store amount and ask for wallet
    user_states[user_id] = {
        "action": "waiting_wallet",
        "amount": amount
    }
    
    send_message(chat_id, 
                "📮 *Enter your wallet address*\n\n"
                "Please enter your Ethereum wallet address (starts with 0x):\n"
                "Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`")

def handle_wallet(message, user_id, chat_id):
    """Handle wallet address input"""
    global user_states
    
    wallet = message.get("text", "").strip()
    
    # Validate wallet
    if not wallet.startswith("0x") or len(wallet) != 42:
        send_message(chat_id, 
                    "❌ *Invalid wallet address*\n\n"
                    "Must start with 0x and be 42 characters long.")
        return
    
    try:
        int(wallet[2:], 16)  # Check if hex
    except:
        send_message(chat_id, "❌ Invalid hex characters in address.")
        return
    
    state = user_states.get(user_id, {})
    amount = state.get("amount")
    
    if not amount:
        send_message(chat_id, "❌ Please start withdrawal again.")
        return
    
    # Deduct balance
    user_data = db.get_user(user_id)
    new_balance = user_data.get("balance", 0) - amount
    db.update_user(user_id, balance=new_balance, wallet=wallet)
    
    # Create withdrawal request
    request_id = db.create_withdrawal(user_id, amount, wallet)
    
    # Clear state
    user_states.pop(user_id, None)
    
    # Confirm to user
    text = (
        f"✅ *Withdrawal Request Submitted!*\n\n"
        f"📝 Request ID: `{request_id}`\n"
        f"💰 Amount: {db.format_refi(amount)}\n"
        f"📮 Wallet: `{wallet[:6]}...{wallet[-4:]}`\n\n"
        f"⏳ Status: *Pending Review*"
    )
    send_message(chat_id, text, main_keyboard(user_data.get("is_admin", False)))
    
    # Notify admins
    for admin_id in ADMIN_IDS:
        try:
            send_message(
                admin_id,
                f"💰 *New Withdrawal Request*\n\n"
                f"User: {user_data.get('first_name', 'Unknown')} (@{user_data.get('username', '')})\n"
                f"ID: `{user_id}`\n"
                f"Amount: {db.format_refi(amount)}\n"
                f"Wallet: `{wallet}`\n\n"
                f"Request ID: `{request_id}`"
            )
        except:
            pass

def handle_back(callback, user_id, chat_id, message_id):
    """Handle back button"""
    user_data = db.get_user(user_id)
    text = (
        f"🎯 *Main Menu*\n\n"
        f"💰 Balance: {db.format_refi(user_data.get('balance', 0))}\n"
        f"👥 Referrals: {user_data.get('referrals_count', 0)}"
    )
    edit_message(chat_id, message_id, text, main_keyboard(user_data.get("is_admin", False)))

# ==================== ADMIN HANDLERS ====================

def handle_admin_panel(callback, user_id, chat_id, message_id):
    """Show admin panel"""
    if int(user_id) not in ADMIN_IDS:
        answer_callback(callback["id"], "⛔ Unauthorized")
        return
    
    if not db.is_admin_logged_in(int(user_id)):
        text = "🔐 *Please login first*\n\nUse /admin command to login."
        edit_message(chat_id, message_id, text)
        return
    
    stats = db.get_stats()
    hours = stats["uptime"] // 3600
    minutes = (stats["uptime"] % 3600) // 60
    
    text = (
        f"👑 *Admin Panel*\n\n"
        f"📊 *Statistics*\n"
        f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
        f"• Balance: {db.format_refi(stats['total_balance'])}\n"
        f"• Withdrawals: {stats['total_withdrawals']} (💰 {stats['pending_withdrawals']} pending)\n"
        f"• Referrals: {stats['total_referrals']}\n"
        f"• Uptime: {hours}h {minutes}m"
    )
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_stats(callback, user_id, chat_id, message_id):
    """Show detailed admin statistics"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    stats = db.get_stats()
    hours = stats["uptime"] // 3600
    minutes = (stats["uptime"] % 3600) // 60
    
    # Calculate active users
    now = time.time()
    active_today = sum(1 for u in db.users.values() if u.get("last_active", 0) > now - 86400)
    active_week = sum(1 for u in db.users.values() if u.get("last_active", 0) > now - 604800)
    
    text = (
        f"📊 *Detailed Statistics*\n\n"
        f"👥 *Users*\n"
        f"• Total: {stats['total_users']}\n"
        f"• Verified: {stats['verified']}\n"
        f"• Unverified: {stats['unverified']}\n"
        f"• Active today: {active_today}\n"
        f"• Active week: {active_week}\n\n"
        f"💰 *Financial*\n"
        f"• Total balance: {db.format_refi(stats['total_balance'])}\n"
        f"• Total withdrawn: {db.format_refi(stats['total_withdrawn'])}\n"
        f"• Pending withdrawals: {stats['pending_withdrawals']}\n\n"
        f"📈 *Referrals*\n"
        f"• Total: {stats['total_referrals']}\n"
        f"• Avg per user: {stats['total_referrals'] / max(1, stats['total_users']):.2f}\n\n"
        f"⏱️ *Bot Stats*\n"
        f"• Uptime: {hours}h {minutes}m\n"
        f"• Started: {datetime.fromtimestamp(db.stats['start_time']).strftime('%Y-%m-%d %H:%M')}"
    )
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_withdrawals(callback, user_id, chat_id, message_id):
    """Show pending withdrawals"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    pending = db.get_pending_withdrawals()
    
    if not pending:
        text = "✅ *No pending withdrawals.*"
        edit_message(chat_id, message_id, text, admin_keyboard())
        return
    
    text = "💰 *Pending Withdrawals*\n\n"
    keyboard = []
    
    for w in pending[:5]:  # Show first 5
        user = db.get_user(w["user_id"])
        name = user.get("first_name", "Unknown")
        username = f"@{user.get('username', '')}" if user.get('username') else "No username"
        
        text += (
            f"🆔 `{w['id'][:8]}...`\n"
            f"👤 {name} ({username})\n"
            f"💰 {db.format_refi(w['amount'])}\n"
            f"📮 `{w['wallet'][:6]}...{w['wallet'][-4:]}`\n\n"
        )
        
        keyboard.append([{
            "text": f"Process {w['id'][:8]}",
            "callback_data": f"process_{w['id']}"
        }])
    
    if len(pending) > 5:
        text += f"*... and {len(pending) - 5} more*\n\n"
    
    keyboard.append([{"text": "🔙 Back", "callback_data": "admin_panel"}])
    edit_message(chat_id, message_id, text, {"inline_keyboard": keyboard})

def handle_process_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Show withdrawal details for processing"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    withdrawal = db.get_withdrawal(request_id)
    if not withdrawal:
        answer_callback(callback["id"], "❌ Withdrawal not found")
        return
    
    user = db.get_user(withdrawal["user_id"])
    
    text = (
        f"💰 *Withdrawal Details*\n\n"
        f"📝 Request ID: `{request_id}`\n"
        f"👤 User: {user.get('first_name', 'Unknown')} (@{user.get('username', '')})\n"
        f"🆔 User ID: `{withdrawal['user_id']}`\n"
        f"💰 Amount: {db.format_refi(withdrawal['amount'])}\n"
        f"📮 Wallet: `{withdrawal['wallet']}`\n"
        f"📅 Created: {datetime.fromtimestamp(withdrawal['created_at']).strftime('%Y-%m-%d %H:%M')}\n"
        f"📊 Status: {withdrawal['status']}"
    )
    
    edit_message(chat_id, message_id, text, withdrawal_action_keyboard(request_id))

def handle_approve_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Approve withdrawal"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    withdrawal = db.get_withdrawal(request_id)
    if not withdrawal or withdrawal["status"] != "pending":
        answer_callback(callback["id"], "❌ Already processed")
        return
    
    # Process approval
    db.process_withdrawal(request_id, int(user_id), "approved")
    
    # Notify user
    try:
        user = db.get_user(withdrawal["user_id"])
        send_message(
            int(withdrawal["user_id"]),
            f"✅ *Withdrawal Approved!*\n\n"
            f"Request ID: `{request_id}`\n"
            f"Amount: {db.format_refi(withdrawal['amount'])}\n"
            f"Wallet: `{withdrawal['wallet']}`\n\n"
            f"Your withdrawal has been approved and will be processed shortly."
        )
    except:
        pass
    
    answer_callback(callback["id"], "✅ Approved")
    handle_admin_withdrawals(callback, user_id, chat_id, message_id)

def handle_reject_withdrawal(callback, user_id, chat_id, message_id, request_id):
    """Reject withdrawal and return funds"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    withdrawal = db.get_withdrawal(request_id)
    if not withdrawal or withdrawal["status"] != "pending":
        answer_callback(callback["id"], "❌ Already processed")
        return
    
    # Return funds to user
    user = db.get_user(withdrawal["user_id"])
    user["balance"] = user.get("balance", 0) + withdrawal["amount"]
    db.update_user(withdrawal["user_id"], balance=user["balance"])
    
    # Process rejection
    db.process_withdrawal(request_id, int(user_id), "rejected")
    
    # Notify user
    try:
        send_message(
            int(withdrawal["user_id"]),
            f"❌ *Withdrawal Rejected*\n\n"
            f"Request ID: `{request_id}`\n"
            f"Amount: {db.format_refi(withdrawal['amount'])}\n\n"
            f"Your withdrawal was rejected. The amount has been returned to your balance.\n"
            f"Please contact support for more information."
        )
    except:
        pass
    
    answer_callback(callback["id"], "❌ Rejected")
    handle_admin_withdrawals(callback, user_id, chat_id, message_id)

def handle_admin_search(callback, user_id, chat_id, message_id):
    """Initiate user search"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    text = (
        "🔍 *Search User*\n\n"
        "Send me the User ID or username to search for.\n\n"
        "Examples:\n"
        "• `1653918641` (User ID)\n"
        "• `@username` (Username)"
    )
    edit_message(chat_id, message_id, text)
    
    global user_states
    user_states[user_id] = {"action": "admin_search"}

def handle_admin_search_input(message, user_id, chat_id):
    """Handle search input"""
    global user_states
    
    query = message.get("text", "").strip()
    found_user = None
    
    # Search by ID
    if query.isdigit():
        found_user = db.get_user(query)
    else:
        # Search by username
        found_user = db.get_user_by_username(query)
    
    if not found_user:
        send_message(chat_id, f"❌ User not found: {query}")
        user_states.pop(user_id, None)
        return
    
    # Calculate user stats
    balance = found_user.get("balance", 0)
    total_earned = found_user.get("total_earned", 0)
    total_withdrawn = found_user.get("total_withdrawn", 0)
    referrals = found_user.get("referrals_count", 0)
    pending = [w for w in db.get_user_withdrawals(found_user["id"]) if w["status"] == "pending"]
    
    joined = datetime.fromtimestamp(found_user.get("joined_at", 0)).strftime("%Y-%m-%d %H:%M")
    last_active = datetime.fromtimestamp(found_user.get("last_active", 0)).strftime("%Y-%m-%d %H:%M")
    
    text = (
        f"👤 *User Information*\n\n"
        f"🆔 ID: `{found_user['id']}`\n"
        f"📱 Username: @{found_user.get('username', 'None')}\n"
        f"👤 Name: {found_user.get('first_name', 'Unknown')}\n"
        f"📅 Joined: {joined}\n"
        f"⏱️ Last active: {last_active}\n\n"
        f"💰 *Financial*\n"
        f"• Balance: {db.format_refi(balance)}\n"
        f"• Total earned: {db.format_refi(total_earned)}\n"
        f"• Withdrawn: {db.format_refi(total_withdrawn)}\n"
        f"• Pending withdrawals: {len(pending)}\n\n"
        f"👥 *Referrals*\n"
        f"• Count: {referrals}\n"
        f"• Code: `{found_user.get('referral_code', '')}`\n"
        f"• Clicks: {found_user.get('referral_clicks', 0)}\n"
        f"• Referred by: {found_user.get('referred_by', 'Direct')}\n\n"
        f"✅ *Status*\n"
        f"• Verified: {'✅' if found_user.get('verified') else '❌'}\n"
        f"• Wallet: {found_user.get('wallet', 'Not set')}\n"
        f"• Admin: {'✅' if found_user.get('is_admin') else '❌'}\n"
        f"• Banned: {'✅' if found_user.get('is_banned') else '❌'}"
    )
    
    send_message(chat_id, text)
    user_states.pop(user_id, None)

def handle_admin_broadcast(callback, user_id, chat_id, message_id):
    """Initiate broadcast"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    text = (
        "📢 *Broadcast Message*\n\n"
        f"Total users: {len(db.users)}\n\n"
        "Send me the message you want to broadcast to all users.\n"
        "You can use Markdown formatting."
    )
    edit_message(chat_id, message_id, text)
    
    global user_states
    user_states[user_id] = {"action": "admin_broadcast"}

def handle_admin_broadcast_input(message, user_id, chat_id):
    """Handle broadcast input"""
    global user_states
    
    msg_text = message.get("text", "")
    if not msg_text:
        send_message(chat_id, "❌ Message cannot be empty.")
        return
    
    send_message(chat_id, f"📢 Broadcasting to {len(db.users)} users...")
    
    sent = 0
    failed = 0
    
    for uid in db.users.keys():
        try:
            send_message(int(uid), msg_text)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)  # Avoid flood limits
        except Exception as e:
            failed += 1
            logger.error(f"Broadcast failed to {uid}: {e}")
    
    result = (
        f"✅ *Broadcast Complete*\n\n"
        f"• Sent: {sent}\n"
        f"• Failed: {failed}\n"
        f"• Total: {len(db.users)}"
    )
    send_message(chat_id, result)
    user_states.pop(user_id, None)

def handle_admin_users(callback, user_id, chat_id, message_id):
    """Show users list"""
    if int(user_id) not in ADMIN_IDS or not db.is_admin_logged_in(int(user_id)):
        return
    
    users_list = sorted(db.users.values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    
    text = "👥 *Recent Users*\n\n"
    for u in users_list:
        name = u.get("first_name", "Unknown")
        username = f"@{u.get('username', '')}" if u.get('username') else "No username"
        verified = "✅" if u.get("verified") else "❌"
        joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime("%m-%d")
        text += f"{verified} {name} {username} - {joined}\n"
    
    text += f"\n*Total: {len(db.users)} users*"
    edit_message(chat_id, message_id, text, admin_keyboard())

def handle_admin_logout(callback, user_id, chat_id, message_id):
    """Logout from admin panel"""
    if int(user_id) in ADMIN_IDS:
        db.admin_logout(int(user_id))
    
    user_data = db.get_user(user_id)
    text = f"🔒 *Logged out*\n\n💰 Balance: {db.format_refi(user_data.get('balance', 0))}"
    edit_message(chat_id, message_id, text, main_keyboard(user_data.get("is_admin", False)))

# ==================== ADMIN LOGIN ====================

def handle_admin_command(message):
    """Handle /admin command"""
    chat_id = message["chat"]["id"]
    user_id = message["from"]["id"]
    
    if user_id not in ADMIN_IDS:
        send_message(chat_id, "⛔ Unauthorized")
        return
    
    if db.is_admin_logged_in(user_id):
        stats = db.get_stats()
        hours = stats["uptime"] // 3600
        minutes = (stats["uptime"] % 3600) // 60
        
        text = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {db.format_refi(stats['total_balance'])}\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        send_message(chat_id, text, admin_keyboard())
    else:
        send_message(chat_id, "🔐 *Admin Login*\n\nPlease enter password:")
        global user_states
        user_states[str(user_id)] = {"action": "admin_login"}

def handle_admin_login_input(message, user_id, chat_id):
    """Handle admin password input"""
    global user_states
    
    password = message.get("text", "").strip()
    
    if password == ADMIN_PASSWORD:
        db.admin_login(int(user_id))
        
        # Update user as admin
        user_data = db.get_user(str(user_id))
        db.update_user(str(user_id), is_admin=True)
        
        send_message(chat_id, "✅ *Login successful!*")
        
        stats = db.get_stats()
        hours = stats["uptime"] // 3600
        minutes = (stats["uptime"] % 3600) // 60
        
        text = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Users: {stats['total_users']} (✅ {stats['verified']})\n"
            f"• Balance: {db.format_refi(stats['total_balance'])}\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        send_message(chat_id, text, admin_keyboard())
    else:
        send_message(chat_id, "❌ *Wrong password!*")
    
    user_states.pop(str(user_id), None)

# ==================== MAIN LOOP ====================

# Global states
user_states = {}
offset = 0

def main():
    """Main polling loop"""
    global offset
    
    print("\n" + "="*60)
    print("🤖 REFi BOT - COMPLETE VERSION")
    print("="*60)
    print(f"📱 Token: {BOT_TOKEN[:15]}...")
    print(f"👤 Admins: {ADMIN_IDS}")
    print(f"💰 Welcome: {db.format_refi(WELCOME_BONUS)}")
    print(f"👥 Referral: {db.format_refi(REFERRAL_BONUS)}")
    print(f"💸 Min withdraw: {db.format_refi(MIN_WITHDRAW)}")
    print(f"👥 Total users: {len(db.users)}")
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
                    update_id = update["update_id"]
                    
                    # Process message
                    if "message" in update:
                        msg = update["message"]
                        chat_id = msg["chat"]["id"]
                        user_id = str(msg["from"]["id"])
                        text = msg.get("text", "")
                        
                        # Check if user is banned
                        user_data = db.get_user(user_id)
                        if user_data.get("is_banned", False):
                            send_message(chat_id, "⛔ You are banned from using this bot.")
                            offset = update_id + 1
                            continue
                        
                        # Handle commands
                        if text == "/start":
                            handle_start(msg)
                        elif text == "/admin":
                            handle_admin_command(msg)
                        elif text.startswith("/"):
                            send_message(chat_id, "❌ Unknown command. Use /start")
                        else:
                            # Handle state-based input
                            state = user_states.get(user_id, {}).get("action")
                            if state == "waiting_amount":
                                handle_withdraw_amount(msg, user_id, chat_id)
                            elif state == "waiting_wallet":
                                handle_wallet(msg, user_id, chat_id)
                            elif state == "admin_login":
                                handle_admin_login_input(msg, user_id, chat_id)
                            elif state == "admin_search":
                                handle_admin_search_input(msg, user_id, chat_id)
                            elif state == "admin_broadcast":
                                handle_admin_broadcast_input(msg, user_id, chat_id)
                    
                    # Process callback query
                    elif "callback_query" in update:
                        callback = update["callback_query"]
                        data = callback.get("data", "")
                        user_id = str(callback["from"]["id"])
                        chat_id = callback["message"]["chat"]["id"]
                        message_id = callback["message"]["message_id"]
                        
                        answer_callback(callback["id"])
                        
                        # Check if user is banned
                        user_data = db.get_user(user_id)
                        if user_data.get("is_banned", False):
                            send_message(chat_id, "⛔ You are banned from using this bot.")
                            offset = update_id + 1
                            continue
                        
                        # Handle callbacks
                        if data == "verify":
                            handle_verify(callback, user_id, chat_id, message_id)
                        elif data == "balance":
                            handle_balance(callback, user_id, chat_id, message_id)
                        elif data == "referral":
                            handle_referral(callback, user_id, chat_id, message_id)
                        elif data == "stats":
                            handle_stats(callback, user_id, chat_id, message_id)
                        elif data == "withdraw":
                            handle_withdraw(callback, user_id, chat_id, message_id)
                        elif data == "back":
                            handle_back(callback, user_id, chat_id, message_id)
                        elif data == "admin_panel":
                            handle_admin_panel(callback, user_id, chat_id, message_id)
                        elif data == "admin_stats":
                            handle_admin_stats(callback, user_id, chat_id, message_id)
                        elif data == "admin_withdrawals":
                            handle_admin_withdrawals(callback, user_id, chat_id, message_id)
                        elif data == "admin_search":
                            handle_admin_search(callback, user_id, chat_id, message_id)
                        elif data == "admin_broadcast":
                            handle_admin_broadcast(callback, user_id, chat_id, message_id)
                        elif data == "admin_users":
                            handle_admin_users(callback, user_id, chat_id, message_id)
                        elif data == "admin_logout":
                            handle_admin_logout(callback, user_id, chat_id, message_id)
                        elif data.startswith("process_"):
                            request_id = data[8:]
                            handle_process_withdrawal(callback, user_id, chat_id, message_id, request_id)
                        elif data.startswith("approve_"):
                            request_id = data[8:]
                            handle_approve_withdrawal(callback, user_id, chat_id, message_id, request_id)
                        elif data.startswith("reject_"):
                            request_id = data[7:]
                            handle_reject_withdrawal(callback, user_id, chat_id, message_id, request_id)
                    
                    offset = update_id + 1
            
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            logger.error(f"Polling error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal")

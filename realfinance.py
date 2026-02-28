#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
🤖 REFi REFERRAL BOT - PROFESSIONAL EDITION
=========================================================
A complete Telegram referral & earn bot with admin panel,
channel verification, withdrawal system, and REFi token rewards.

Author: Professional Development
Version: 3.0.0 (Production Ready)
Last Updated: 2026-02-28
=========================================================
"""

# ==================== STANDARD LIBRARY IMPORTS ====================
import os
import sys
import logging
import time
import json
import hashlib
import hmac
import random
import string
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any, Union, Callable
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field, asdict
from collections import defaultdict, deque
from threading import Lock
import traceback

# ==================== THIRD-PARTY IMPORTS ====================
try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application,
        CommandHandler,
        MessageHandler,
        CallbackQueryHandler,
        filters,
        ContextTypes,
        ConversationHandler,
        Defaults
    )
    from telegram.constants import ParseMode
    from telegram.error import TelegramError, TimedOut, NetworkError
    import nest_asyncio
    nest_asyncio.apply()
except ImportError as e:
    print(f"❌ Missing required library: {e}")
    print("📦 Please install: pip install python-telegram-bot nest-asyncio")
    sys.exit(1)

# ==================== CONFIGURATION ====================

class Config:
    """Centralized configuration management"""
    
    # ========== BOT SETTINGS ==========
    BOT_TOKEN = os.environ.get('BOT_TOKEN', "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs")
    BOT_USERNAME = "Realfinancepaybot"
    BOT_NAME = "REFi Earn Bot"
    
    # ========== ADMIN SETTINGS ==========
    ADMIN_IDS = [1653918641]  # List of admin user IDs
    ADMIN_PASSWORD = "Ali97$"  # Admin password (change this!)
    
    # ========== TOKENOMICS ==========
    COIN_NAME = "REFi"
    COIN_SYMBOL = "REFi"
    
    # 1 million REFi = $2 USD (fixed rate)
    REFI_PER_MILLION = 2.0  # USD per 1M REFi
    WELCOME_BONUS = 1_000_000  # 1,000,000 REFi
    REFERRAL_BONUS = 1_000_000  # 1,000,000 REFi per referral
    MIN_WITHDRAW = 5_000_000  # Minimum 5,000,000 REFi to withdraw
    
    # ========== CHANNEL REQUIREMENTS ==========
    REQUIRED_CHANNELS = [
        {
            "name": "REFi Distribution",
            "username": "@Realfinance_REFI",
            "link": "https://t.me/Realfinance_REFI",
            "id": "@Realfinance_REFI"
        },
        {
            "name": "Airdrop Master VIP",
            "username": "@Airdrop_MasterVIP",
            "link": "https://t.me/Airdrop_MasterVIP",
            "id": "@Airdrop_MasterVIP"
        },
        {
            "name": "Daily Airdrop",
            "username": "@Daily_AirdropX",
            "link": "https://t.me/Daily_AirdropX",
            "id": "@Daily_AirdropX"
        }
    ]
    
    # ========== LIMITS & RESTRICTIONS ==========
    MAX_PENDING_WITHDRAWALS = 3  # Max pending withdrawals per user
    MAX_REFERRALS_PER_DAY = 50  # Anti-spam
    DAILY_WITHDRAWAL_LIMIT = 10_000_000  # Max 10M REFi per day
    SESSION_TIMEOUT = 3600  # 1 hour in seconds
    REQUEST_TIMEOUT = 30  # HTTP request timeout
    
    # ========== LOGGING SETTINGS ==========
    LOG_LEVEL = logging.INFO
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = 'bot.log'
    
    # ========== PERFORMANCE SETTINGS ==========
    CONCURRENT_WORKERS = 4
    POLLING_TIMEOUT = 30
    POLLING_READ_TIMEOUT = 30
    POLLING_CONNECT_TIMEOUT = 30
    POLLING_POOL_TIMEOUT = 30
    
    # ========== VALIDATION ==========
    @classmethod
    def validate(cls) -> bool:
        """Validate critical configuration"""
        if not cls.BOT_TOKEN or len(cls.BOT_TOKEN) < 40:
            raise ValueError("❌ Invalid BOT_TOKEN")
        if not cls.ADMIN_IDS:
            raise ValueError("❌ No ADMIN_IDS configured")
        if cls.MIN_WITHDRAW <= 0:
            raise ValueError("❌ MIN_WITHDRAW must be positive")
        return True

# ==================== LOGGING SETUP ====================

def setup_logging():
    """Configure logging with both file and console handlers"""
    # Create logger
    logger = logging.getLogger()
    logger.setLevel(Config.LOG_LEVEL)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Create formatters
    formatter = logging.Formatter(Config.LOG_FORMAT)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler
    try:
        file_handler = logging.FileHandler(Config.LOG_FILE)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except Exception as e:
        print(f"⚠️ Could not create log file: {e}")
    
    return logger

# Initialize logger
logger = setup_logging()

# ==================== ENUMS ====================

class UserState(Enum):
    """User conversation states"""
    IDLE = 0
    WAITING_ADMIN_PASS = 1
    WAITING_WITHDRAW_AMOUNT = 2
    WAITING_WALLET_ADDRESS = 3
    WAITING_ADMIN_SEARCH = 4
    WAITING_ADMIN_BROADCAST = 5
    WAITING_ADMIN_USER_ID = 6

class VerificationStatus(Enum):
    """User verification status"""
    UNVERIFIED = "unverified"
    VERIFIED = "verified"
    BANNED = "banned"

class WithdrawalStatus(Enum):
    """Withdrawal request status"""
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

# ==================== DATA MODELS ====================

@dataclass
class User:
    """User data model"""
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    language: str = "en"
    
    joined_at: float = field(default_factory=time.time)
    last_active: float = field(default_factory=time.time)
    
    balance: int = 0
    total_earned: int = 0
    total_withdrawn: int = 0
    
    referral_code: str = ""
    referred_by: Optional[int] = None
    referrals_count: int = 0
    referrals: Dict[str, float] = field(default_factory=dict)
    referral_clicks: int = 0
    
    verification_status: VerificationStatus = VerificationStatus.UNVERIFIED
    verified_at: Optional[float] = None
    
    wallet_address: Optional[str] = None
    
    is_admin: bool = False
    is_banned: bool = False
    
    daily_referrals: Dict[str, int] = field(default_factory=dict)
    daily_withdrawals: int = 0
    last_withdrawal_date: Optional[str] = None
    
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'language': self.language,
            'joined_at': self.joined_at,
            'last_active': self.last_active,
            'balance': self.balance,
            'total_earned': self.total_earned,
            'total_withdrawn': self.total_withdrawn,
            'referral_code': self.referral_code,
            'referred_by': self.referred_by,
            'referrals_count': self.referrals_count,
            'referrals': self.referrals,
            'referral_clicks': self.referral_clicks,
            'verification_status': self.verification_status.value,
            'verified_at': self.verified_at,
            'wallet_address': self.wallet_address,
            'is_admin': self.is_admin,
            'is_banned': self.is_banned,
            'daily_referrals': self.daily_referrals,
            'daily_withdrawals': self.daily_withdrawals,
            'last_withdrawal_date': self.last_withdrawal_date,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create from dictionary"""
        user = cls(user_id=data['user_id'])
        user.username = data.get('username', '')
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
        user.language = data.get('language', 'en')
        user.joined_at = data.get('joined_at', time.time())
        user.last_active = data.get('last_active', time.time())
        user.balance = data.get('balance', 0)
        user.total_earned = data.get('total_earned', 0)
        user.total_withdrawn = data.get('total_withdrawn', 0)
        user.referral_code = data.get('referral_code', '')
        user.referred_by = data.get('referred_by')
        user.referrals_count = data.get('referrals_count', 0)
        user.referrals = data.get('referrals', {})
        user.referral_clicks = data.get('referral_clicks', 0)
        
        status = data.get('verification_status', 'unverified')
        user.verification_status = VerificationStatus(status)
        
        user.verified_at = data.get('verified_at')
        user.wallet_address = data.get('wallet_address')
        user.is_admin = data.get('is_admin', False)
        user.is_banned = data.get('is_banned', False)
        user.daily_referrals = data.get('daily_referrals', {})
        user.daily_withdrawals = data.get('daily_withdrawals', 0)
        user.last_withdrawal_date = data.get('last_withdrawal_date')
        user.notes = data.get('notes', '')
        return user
    
    def update_activity(self):
        """Update last activity timestamp"""
        self.last_active = time.time()

@dataclass
class Withdrawal:
    """Withdrawal request model"""
    request_id: str
    user_id: int
    amount: int
    wallet_address: str
    status: WithdrawalStatus
    created_at: float
    processed_at: Optional[float] = None
    processed_by: Optional[int] = None
    tx_hash: Optional[str] = None
    notes: str = ""
    
    def to_dict(self) -> dict:
        """Convert to dictionary for storage"""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'wallet_address': self.wallet_address,
            'status': self.status.value,
            'created_at': self.created_at,
            'processed_at': self.processed_at,
            'processed_by': self.processed_by,
            'tx_hash': self.tx_hash,
            'notes': self.notes
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Withdrawal':
        """Create from dictionary"""
        req = cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            amount=data['amount'],
            wallet_address=data['wallet_address'],
            status=WithdrawalStatus(data['status']),
            created_at=data['created_at']
        )
        req.processed_at = data.get('processed_at')
        req.processed_by = data.get('processed_by')
        req.tx_hash = data.get('tx_hash')
        req.notes = data.get('notes', '')
        return req

# ==================== DATABASE LAYER ====================

class Database:
    """Thread-safe in-memory database with persistence"""
    
    _instance = None
    _lock = Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
            return cls._instance
    
    def _initialize(self):
        """Initialize database"""
        self.users: Dict[int, User] = {}
        self.withdrawals: Dict[str, Withdrawal] = {}
        self.admin_sessions: Dict[int, float] = {}
        self.stats_lock = Lock()
        
        self.stats = {
            'total_users': 0,
            'total_verified': 0,
            'total_withdrawals': 0,
            'total_withdrawn_amount': 0,
            'total_referrals': 0,
            'bot_start_time': time.time(),
            'commands_processed': 0
        }
        
        # Load data if exists
        self._load()
        logger.info("✅ Database initialized")
    
    # ========== PERSISTENCE ==========
    
    def _save(self):
        """Save data to file (optional)"""
        try:
            data = {
                'users': {str(uid): u.to_dict() for uid, u in self.users.items()},
                'withdrawals': {wid: w.to_dict() for wid, w in self.withdrawals.items()},
                'stats': self.stats
            }
            with open('bot_data.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
    
    def _load(self):
        """Load data from file (optional)"""
        try:
            if os.path.exists('bot_data.json'):
                with open('bot_data.json', 'r') as f:
                    data = json.load(f)
                
                # Load users
                for uid_str, u_data in data.get('users', {}).items():
                    self.users[int(uid_str)] = User.from_dict(u_data)
                
                # Load withdrawals
                for wid, w_data in data.get('withdrawals', {}).items():
                    self.withdrawals[wid] = Withdrawal.from_dict(w_data)
                
                # Load stats
                self.stats.update(data.get('stats', {}))
                
                logger.info(f"📂 Loaded {len(self.users)} users, {len(self.withdrawals)} withdrawals")
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
    
    # ========== USER OPERATIONS ==========
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self._lock:
            return self.users.get(user_id)
    
    def create_user(self, user_id: int, **kwargs) -> User:
        """Create new user"""
        with self._lock:
            user = User(user_id=user_id, **kwargs)
            user.referral_code = self._generate_referral_code(user_id)
            self.users[user_id] = user
            self.stats['total_users'] += 1
            self._save()
            logger.info(f"👤 New user: {user_id} (@{user.username})")
            return user
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        """Update user data"""
        with self._lock:
            user = self.get_user(user_id)
            if user:
                for key, value in kwargs.items():
                    if hasattr(user, key):
                        setattr(user, key, value)
                user.update_activity()
                self._save()
            return user
    
    def get_or_create_user(self, user_id: int, **kwargs) -> User:
        """Get existing user or create new one"""
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, **kwargs)
        return user
    
    def get_user_by_referral_code(self, code: str) -> Optional[User]:
        """Find user by referral code"""
        with self._lock:
            for user in self.users.values():
                if user.referral_code == code:
                    return user
            return None
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Find user by username (without @)"""
        username = username.lower().lstrip('@')
        with self._lock:
            for user in self.users.values():
                if user.username and user.username.lower() == username:
                    return user
            return None
    
    # ========== REFERRAL OPERATIONS ==========
    
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Add a successful referral"""
        with self._lock:
            referrer = self.get_user(referrer_id)
            referred = self.get_user(referred_id)
            
            if not referrer or not referred:
                return False
            
            # Check if already referred
            if str(referred_id) in referrer.referrals:
                return False
            
            # Add referral
            referrer.referrals[str(referred_id)] = time.time()
            referrer.referrals_count += 1
            referrer.balance += Config.REFERRAL_BONUS
            referrer.total_earned += Config.REFERRAL_BONUS
            
            # Update daily stats
            today = datetime.now().strftime('%Y-%m-%d')
            referrer.daily_referrals[today] = referrer.daily_referrals.get(today, 0) + 1
            
            self.stats['total_referrals'] += 1
            self._save()
            
            logger.info(f"✅ Referral: {referrer_id} -> {referred_id}")
            return True
    
    # ========== WITHDRAWAL OPERATIONS ==========
    
    def create_withdrawal(self, user_id: int, amount: int, wallet: str) -> Withdrawal:
        """Create withdrawal request"""
        with self._lock:
            request_id = self._generate_request_id(user_id)
            withdrawal = Withdrawal(
                request_id=request_id,
                user_id=user_id,
                amount=amount,
                wallet_address=wallet,
                status=WithdrawalStatus.PENDING,
                created_at=time.time()
            )
            self.withdrawals[request_id] = withdrawal
            self._save()
            logger.info(f"💰 New withdrawal: {request_id} from {user_id} for {amount}")
            return withdrawal
    
    def get_withdrawal(self, request_id: str) -> Optional[Withdrawal]:
        """Get withdrawal by ID"""
        with self._lock:
            return self.withdrawals.get(request_id)
    
    def get_user_withdrawals(self, user_id: int, status: Optional[WithdrawalStatus] = None) -> List[Withdrawal]:
        """Get all withdrawals for a user"""
        with self._lock:
            withdrawals = [w for w in self.withdrawals.values() if w.user_id == user_id]
            if status:
                withdrawals = [w for w in withdrawals if w.status == status]
            return sorted(withdrawals, key=lambda w: w.created_at, reverse=True)
    
    def get_pending_withdrawals(self) -> List[Withdrawal]:
        """Get all pending withdrawals"""
        with self._lock:
            return [w for w in self.withdrawals.values() 
                   if w.status == WithdrawalStatus.PENDING]
    
    def process_withdrawal(self, request_id: str, admin_id: int, 
                          status: WithdrawalStatus, tx_hash: str = None) -> bool:
        """Process a withdrawal request"""
        with self._lock:
            withdrawal = self.get_withdrawal(request_id)
            if not withdrawal or withdrawal.status != WithdrawalStatus.PENDING:
                return False
            
            withdrawal.status = status
            withdrawal.processed_at = time.time()
            withdrawal.processed_by = admin_id
            withdrawal.tx_hash = tx_hash
            
            if status == WithdrawalStatus.APPROVED:
                self.stats['total_withdrawals'] += 1
                self.stats['total_withdrawn_amount'] += withdrawal.amount
                
                # Update user
                user = self.get_user(withdrawal.user_id)
                if user:
                    user.total_withdrawn += withdrawal.amount
                    user.daily_withdrawals += withdrawal.amount
                    user.last_withdrawal_date = datetime.now().strftime('%Y-%m-%d')
            
            self._save()
            logger.info(f"✅ Withdrawal {request_id} processed: {status.value}")
            return True
    
    # ========== ADMIN SESSIONS ==========
    
    def create_admin_session(self, user_id: int) -> None:
        """Create admin session"""
        with self._lock:
            self.admin_sessions[user_id] = time.time() + Config.SESSION_TIMEOUT
    
    def is_admin_session_valid(self, user_id: int) -> bool:
        """Check if admin session is valid"""
        with self._lock:
            if user_id not in self.admin_sessions:
                return False
            if self.admin_sessions[user_id] < time.time():
                del self.admin_sessions[user_id]
                return False
            return True
    
    def end_admin_session(self, user_id: int) -> None:
        """End admin session"""
        with self._lock:
            self.admin_sessions.pop(user_id, None)
    
    # ========== STATISTICS ==========
    
    def get_stats(self) -> dict:
        """Get bot statistics"""
        with self.stats_lock:
            stats = self.stats.copy()
            stats['users_verified'] = sum(1 for u in self.users.values() 
                                        if u.verification_status == VerificationStatus.VERIFIED)
            stats['users_banned'] = sum(1 for u in self.users.values() if u.is_banned)
            stats['total_balance'] = sum(u.balance for u in self.users.values())
            stats['pending_withdrawals'] = len(self.get_pending_withdrawals())
            stats['uptime'] = int(time.time() - stats['bot_start_time'])
            return stats
    
    def increment_command_count(self):
        """Increment command counter"""
        with self.stats_lock:
            self.stats['commands_processed'] += 1
    
    # ========== HELPER METHODS ==========
    
    def _generate_referral_code(self, user_id: int) -> str:
        """Generate unique referral code"""
        while True:
            # Create code from user_id + random
            random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            code = f"{user_id}{random_part}"[:8]
            
            # Ensure uniqueness
            existing = self.get_user_by_referral_code(code)
            if not existing:
                return code
    
    def _generate_request_id(self, user_id: int) -> str:
        """Generate unique request ID"""
        timestamp = int(time.time())
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"W{timestamp}{user_id}{random_part}"

# Initialize database
db = Database()

# ==================== UTILITY CLASS ====================

class Utils:
    """Utility functions"""
    
    @staticmethod
    def format_number(num: int) -> str:
        """Format number with commas"""
        return f"{num:,}"
    
    @staticmethod
    def refi_to_usd(refi: int) -> float:
        """Convert REFi to USD (1M = $2)"""
        return (refi / 1_000_000) * 2.0
    
    @staticmethod
    def usd_to_refi(usd: float) -> int:
        """Convert USD to REFi"""
        return int((usd / 2.0) * 1_000_000)
    
    @staticmethod
    def short_wallet(wallet: str, chars: int = 6) -> str:
        """Shorten wallet address for display"""
        if not wallet or len(wallet) <= 16:
            return wallet or "Not set"
        return f"{wallet[:chars]}...{wallet[-chars:]}"
    
    @staticmethod
    def is_valid_eth_wallet(wallet: str) -> bool:
        """Validate Ethereum wallet address"""
        if not wallet or not isinstance(wallet, str):
            return False
        wallet = wallet.strip()
        if not wallet.startswith('0x'):
            return False
        if len(wallet) != 42:
            return False
        try:
            int(wallet[2:], 16)
            return True
        except ValueError:
            return False
    
    @staticmethod
    def get_date(timestamp: float = None, format: str = '%Y-%m-%d %H:%M') -> str:
        """Get formatted date"""
        dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
        return dt.strftime(format)
    
    @staticmethod
    def get_today() -> str:
        """Get today's date string"""
        return datetime.now().strftime('%Y-%m-%d')
    
    @staticmethod
    def escape_markdown(text: str) -> str:
        """Escape Markdown special characters"""
        special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
        for char in special_chars:
            text = text.replace(char, f'\\{char}')
        return text
    
    @staticmethod
    def safe_send(func: Callable) -> Callable:
        """Decorator to safely send messages"""
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except TimedOut:
                logger.warning("Request timed out")
            except NetworkError as e:
                logger.error(f"Network error: {e}")
            except TelegramError as e:
                logger.error(f"Telegram error: {e}")
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
            return None
        return wrapper

# ==================== DECORATORS ====================

def admin_required(func: Callable) -> Callable:
    """Decorator to check if user is admin with active session"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text(
                "⛔ You are not authorized to use this command.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        if not db.is_admin_session_valid(user.id):
            await update.message.reply_text(
                "🔐 Please login first with /admin",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def registered_user_required(func: Callable) -> Callable:
    """Decorator to ensure user is registered"""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user = update.effective_user
        if not user:
            return
        
        # Get or create user
        user_data = db.get_or_create_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or "",
            last_name=user.last_name or "",
            language=user.language_code or "en"
        )
        
        # Check if banned
        if user_data.is_banned:
            await update.message.reply_text(
                "⛔ You are banned from using this bot.",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Add user data to context
        context.user_data['user'] = user_data
        db.increment_command_count()
        
        return await func(update, context, *args, **kwargs)
    return wrapper

def log_errors(func: Callable) -> Callable:
    """Decorator to log errors"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}\n{traceback.format_exc()}")
            raise
    return wrapper

# ==================== KEYBOARDS ====================

class Keyboards:
    """All keyboard layouts"""
    
    @staticmethod
    def channels() -> InlineKeyboardMarkup:
        """Channels verification keyboard"""
        keyboard = []
        for channel in Config.REQUIRED_CHANNELS:
            keyboard.append([InlineKeyboardButton(
                text=f"📢 Join {channel['name']}",
                url=channel['link']
            )])
        keyboard.append([InlineKeyboardButton(
            text="✅ Verify Membership",
            callback_data="verify"
        )])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def main(user: User = None) -> InlineKeyboardMarkup:
        """Main menu keyboard"""
        keyboard = [
            [
                InlineKeyboardButton("💰 Balance", callback_data="balance"),
                InlineKeyboardButton("🔗 Referral", callback_data="referral")
            ],
            [
                InlineKeyboardButton("💸 Withdraw", callback_data="withdraw"),
                InlineKeyboardButton("📊 Stats", callback_data="stats")
            ]
        ]
        
        # Add admin button for admins
        if user and user.is_admin:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
        
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back() -> InlineKeyboardMarkup:
        """Back button only"""
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="main_menu")
        ]])
    
    @staticmethod
    def admin() -> InlineKeyboardMarkup:
        """Admin panel keyboard"""
        keyboard = [
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Pending Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_search")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("👥 Users List", callback_data="admin_users")],
            [InlineKeyboardButton("🔒 Logout", callback_data="admin_logout")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def withdrawal_actions(request_id: str) -> InlineKeyboardMarkup:
        """Withdrawal action buttons for admin"""
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_withdrawals")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def user_actions(user_id: int, is_banned: bool, is_admin: bool) -> InlineKeyboardMarkup:
        """User management buttons for admin"""
        keyboard = []
        
        # Ban/Unban button
        if is_banned:
            keyboard.append([InlineKeyboardButton("✅ Unban User", callback_data=f"unban_{user_id}")])
        else:
            keyboard.append([InlineKeyboardButton("🔨 Ban User", callback_data=f"ban_{user_id}")])
        
        # Make/Remove admin button
        if is_admin:
            keyboard.append([InlineKeyboardButton("👤 Remove Admin", callback_data=f"remove_admin_{user_id}")])
        else:
            keyboard.append([InlineKeyboardButton("👑 Make Admin", callback_data=f"make_admin_{user_id}")])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
        
        return InlineKeyboardMarkup(keyboard)

# ==================== MESSAGE TEMPLATES ====================

class Messages:
    """All message templates"""
    
    WELCOME = (
        "🎉 *Welcome to REFi Earn Bot!*\n\n"
        "💰 *Welcome Bonus:* {welcome:,} REFi (${welcome_usd:.2f})\n"
        "👥 *Referral Bonus:* {referral:,} REFi (${referral_usd:.2f}) per friend\n\n"
        "📢 *To start, you must join these channels:*\n{channels}\n\n"
        "👇 Click 'Verify' after joining"
    )
    
    VERIFY_SUCCESS = (
        "✅ *Verification Successful!*\n\n"
        "✨ Added {welcome:,} REFi to your balance\n"
        "💰 Current balance: {balance:,} REFi (${balance_usd:.2f})\n\n"
        "👥 Share your referral link and earn {referral:,} REFi per friend!"
    )
    
    VERIFY_FAILED = (
        "❌ *Verification Failed*\n\n"
        "You haven't joined these channels yet:\n{not_joined}\n\n"
        "Please join them and try again."
    )
    
    MAIN_MENU = (
        "🎯 *Main Menu*\n\n"
        "💰 Balance: {balance:,} REFi (${balance_usd:.2f})\n"
        "👥 Referrals: {referrals}\n"
        "📊 Total earned: {total_earned:,} REFi (${total_earned_usd:.2f})\n\n"
        "Choose an option below:"
    )
    
    BALANCE = (
        "💰 *Your Balance*\n\n"
        "• REFi: `{balance:,}`\n"
        "• USD: `${balance_usd:.2f}`\n\n"
        "📊 *Statistics*\n"
        "• Total referrals: {referrals}\n"
        "• Total earned: `{total_earned:,}` REFi (${total_earned_usd:.2f})\n"
        "• Referral earnings: `{ref_earned:,}` REFi (${ref_earned_usd:.2f})\n"
        "• Join date: {join_date}"
    )
    
    REFERRAL = (
        "🔗 *Your Referral Link*\n\n"
        "`{link}`\n\n"
        "🎁 *Rewards*\n"
        "• You get: {referral:,} REFi (${referral_usd:.2f}) per referral\n"
        "• Friend gets: {welcome:,} REFi (${welcome_usd:.2f})\n\n"
        "📊 *Stats*\n"
        "• Total clicks: {clicks}\n"
        "• Successful referrals: {successful}\n"
        "• Earnings from referrals: {earned:,} REFi (${earned_usd:.2f})\n\n"
        "Share this link with your friends!"
    )
    
    WITHDRAW_MENU = (
        "💸 *Withdrawal*\n\n"
        "💰 Your balance: {balance:,} REFi (${balance_usd:.2f})\n"
        "📉 Minimum: {min_withdraw:,} REFi (${min_withdraw_usd:.2f})\n"
        "⏳ Pending requests: {pending}\n\n"
        "Enter the amount you want to withdraw:"
    )
    
    WITHDRAW_SUCCESS = (
        "✅ *Withdrawal Request Submitted!*\n\n"
        "📝 Request ID: `{request_id}`\n"
        "💰 Amount: {amount:,} REFi (${amount_usd:.2f})\n"
        "📮 Wallet: `{wallet_short}`\n\n"
        "⏳ Status: *Pending Review*\n"
        "You'll be notified when processed."
    )
    
    WITHDRAW_INSUFFICIENT = (
        "⚠️ *Insufficient Balance*\n\n"
        "Your balance: {balance:,} REFi (${balance_usd:.2f})\n"
        "Requested: {amount:,} REFi (${amount_usd:.2f})\n\n"
        "Please enter a smaller amount."
    )
    
    WITHDRAW_BELOW_MIN = (
        "⚠️ *Below Minimum Withdrawal*\n\n"
        "Minimum: {min:,} REFi (${min_usd:.2f})\n"
        "Your balance: {balance:,} REFi (${balance_usd:.2f})\n\n"
        "You need {needed:,} more REFi to withdraw."
    )
    
    WITHDRAW_PENDING_LIMIT = (
        "⚠️ *Pending Withdrawals Limit*\n\n"
        "You already have {count} pending withdrawals.\n"
        "Maximum allowed is {max_count}.\n\n"
        "Please wait for them to be processed."
    )
    
    WITHDRAW_DAILY_LIMIT = (
        "⚠️ *Daily Withdrawal Limit*\n\n"
        "You've reached your daily limit of {limit:,} REFi.\n"
        "Please try again tomorrow."
    )
    
    WITHDRAW_APPROVED_USER = (
        "✅ *Withdrawal Approved!*\n\n"
        "Request ID: `{request_id}`\n"
        "Amount: {amount:,} REFi (${amount_usd:.2f})\n"
        "Wallet: {wallet}\n\n"
        "Your withdrawal has been approved and will be processed shortly."
    )
    
    WITHDRAW_REJECTED_USER = (
        "❌ *Withdrawal Rejected*\n\n"
        "Request ID: `{request_id}`\n"
        "Amount: {amount:,} REFi (${amount_usd:.2f})\n\n"
        "Your withdrawal request was rejected.\n"
        "Reason: {reason}\n\n"
        "The amount has been returned to your balance."
    )
    
    ADMIN_PANEL = (
        "👑 *Admin Panel*\n\n"
        "📊 *Statistics*\n"
        "• Total users: {total_users}\n"
        "• Verified users: {verified}\n"
        "• Banned users: {banned}\n"
        "• Total balance: {total_balance:,} REFi\n"
        "• Total withdrawals: {total_withdrawals}\n"
        "• Total withdrawn: {total_withdrawn:,} REFi\n"
        "• Pending withdrawals: {pending_withdrawals}\n"
        "• Uptime: {uptime}\n\n"
        "Choose an option:"
    )
    
    ADMIN_STATS = (
        "📊 *Detailed Statistics*\n\n"
        "👥 *Users*\n"
        "• Total: {total_users}\n"
        "• Verified: {verified}\n"
        "• Unverified: {unverified}\n"
        "• Banned: {banned}\n"
        "• Active today: {active_today}\n"
        "• Active week: {active_week}\n\n"
        "💰 *Financial*\n"
        "• Total balance: {total_balance:,} REFi\n"
        "• Total earned: {total_earned:,} REFi\n"
        "• Total withdrawn: {total_withdrawn:,} REFi\n"
        "• Avg balance: {avg_balance:,} REFi\n\n"
        "📈 *Referrals*\n"
        "• Total referrals: {total_referrals}\n"
        "• Avg per user: {avg_referrals:.2f}\n"
        "• Top referrer: {top_referrer}\n\n"
        "⏱️ *Bot Stats*\n"
        "• Commands processed: {commands}\n"
        "• Uptime: {uptime}\n"
        "• Start time: {start_time}"
    )
    
    ADMIN_USER_INFO = (
        "👤 *User Information*\n\n"
        "• ID: `{user_id}`\n"
        "• Username: @{username}\n"
        "• Name: {first_name} {last_name}\n"
        "• Language: {language}\n"
        "• Joined: {joined_at}\n"
        "• Last active: {last_active}\n\n"
        "💰 *Financial*\n"
        "• Balance: {balance:,} REFi (${balance_usd:.2f})\n"
        "• Total earned: {total_earned:,} REFi (${total_earned_usd:.2f})\n"
        "• Total withdrawn: {total_withdrawn:,} REFi (${total_withdrawn_usd:.2f})\n"
        "• Pending withdrawals: {pending_withdrawals}\n\n"
        "👥 *Referrals*\n"
        "• Total: {referrals_count}\n"
        "• Code: `{referral_code}`\n"
        "• Referred by: {referred_by}\n"
        "• Clicks: {referral_clicks}\n\n"
        "✅ *Status*\n"
        "• Verified: {verified}\n"
        "• Wallet: {wallet}\n"
        "• Admin: {admin}\n"
        "• Banned: {banned}"
    )
    
    ERROR = "❌ *Error*: {error}"
    UNAUTHORIZED = "⛔ You are not authorized to use this command."

# ==================== HANDLERS ====================

class Handlers:
    """All command and callback handlers"""
    
    # ========== START & REGISTRATION ==========
    
    @staticmethod
    @log_errors
    @registered_user_required
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        args = context.args
        user_data = context.user_data['user']
        
        # Check for referral code
        if args and args[0]:
            referral_code = args[0]
            
            # Don't process self-referral
            if referral_code != user_data.referral_code:
                referrer = db.get_user_by_referral_code(referral_code)
                if referrer and not user_data.referred_by:
                    user_data.referred_by = referrer.user_id
                    
                    # Update referral click stats
                    referrer.referral_clicks += 1
                    db.update_user(referrer.user_id, referral_clicks=referrer.referral_clicks)
                    
                    logger.info(f"📋 Referral click: {referrer.user_id} -> {user.id}")
        
        # Check if already verified
        if user_data.verification_status == VerificationStatus.VERIFIED:
            await Handlers._show_main_menu(update, context, user_data)
            return
        
        # Show channels for verification
        channels_text = "\n".join([f"• {ch['name']}: {ch['link']}" 
                                   for ch in Config.REQUIRED_CHANNELS])
        
        await update.message.reply_text(
            Messages.WELCOME.format(
                welcome=Utils.format_number(Config.WELCOME_BONUS),
                welcome_usd=Utils.refi_to_usd(Config.WELCOME_BONUS),
                referral=Utils.format_number(Config.REFERRAL_BONUS),
                referral_usd=Utils.refi_to_usd(Config.REFERRAL_BONUS),
                channels=channels_text
            ),
            reply_markup=Keyboards.channels(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle verify button callback"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        # Check channel membership
        is_member, not_joined = await Handlers._check_channels(user_id, context)
        
        if is_member:
            # Check if already verified
            if user_data.verification_status == VerificationStatus.VERIFIED:
                await Handlers._show_main_menu(update, context, user_data, query)
                return
            
            # Verify user
            user_data.verification_status = VerificationStatus.VERIFIED
            user_data.verified_at = time.time()
            
            # Add welcome bonus
            user_data.balance += Config.WELCOME_BONUS
            user_data.total_earned += Config.WELCOME_BONUS
            
            # Process referral if any
            if user_data.referred_by:
                referrer = db.get_user(user_data.referred_by)
                if referrer and referrer.verification_status == VerificationStatus.VERIFIED:
                    db.add_referral(referrer.user_id, user_id)
                    
                    # Notify referrer
                    try:
                        await context.bot.send_message(
                            chat_id=referrer.user_id,
                            text=(
                                f"🎉 *Congratulations!*\n\n"
                                f"Your friend {user_data.first_name} joined using your link!\n"
                                f"✨ You earned {Utils.format_number(Config.REFERRAL_BONUS)} REFi "
                                f"(${Utils.refi_to_usd(Config.REFERRAL_BONUS):.2f})"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify referrer {referrer.user_id}: {e}")
            
            # Save user
            db.update_user(user_id,
                          verification_status=user_data.verification_status,
                          verified_at=user_data.verified_at,
                          balance=user_data.balance,
                          total_earned=user_data.total_earned)
            
            await query.edit_message_text(
                Messages.VERIFY_SUCCESS.format(
                    welcome=Utils.format_number(Config.WELCOME_BONUS),
                    balance=Utils.format_number(user_data.balance),
                    balance_usd=Utils.refi_to_usd(user_data.balance),
                    referral=Utils.format_number(Config.REFERRAL_BONUS)
                ),
                reply_markup=Keyboards.main(user_data),
                parse_mode=ParseMode.MARKDOWN
            )
            
            logger.info(f"✅ User {user_id} verified")
        else:
            not_joined_text = "\n".join([f"• {ch}" for ch in not_joined])
            await query.edit_message_text(
                Messages.VERIFY_FAILED.format(not_joined=not_joined_text),
                reply_markup=Keyboards.channels(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    @staticmethod
    async def _check_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
        """Check if user has joined all required channels"""
        not_joined = []
        
        for channel in Config.REQUIRED_CHANNELS:
            try:
                member = await context.bot.get_chat_member(
                    chat_id=channel['username'],
                    user_id=user_id
                )
                if member.status in ['left', 'kicked']:
                    not_joined.append(channel['name'])
            except Exception as e:
                logger.error(f"Channel check failed for {channel['name']}: {e}")
                not_joined.append(channel['name'])
        
        return len(not_joined) == 0, not_joined
    
    # ========== MAIN MENU ==========
    
    @staticmethod
    @log_errors
    async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Return to main menu"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        await Handlers._show_main_menu(update, context, user_data, query)
    
    @staticmethod
    async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                              user_data: User, query=None):
        """Show main menu"""
        text = Messages.MAIN_MENU.format(
            balance=Utils.format_number(user_data.balance),
            balance_usd=Utils.refi_to_usd(user_data.balance),
            referrals=user_data.referrals_count,
            total_earned=Utils.format_number(user_data.total_earned),
            total_earned_usd=Utils.refi_to_usd(user_data.total_earned)
        )
        
        if query:
            await query.edit_message_text(
                text,
                reply_markup=Keyboards.main(user_data),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=Keyboards.main(user_data),
                parse_mode=ParseMode.MARKDOWN
            )
    
    # ========== BALANCE ==========
    
    @staticmethod
    @log_errors
    async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show user balance"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        # Calculate referral earnings
        ref_earned = user_data.referrals_count * Config.REFERRAL_BONUS
        
        text = Messages.BALANCE.format(
            balance=Utils.format_number(user_data.balance),
            balance_usd=Utils.refi_to_usd(user_data.balance),
            referrals=user_data.referrals_count,
            total_earned=Utils.format_number(user_data.total_earned),
            total_earned_usd=Utils.refi_to_usd(user_data.total_earned),
            ref_earned=Utils.format_number(ref_earned),
            ref_earned_usd=Utils.refi_to_usd(ref_earned),
            join_date=Utils.get_date(user_data.joined_at)
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== REFERRAL ==========
    
    @staticmethod
    @log_errors
    async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show referral link and stats"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        bot_username = context.bot.username
        link = f"https://t.me/{bot_username}?start={user_data.referral_code}"
        
        earned_from_refs = user_data.referrals_count * Config.REFERRAL_BONUS
        
        text = Messages.REFERRAL.format(
            link=link,
            referral=Utils.format_number(Config.REFERRAL_BONUS),
            referral_usd=Utils.refi_to_usd(Config.REFERRAL_BONUS),
            welcome=Utils.format_number(Config.WELCOME_BONUS),
            welcome_usd=Utils.refi_to_usd(Config.WELCOME_BONUS),
            clicks=user_data.referral_clicks,
            successful=user_data.referrals_count,
            earned=Utils.format_number(earned_from_refs),
            earned_usd=Utils.refi_to_usd(earned_from_refs)
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== STATS ==========
    
    @staticmethod
    @log_errors
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed user statistics"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        # Calculate additional stats
        total_ref_earned = user_data.referrals_count * Config.REFERRAL_BONUS
        welcome_earned = Config.WELCOME_BONUS if user_data.verified_at else 0
        
        text = (
            f"📊 *Detailed Statistics*\n\n"
            f"👤 *User Info*\n"
            f"• ID: `{user_data.user_id}`\n"
            f"• Username: @{user_data.username}\n"
            f"• Joined: {Utils.get_date(user_data.joined_at)}\n\n"
            f"💰 *Financial*\n"
            f"• Balance: `{Utils.format_number(user_data.balance)}` REFi\n"
            f"• Total earned: `{Utils.format_number(user_data.total_earned)}` REFi\n"
            f"• Total withdrawn: `{Utils.format_number(user_data.total_withdrawn)}` REFi\n"
            f"• Welcome bonus: `{Utils.format_number(welcome_earned)}` REFi\n\n"
            f"👥 *Referrals*\n"
            f"• Total: {user_data.referrals_count}\n"
            f"• Earnings: `{Utils.format_number(total_ref_earned)}` REFi\n"
            f"• Link clicks: {user_data.referral_clicks}\n"
            f"• Conversion rate: {user_data.referral_clicks and (user_data.referrals_count / user_data.referral_clicks * 100):.1f}%\n\n"
            f"✅ *Status*\n"
            f"• Verified: {'✅' if user_data.verification_status == VerificationStatus.VERIFIED else '❌'}\n"
            f"• Wallet: {'✅ Set' if user_data.wallet_address else '❌ Not set'}\n"
            f"• Admin: {'✅' if user_data.is_admin else '❌'}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== WITHDRAWAL ==========
    
    @staticmethod
    @log_errors
    async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Start withdrawal process"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        # Check if verified
        if user_data.verification_status != VerificationStatus.VERIFIED:
            await query.edit_message_text(
                "❌ You need to verify your membership first!\n"
                "Send /start to begin verification."
            )
            return
        
        # Get pending withdrawals count
        pending = db.get_user_withdrawals(user_id, WithdrawalStatus.PENDING)
        
        # Check pending limit
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            await query.edit_message_text(
                Messages.WITHDRAW_PENDING_LIMIT.format(
                    count=len(pending),
                    max_count=Config.MAX_PENDING_WITHDRAWALS
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Check daily limit
        today = Utils.get_today()
        if user_data.last_withdrawal_date == today:
            if user_data.daily_withdrawals >= Config.DAILY_WITHDRAWAL_LIMIT:
                await query.edit_message_text(
                    Messages.WITHDRAW_DAILY_LIMIT.format(
                        limit=Utils.format_number(Config.DAILY_WITHDRAWAL_LIMIT)
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
                return
        
        text = Messages.WITHDRAW_MENU.format(
            balance=Utils.format_number(user_data.balance),
            balance_usd=Utils.refi_to_usd(user_data.balance),
            min_withdraw=Utils.format_number(Config.MIN_WITHDRAW),
            min_withdraw_usd=Utils.refi_to_usd(Config.MIN_WITHDRAW),
            pending=len(pending)
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Set state
        context.user_data['state'] = UserState.WAITING_WITHDRAW_AMOUNT
    
    @staticmethod
    @log_errors
    async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle withdrawal amount input"""
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await update.message.reply_text("❌ Please send /start first")
            return
        
        try:
            amount = int(update.message.text.replace(',', '').strip())
        except ValueError:
            await update.message.reply_text("❌ Please enter a valid number")
            return
        
        # Check minimum
        if amount < Config.MIN_WITHDRAW:
            needed = Config.MIN_WITHDRAW - amount
            await update.message.reply_text(
                Messages.WITHDRAW_BELOW_MIN.format(
                    min=Utils.format_number(Config.MIN_WITHDRAW),
                    min_usd=Utils.refi_to_usd(Config.MIN_WITHDRAW),
                    balance=Utils.format_number(user_data.balance),
                    balance_usd=Utils.refi_to_usd(user_data.balance),
                    needed=Utils.format_number(needed)
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('state', None)
            return
        
        # Check balance
        if amount > user_data.balance:
            await update.message.reply_text(
                Messages.WITHDRAW_INSUFFICIENT.format(
                    balance=Utils.format_number(user_data.balance),
                    balance_usd=Utils.refi_to_usd(user_data.balance),
                    amount=Utils.format_number(amount),
                    amount_usd=Utils.refi_to_usd(amount)
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('state', None)
            return
        
        # Check pending withdrawals limit
        pending = db.get_user_withdrawals(user_id, WithdrawalStatus.PENDING)
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            await update.message.reply_text(
                Messages.WITHDRAW_PENDING_LIMIT.format(
                    count=len(pending),
                    max_count=Config.MAX_PENDING_WITHDRAWALS
                ),
                parse_mode=ParseMode.MARKDOWN
            )
            context.user_data.pop('state', None)
            return
        
        # Store amount and ask for wallet
        context.user_data['withdraw_amount'] = amount
        context.user_data['state'] = UserState.WAITING_WALLET_ADDRESS
        
        await update.message.reply_text(
            "📮 *Enter your wallet address*\n\n"
            "Please enter your Ethereum wallet address (starts with 0x):\n"
            "Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle wallet address input"""
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        wallet = update.message.text.strip()
        
        if not user_data:
            await update.message.reply_text("❌ Please send /start first")
            return
        
        # Validate wallet
        if not Utils.is_valid_eth_wallet(wallet):
            await update.message.reply_text(
                "❌ *Invalid wallet address*\n\n"
                "Please enter a valid Ethereum wallet address starting with 0x\n"
                "Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`",
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        amount = context.user_data.get('withdraw_amount')
        if not amount:
            await update.message.reply_text("❌ Please start withdrawal again")
            context.user_data.pop('state', None)
            return
        
        # Deduct balance
        user_data.balance -= amount
        
        # Create withdrawal request
        withdrawal = db.create_withdrawal(user_id, amount, wallet)
        
        # Update user
        db.update_user(user_id, 
                      balance=user_data.balance,
                      wallet_address=wallet)
        
        # Clear state
        context.user_data.pop('state', None)
        context.user_data.pop('withdraw_amount', None)
        
        # Notify user
        await update.message.reply_text(
            Messages.WITHDRAW_SUCCESS.format(
                request_id=withdrawal.request_id,
                amount=Utils.format_number(amount),
                amount_usd=Utils.refi_to_usd(amount),
                wallet_short=Utils.short_wallet(wallet)
            ),
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.main(user_data)
        )
        
        # Notify admins
        for admin_id in Config.ADMIN_IDS:
            try:
                await context.bot.send_message(
                    chat_id=admin_id,
                    text=(
                        f"💰 *New Withdrawal Request*\n\n"
                        f"Request ID: `{withdrawal.request_id}`\n"
                        f"User: {user_data.first_name} (@{user_data.username})\n"
                        f"User ID: `{user_id}`\n"
                        f"Amount: {Utils.format_number(amount)} REFi\n"
                        f"USD: ${Utils.refi_to_usd(amount):.2f}\n"
                        f"Wallet: `{wallet}`\n\n"
                        f"Use /admin to review."
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify admin {admin_id}: {e}")
        
        logger.info(f"💰 Withdrawal created: {withdrawal.request_id} for {amount} REFi")
    
    # ========== ADMIN ==========
    
    @staticmethod
    @log_errors
    async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command"""
        user = update.effective_user
        
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text(Messages.UNAUTHORIZED)
            return ConversationHandler.END
        
        if db.is_admin_session_valid(user.id):
            await Handlers._show_admin_panel(update, context)
            return ConversationHandler.END
        
        await update.message.reply_text(
            "🔐 *Admin Login*\n\n"
            "Please enter the admin password:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return UserState.WAITING_ADMIN_PASS.value
    
    @staticmethod
    @log_errors
    async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle admin password input"""
        user = update.effective_user
        password = update.message.text
        
        if password == Config.ADMIN_PASSWORD:
            db.create_admin_session(user.id)
            
            # Set user as admin in database
            user_data = db.get_or_create_user(user.id)
            user_data.is_admin = True
            db.update_user(user.id, is_admin=True)
            
            await update.message.reply_text("✅ Login successful!")
            await Handlers._show_admin_panel(update, context)
        else:
            await update.message.reply_text("❌ Wrong password!")
        
        return ConversationHandler.END
    
    @staticmethod
    async def _show_admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel"""
        stats = db.get_stats()
        
        # Format uptime
        uptime_seconds = stats['uptime']
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        text = Messages.ADMIN_PANEL.format(
            total_users=stats['total_users'],
            verified=stats['users_verified'],
            banned=stats['users_banned'],
            total_balance=Utils.format_number(stats['total_balance']),
            total_withdrawals=stats['total_withdrawals'],
            total_withdrawn=Utils.format_number(stats['total_withdrawn_amount']),
            pending_withdrawals=stats['pending_withdrawals'],
            uptime=f"{hours}h {minutes}m"
        )
        
        if update.callback_query:
            await update.callback_query.edit_message_text(
                text,
                reply_markup=Keyboards.admin(),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await update.message.reply_text(
                text,
                reply_markup=Keyboards.admin(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show detailed admin statistics"""
        query = update.callback_query
        await query.answer()
        
        stats = db.get_stats()
        users = list(db.users.values())
        
        # Calculate activity stats
        now = time.time()
        active_today = [u for u in users if u.last_active > now - 86400]
        active_week = [u for u in users if u.last_active > now - 604800]
        
        # Calculate totals
        total_earned = sum(u.total_earned for u in users)
        avg_balance = stats['total_balance'] // max(1, stats['total_users'])
        
        # Find top referrer
        top_referrer = max(users, key=lambda u: u.referrals_count) if users else None
        top_referrer_text = f"{top_referrer.first_name} (@{top_referrer.username}): {top_referrer.referrals_count}" if top_referrer else "None"
        
        # Format uptime
        uptime_seconds = stats['uptime']
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        text = Messages.ADMIN_STATS.format(
            total_users=stats['total_users'],
            verified=stats['users_verified'],
            unverified=stats['total_users'] - stats['users_verified'],
            banned=stats['users_banned'],
            active_today=len(active_today),
            active_week=len(active_week),
            total_balance=Utils.format_number(stats['total_balance']),
            total_earned=Utils.format_number(total_earned),
            total_withdrawn=Utils.format_number(stats['total_withdrawn_amount']),
            avg_balance=Utils.format_number(avg_balance),
            total_referrals=stats['total_referrals'],
            avg_referrals=stats['total_referrals'] / max(1, stats['total_users']),
            top_referrer=top_referrer_text,
            commands=stats['commands_processed'],
            uptime=f"{hours}h {minutes}m",
            start_time=Utils.get_date(stats['bot_start_time'])
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.admin(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show pending withdrawals"""
        query = update.callback_query
        await query.answer()
        
        pending = db.get_pending_withdrawals()
        
        if not pending:
            await query.edit_message_text(
                "✅ No pending withdrawals.",
                reply_markup=Keyboards.admin(),
                parse_mode=ParseMode.MARKDOWN
            )
            return
        
        # Show first 5 withdrawals
        text = "💰 *Pending Withdrawals*\n\n"
        keyboard = []
        
        for w in pending[:5]:
            user = db.get_user(w.user_id)
            user_name = user.first_name if user else "Unknown"
            user_username = f"@{user.username}" if user and user.username else "No username"
            
            text += (
                f"🆔 `{w.request_id}`\n"
                f"👤 {user_name} ({user_username})\n"
                f"💰 {Utils.format_number(w.amount)} REFi (${Utils.refi_to_usd(w.amount):.2f})\n"
                f"📮 {Utils.short_wallet(w.wallet_address)}\n"
                f"📅 {Utils.get_date(w.created_at)}\n\n"
            )
            
            # Add button for this withdrawal
            keyboard.append([InlineKeyboardButton(
                f"Process {w.request_id[:8]}", 
                callback_data=f"withdrawal_{w.request_id}"
            )])
        
        if len(pending) > 5:
            text += f"*... and {len(pending) - 5} more*\n\n"
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_withdrawal_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show withdrawal details"""
        query = update.callback_query
        data = query.data
        
        request_id = data.replace('withdrawal_', '')
        withdrawal = db.get_withdrawal(request_id)
        
        if not withdrawal:
            await query.answer("❌ Withdrawal not found")
            return
        
        user = db.get_user(withdrawal.user_id)
        
        text = (
            f"💰 *Withdrawal Details*\n\n"
            f"🆔 Request ID: `{withdrawal.request_id}`\n"
            f"👤 User: {user.first_name} (@{user.username})\n"
            f"👤 User ID: `{user.user_id}`\n"
            f"💰 Amount: {Utils.format_number(withdrawal.amount)} REFi\n"
            f"💵 USD: ${Utils.refi_to_usd(withdrawal.amount):.2f}\n"
            f"📮 Wallet: `{withdrawal.wallet_address}`\n"
            f"📅 Created: {Utils.get_date(withdrawal.created_at)}\n"
            f"📊 Status: {withdrawal.status.value}\n"
        )
        
        if withdrawal.processed_at:
            text += f"⏱️ Processed: {Utils.get_date(withdrawal.processed_at)}\n"
        if withdrawal.tx_hash:
            text += f"🔗 TX: `{withdrawal.tx_hash}`\n"
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.withdrawal_actions(request_id),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    @admin_required
    async def handle_withdrawal_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle approve/reject withdrawal"""
        query = update.callback_query
        data = query.data
        
        # Parse action and request_id
        if data.startswith('approve_'):
            action = 'approve'
            request_id = data[8:]
        elif data.startswith('reject_'):
            action = 'reject'
            request_id = data[7:]
        else:
            return
        
        withdrawal = db.get_withdrawal(request_id)
        if not withdrawal:
            await query.answer("❌ Withdrawal not found")
            return
        
        user = db.get_user(withdrawal.user_id)
        
        if action == 'approve':
            # Process approval
            db.process_withdrawal(request_id, update.effective_user.id, 
                                 WithdrawalStatus.APPROVED)
            
            await query.edit_message_text(
                f"✅ *Withdrawal Approved*\n\n"
                f"Request: `{request_id}`\n"
                f"User: {user.first_name} (@{user.username})\n"
                f"Amount: {Utils.format_number(withdrawal.amount)} REFi\n"
                f"Wallet: {withdrawal.wallet_address}\n\n"
                f"The user has been notified.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.admin()
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=withdrawal.user_id,
                    text=Messages.WITHDRAW_APPROVED_USER.format(
                        request_id=request_id,
                        amount=Utils.format_number(withdrawal.amount),
                        amount_usd=Utils.refi_to_usd(withdrawal.amount),
                        wallet=withdrawal.wallet_address
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify user {withdrawal.user_id}: {e}")
            
            logger.info(f"✅ Withdrawal approved: {request_id}")
        
        else:  # reject
            # Return funds to user
            if user:
                user.balance += withdrawal.amount
                db.update_user(user.user_id, balance=user.balance)
            
            db.process_withdrawal(request_id, update.effective_user.id,
                                 WithdrawalStatus.REJECTED)
            
            await query.edit_message_text(
                f"❌ *Withdrawal Rejected*\n\n"
                f"Request: `{request_id}`\n"
                f"User: {user.first_name} (@{user.username})\n"
                f"Amount: {Utils.format_number(withdrawal.amount)} REFi\n\n"
                f"Funds have been returned to user.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=Keyboards.admin()
            )
            
            # Notify user
            try:
                await context.bot.send_message(
                    chat_id=withdrawal.user_id,
                    text=Messages.WITHDRAW_REJECTED_USER.format(
                        request_id=request_id,
                        amount=Utils.format_number(withdrawal.amount),
                        amount_usd=Utils.refi_to_usd(withdrawal.amount),
                        reason="Rejected by admin"
                    ),
                    parse_mode=ParseMode.MARKDOWN
                )
            except Exception as e:
                logger.error(f"Failed to notify user {withdrawal.user_id}: {e}")
            
            logger.info(f"❌ Withdrawal rejected: {request_id}")
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate user search"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔍 *Search User*\n\n"
            "Send me the User ID or username to search for.\n\n"
            "Examples:\n"
            "• `1653918641` (User ID)\n"
            "• `@username` (Username)\n"
            "• `username` (Username without @)",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['admin_state'] = 'searching'
    
    @staticmethod
    @log_errors
    @admin_required
    async def handle_admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle search input"""
        query_text = update.message.text.strip()
        user = None
        
        # Search by user ID
        if query_text.isdigit():
            user_id = int(query_text)
            user = db.get_user(user_id)
        else:
            # Search by username
            username = query_text.lstrip('@').lower()
            user = db.get_user_by_username(username)
        
        if not user:
            await update.message.reply_text(
                f"❌ User not found: {query_text}",
                reply_markup=Keyboards.admin()
            )
            context.user_data.pop('admin_state', None)
            return
        
        # Get user withdrawals
        withdrawals = db.get_user_withdrawals(user.user_id)
        pending_w = [w for w in withdrawals if w.status == WithdrawalStatus.PENDING]
        
        # Format user info
        text = Messages.ADMIN_USER_INFO.format(
            user_id=user.user_id,
            username=user.username or "None",
            first_name=user.first_name or "None",
            last_name=user.last_name or "",
            language=user.language,
            joined_at=Utils.get_date(user.joined_at),
            last_active=Utils.get_date(user.last_active),
            balance=Utils.format_number(user.balance),
            balance_usd=Utils.refi_to_usd(user.balance),
            total_earned=Utils.format_number(user.total_earned),
            total_earned_usd=Utils.refi_to_usd(user.total_earned),
            total_withdrawn=Utils.format_number(user.total_withdrawn),
            total_withdrawn_usd=Utils.refi_to_usd(user.total_withdrawn),
            pending_withdrawals=len(pending_w),
            referrals_count=user.referrals_count,
            referral_code=user.referral_code,
            referred_by=user.referred_by or "Direct",
            referral_clicks=user.referral_clicks,
            verified='✅' if user.verification_status == VerificationStatus.VERIFIED else '❌',
            wallet=user.wallet_address or "Not set",
            admin='✅' if user.is_admin else '❌',
            banned='✅' if user.is_banned else '❌'
        )
        
        await update.message.reply_text(
            text,
            reply_markup=Keyboards.user_actions(user.user_id, user.is_banned, user.is_admin),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data.pop('admin_state', None)
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_user_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user management actions (ban/unban/make admin)"""
        query = update.callback_query
        await query.answer()
        
        data = query.data
        parts = data.split('_')
        action = parts[0]
        user_id = int(parts[-1])
        
        target_user = db.get_user(user_id)
        if not target_user:
            await query.edit_message_text("❌ User not found")
            return
        
        admin_id = update.effective_user.id
        
        if action == 'ban':
            target_user.is_banned = True
            db.update_user(user_id, is_banned=True)
            message = f"✅ User {user_id} has been banned."
            logger.info(f"🔨 User {user_id} banned by {admin_id}")
        
        elif action == 'unban':
            target_user.is_banned = False
            db.update_user(user_id, is_banned=False)
            message = f"✅ User {user_id} has been unbanned."
            logger.info(f"✅ User {user_id} unbanned by {admin_id}")
        
        elif action == 'make':
            target_user.is_admin = True
            db.update_user(user_id, is_admin=True)
            message = f"✅ User {user_id} is now an admin."
            logger.info(f"👑 User {user_id} made admin by {admin_id}")
        
        elif action == 'remove':
            target_user.is_admin = False
            db.update_user(user_id, is_admin=False)
            message = f"✅ User {user_id} is no longer an admin."
            logger.info(f"👤 User {user_id} removed from admin by {admin_id}")
        
        else:
            return
        
        await query.edit_message_text(
            message,
            reply_markup=Keyboards.admin()
        )
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Initiate broadcast"""
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\n"
            "Send me the message you want to broadcast to all users.\n\n"
            "You can use Markdown formatting for rich text.\n"
            "Type /cancel to cancel.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['admin_state'] = 'broadcast'
    
    @staticmethod
    @log_errors
    @admin_required
    async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle broadcast message"""
        if update.message.text == '/cancel':
            await update.message.reply_text("❌ Broadcast cancelled.")
            context.user_data.pop('admin_state', None)
            return
        
        message_text = update.message.text
        total_users = len(db.users)
        
        status_msg = await update.message.reply_text(
            f"📢 Preparing to broadcast to {total_users} users..."
        )
        
        sent = 0
        failed = 0
        start_time = time.time()
        
        for user_id in db.users.keys():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                
                # Update status every 10 messages
                if sent % 10 == 0:
                    await status_msg.edit_text(
                        f"📢 Broadcasting...\n"
                        f"✅ Sent: {sent}\n"
                        f"❌ Failed: {failed}\n"
                        f"⏱️ Elapsed: {int(time.time() - start_time)}s"
                    )
                    await asyncio.sleep(0.5)  # Avoid flood limits
                    
            except Exception as e:
                failed += 1
                logger.error(f"Broadcast failed to {user_id}: {e}")
        
        elapsed = int(time.time() - start_time)
        await status_msg.edit_text(
            f"✅ *Broadcast Complete*\n\n"
            f"• Sent: {sent}\n"
            f"• Failed: {failed}\n"
            f"• Total users: {total_users}\n"
            f"• Time: {elapsed}s",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.admin()
        )
        
        logger.info(f"📢 Broadcast completed: {sent} sent, {failed} failed in {elapsed}s")
        context.user_data.pop('admin_state', None)
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show users list"""
        query = update.callback_query
        await query.answer()
        
        users = list(db.users.values())
        users.sort(key=lambda u: u.joined_at, reverse=True)
        
        text = "👥 *Recent Users*\n\n"
        
        for user in users[:10]:
            verified = '✅' if user.verification_status == VerificationStatus.VERIFIED else '❌'
            text += f"{verified} {user.first_name} (@{user.username}) - {Utils.get_date(user.joined_at)}\n"
        
        text += f"\n*Total: {len(users)} users*"
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.admin(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    @log_errors
    @admin_required
    async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Logout from admin panel"""
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        db.end_admin_session(user_id)
        
        await query.edit_message_text(
            "🔒 You have been logged out from admin panel.",
            reply_markup=Keyboards.main()
        )
        
        logger.info(f"🔒 Admin logged out: {user_id}")
    
    @staticmethod
    @log_errors
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Show admin panel (from callback)"""
        await Handlers._show_admin_panel(update, context)
    
    # ========== ERROR HANDLER ==========
    
    @staticmethod
    @log_errors
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Update {update} caused error {context.error}")
        
        try:
            if update and update.effective_message:
                await update.effective_message.reply_text(
                    Messages.ERROR.format(error="An internal error occurred. Please try again later."),
                    parse_mode=ParseMode.MARKDOWN
                )
        except Exception as e:
            logger.error(f"Error in error handler: {e}")
    
    # ========== UNKNOWN COMMAND ==========
    
    @staticmethod
    @log_errors
    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle unknown commands"""
        await update.message.reply_text(
            "❌ Unknown command. Use /start to begin.",
            parse_mode=ParseMode.MARKDOWN
        )

# ==================== MAIN FUNCTION ====================

def main():
    """Main function to run the bot"""
    
    # Validate configuration
    try:
        Config.validate()
    except ValueError as e:
        logger.error(e)
        sys.exit(1)
    
    # Print banner
    print("\n" + "="*60)
    print("🤖 REFi REFERRAL BOT - PROFESSIONAL EDITION")
    print("="*60)
    print(f"📱 Bot Token: {Config.BOT_TOKEN[:15]}...")
    print(f"👤 Admin IDs: {Config.ADMIN_IDS}")
    print(f"💰 Welcome Bonus: {Utils.format_number(Config.WELCOME_BONUS)} REFi")
    print(f"👥 Referral Bonus: {Utils.format_number(Config.REFERRAL_BONUS)} REFi")
    print(f"💸 Min Withdraw: {Utils.format_number(Config.MIN_WITHDRAW)} REFi")
    print(f"👥 Total Users: {len(db.users)}")
    print("="*60 + "\n")
    
    # Create application with defaults
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN)
    application = Application.builder().token(Config.BOT_TOKEN).defaults(defaults).build()
    
    # ========== CONVERSATION HANDLERS ==========
    
    # Admin login conversation
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", Handlers.admin_login)],
        states={
            UserState.WAITING_ADMIN_PASS.value: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.handle_admin_password)
            ]
        },
        fallbacks=[CommandHandler("cancel", Handlers.unknown_command)]
    )
    
    # ========== COMMAND HANDLERS ==========
    application.add_handler(CommandHandler("start", Handlers.start))
    application.add_handler(admin_conv)
    application.add_handler(MessageHandler(filters.COMMAND, Handlers.unknown_command))
    
    # ========== CALLBACK QUERY HANDLERS ==========
    application.add_handler(CallbackQueryHandler(Handlers.verify_callback, pattern="^verify$"))
    application.add_handler(CallbackQueryHandler(Handlers.main_menu, pattern="^main_menu$"))
    application.add_handler(CallbackQueryHandler(Handlers.balance, pattern="^balance$"))
    application.add_handler(CallbackQueryHandler(Handlers.referral, pattern="^referral$"))
    application.add_handler(CallbackQueryHandler(Handlers.stats, pattern="^stats$"))
    application.add_handler(CallbackQueryHandler(Handlers.withdraw, pattern="^withdraw$"))
    
    # Admin callbacks
    application.add_handler(CallbackQueryHandler(Handlers.admin_panel, pattern="^admin_panel$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_stats, pattern="^admin_stats$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_withdrawals, pattern="^admin_withdrawals$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_search, pattern="^admin_search$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_broadcast, pattern="^admin_broadcast$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_users, pattern="^admin_users$"))
    application.add_handler(CallbackQueryHandler(Handlers.admin_logout, pattern="^admin_logout$"))
    
    # Withdrawal action callbacks
    application.add_handler(CallbackQueryHandler(Handlers.admin_withdrawal_detail, pattern="^withdrawal_"))
    application.add_handler(CallbackQueryHandler(Handlers.handle_withdrawal_action, pattern="^(approve|reject)_"))
    
    # User management callbacks
    application.add_handler(CallbackQueryHandler(Handlers.admin_user_action, pattern="^(ban|unban|make|remove)_"))
    
    # ========== MESSAGE HANDLERS ==========
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_withdraw_amount
    ))
    
    # Admin message handlers
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_admin_search,
        lambda ctx: ctx.user_data.get('admin_state') == 'searching'
    ))
    
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_admin_broadcast,
        lambda ctx: ctx.user_data.get('admin_state') == 'broadcast'
    ))
    
    # Wallet address handler
    application.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_wallet_address,
        lambda ctx: ctx.user_data.get('state') == UserState.WAITING_WALLET_ADDRESS
    ))
    
    # ========== ERROR HANDLER ==========
    application.add_error_handler(Handlers.error_handler)
    
    # ========== START BOT ==========
    logger.info("🚀 Starting bot...")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*60)
    
    # Start polling with configured timeouts
    application.run_polling(
        timeout=Config.POLLING_TIMEOUT,
        read_timeout=Config.POLLING_READ_TIMEOUT,
        connect_timeout=Config.POLLING_CONNECT_TIMEOUT,
        pool_timeout=Config.POLLING_POOL_TIMEOUT
    )

# ==================== ENTRY POINT ====================

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
        logger.info("Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal error")
        sys.exit(1)

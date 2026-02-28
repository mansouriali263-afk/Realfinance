#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
=========================================================
🤖 REFi REFERRAL BOT - COMPLETE EDITION
=========================================================
A complete Telegram referral & earn bot with admin panel,
channel verification, and withdrawal system.

Author: Professional Development
Version: 4.0.0 (Production Ready)
Last Updated: 2026-02-28
=========================================================
"""

# ==================== IMPORTS ====================
import os
import sys
import logging
import time
import json
import random
import string
import hashlib
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, List, Any, Union
from functools import wraps
from enum import Enum
from dataclasses import dataclass, field

# Try to import telegram, with helpful error message
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
except ImportError as e:
    print(f"\n❌ Missing required library: {e}")
    print("📦 Please install: pip install python-telegram-bot==20.7")
    print("💡 If you're on Render, add 'python-telegram-bot==20.7' to requirements.txt\n")
    sys.exit(1)

# ==================== CONFIGURATION ====================

class Config:
    """Centralized configuration"""
    
    # Bot Token -直接从代码读取 (not from env for simplicity)
    BOT_TOKEN = "8720874613:AAF_Qz2ZmwL8M2kk76FpFpdhbTlP0acnbSs"
    BOT_USERNAME = "Realfinancepaybot"
    
    # Admin settings
    ADMIN_IDS = [1653918641]  # List of admin user IDs
    ADMIN_PASSWORD = "Ali97$"  # Admin password
    
    # Tokenomics
    COIN_NAME = "REFi"
    WELCOME_BONUS = 1_000_000  # 1,000,000 REFi
    REFERRAL_BONUS = 1_000_000  # 1,000,000 REFi per referral
    MIN_WITHDRAW = 5_000_000  # Minimum 5,000,000 REFi to withdraw
    
    # Channel requirements
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
    
    # Logging
    LOG_LEVEL = logging.INFO

# ==================== LOGGING ====================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=Config.LOG_LEVEL
)
logger = logging.getLogger(__name__)

# ==================== ENUMS ====================

class UserState(Enum):
    """User conversation states"""
    IDLE = 0
    WAITING_ADMIN_PASS = 1
    WAITING_WITHDRAW_AMOUNT = 2
    WAITING_WALLET_ADDRESS = 3

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

# ==================== DATA MODELS ====================

@dataclass
class User:
    """User data model"""
    user_id: int
    username: str = ""
    first_name: str = ""
    last_name: str = ""
    
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
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'user_id': self.user_id,
            'username': self.username,
            'first_name': self.first_name,
            'last_name': self.last_name,
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
            'is_banned': self.is_banned
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create from dictionary"""
        user = cls(user_id=data['user_id'])
        user.username = data.get('username', '')
        user.first_name = data.get('first_name', '')
        user.last_name = data.get('last_name', '')
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
        return user

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
    
    def to_dict(self) -> dict:
        """Convert to dictionary"""
        return {
            'request_id': self.request_id,
            'user_id': self.user_id,
            'amount': self.amount,
            'wallet_address': self.wallet_address,
            'status': self.status.value,
            'created_at': self.created_at,
            'processed_at': self.processed_at
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Withdrawal':
        """Create from dictionary"""
        return cls(
            request_id=data['request_id'],
            user_id=data['user_id'],
            amount=data['amount'],
            wallet_address=data['wallet_address'],
            status=WithdrawalStatus(data['status']),
            created_at=data['created_at'],
            processed_at=data.get('processed_at')
        )

# ==================== DATABASE ====================

class Database:
    """Simple in-memory database"""
    
    def __init__(self):
        self.users: Dict[int, User] = {}
        self.withdrawals: Dict[str, Withdrawal] = {}
        self.admin_sessions: Dict[int, float] = {}
        self.stats = {
            'total_users': 0,
            'total_verified': 0,
            'total_withdrawals': 0,
            'total_withdrawn_amount': 0,
            'total_referrals': 0,
            'bot_start_time': time.time()
        }
        
        # Load data from file if exists
        self._load()
        logger.info(f"✅ Database initialized with {len(self.users)} users")
    
    def _save(self):
        """Save data to file"""
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
        """Load data from file"""
        try:
            if os.path.exists('bot_data.json'):
                with open('bot_data.json', 'r') as f:
                    data = json.load(f)
                
                for uid_str, u_data in data.get('users', {}).items():
                    self.users[int(uid_str)] = User.from_dict(u_data)
                
                for wid, w_data in data.get('withdrawals', {}).items():
                    self.withdrawals[wid] = Withdrawal.from_dict(w_data)
                
                self.stats.update(data.get('stats', {}))
        except Exception as e:
            logger.error(f"Failed to load data: {e}")
    
    # User methods
    def get_user(self, user_id: int) -> Optional[User]:
        return self.users.get(user_id)
    
    def create_user(self, user_id: int, **kwargs) -> User:
        user = User(user_id=user_id, **kwargs)
        user.referral_code = self._generate_referral_code(user_id)
        self.users[user_id] = user
        self.stats['total_users'] += 1
        self._save()
        logger.info(f"👤 New user: {user_id}")
        return user
    
    def update_user(self, user_id: int, **kwargs) -> Optional[User]:
        user = self.get_user(user_id)
        if user:
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
            user.last_active = time.time()
            self._save()
        return user
    
    def get_or_create_user(self, user_id: int, **kwargs) -> User:
        user = self.get_user(user_id)
        if not user:
            user = self.create_user(user_id, **kwargs)
        return user
    
    def get_user_by_referral_code(self, code: str) -> Optional[User]:
        for user in self.users.values():
            if user.referral_code == code:
                return user
        return None
    
    # Referral methods
    def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        referrer = self.get_user(referrer_id)
        referred = self.get_user(referred_id)
        
        if not referrer or not referred:
            return False
        
        if str(referred_id) in referrer.referrals:
            return False
        
        referrer.referrals[str(referred_id)] = time.time()
        referrer.referrals_count += 1
        referrer.balance += Config.REFERRAL_BONUS
        referrer.total_earned += Config.REFERRAL_BONUS
        
        self.stats['total_referrals'] += 1
        self._save()
        return True
    
    # Withdrawal methods
    def create_withdrawal(self, user_id: int, amount: int, wallet: str) -> Withdrawal:
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
        return withdrawal
    
    def get_withdrawal(self, request_id: str) -> Optional[Withdrawal]:
        return self.withdrawals.get(request_id)
    
    def get_user_withdrawals(self, user_id: int) -> List[Withdrawal]:
        return [w for w in self.withdrawals.values() if w.user_id == user_id]
    
    def get_pending_withdrawals(self) -> List[Withdrawal]:
        return [w for w in self.withdrawals.values() 
                if w.status == WithdrawalStatus.PENDING]
    
    def process_withdrawal(self, request_id: str, admin_id: int, 
                          status: WithdrawalStatus) -> bool:
        withdrawal = self.get_withdrawal(request_id)
        if not withdrawal or withdrawal.status != WithdrawalStatus.PENDING:
            return False
        
        withdrawal.status = status
        withdrawal.processed_at = time.time()
        
        if status == WithdrawalStatus.APPROVED:
            self.stats['total_withdrawals'] += 1
            self.stats['total_withdrawn_amount'] += withdrawal.amount
            
            user = self.get_user(withdrawal.user_id)
            if user:
                user.total_withdrawn += withdrawal.amount
        elif status == WithdrawalStatus.REJECTED:
            # Return funds to user
            user = self.get_user(withdrawal.user_id)
            if user:
                user.balance += withdrawal.amount
        
        self._save()
        return True
    
    # Admin session methods
    def create_admin_session(self, user_id: int):
        self.admin_sessions[user_id] = time.time() + Config.SESSION_TIMEOUT
    
    def is_admin_session_valid(self, user_id: int) -> bool:
        if user_id not in self.admin_sessions:
            return False
        if self.admin_sessions[user_id] < time.time():
            del self.admin_sessions[user_id]
            return False
        return True
    
    def end_admin_session(self, user_id: int):
        self.admin_sessions.pop(user_id, None)
    
    # Stats methods
    def get_stats(self) -> dict:
        stats = self.stats.copy()
        stats['users_verified'] = sum(1 for u in self.users.values() 
                                      if u.verification_status == VerificationStatus.VERIFIED)
        stats['total_balance'] = sum(u.balance for u in self.users.values())
        stats['pending_withdrawals'] = len(self.get_pending_withdrawals())
        stats['uptime'] = int(time.time() - stats['bot_start_time'])
        return stats
    
    # Helper methods
    def _generate_referral_code(self, user_id: int) -> str:
        chars = string.ascii_uppercase + string.digits
        return ''.join(random.choices(chars, k=8))
    
    def _generate_request_id(self, user_id: int) -> str:
        timestamp = int(time.time())
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        return f"W{timestamp}{user_id}{random_part}"

# Initialize database
db = Database()

# ==================== UTILITIES ====================

class Utils:
    @staticmethod
    def format_number(num: int) -> str:
        return f"{num:,}"
    
    @staticmethod
    def refi_to_usd(refi: int) -> float:
        return (refi / 1_000_000) * 2.0
    
    @staticmethod
    def short_wallet(wallet: str, chars: int = 6) -> str:
        if not wallet or len(wallet) <= 16:
            return wallet or "Not set"
        return f"{wallet[:chars]}...{wallet[-chars:]}"
    
    @staticmethod
    def is_valid_eth_wallet(wallet: str) -> bool:
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
        dt = datetime.fromtimestamp(timestamp) if timestamp else datetime.now()
        return dt.strftime('%Y-%m-%d %H:%M')

# ==================== KEYBOARDS ====================

class Keyboards:
    @staticmethod
    def channels():
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
    def main(user=None):
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
        if user and user.is_admin:
            keyboard.append([InlineKeyboardButton("👑 Admin Panel", callback_data="admin_panel")])
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def back():
        return InlineKeyboardMarkup([[
            InlineKeyboardButton("🔙 Back", callback_data="main_menu")
        ]])
    
    @staticmethod
    def admin():
        keyboard = [
            [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
            [InlineKeyboardButton("💰 Pending Withdrawals", callback_data="admin_withdrawals")],
            [InlineKeyboardButton("🔍 Search User", callback_data="admin_search")],
            [InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast")],
            [InlineKeyboardButton("🔒 Logout", callback_data="admin_logout")]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    @staticmethod
    def withdrawal_actions(request_id: str):
        keyboard = [
            [
                InlineKeyboardButton("✅ Approve", callback_data=f"approve_{request_id}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"reject_{request_id}")
            ],
            [InlineKeyboardButton("🔙 Back", callback_data="admin_withdrawals")]
        ]
        return InlineKeyboardMarkup(keyboard)

# ==================== HANDLERS ====================

class Handlers:
    
    # ========== START ==========
    @staticmethod
    async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        args = context.args
        logger.info(f"Start command from user {user.id}")
        
        # Get or create user
        user_data = db.get_or_create_user(
            user_id=user.id,
            username=user.username or "",
            first_name=user.first_name or ""
        )
        
        # Check for referral
        if args and args[0] and not user_data.referred_by:
            referrer = db.get_user_by_referral_code(args[0])
            if referrer and referrer.user_id != user.id:
                user_data.referred_by = referrer.user_id
                referrer.referral_clicks += 1
                db.update_user(referrer.user_id, referral_clicks=referrer.referral_clicks)
                db.update_user(user.id, referred_by=referrer.user_id)
                logger.info(f"Referral click: {referrer.user_id} -> {user.id}")
        
        # If already verified, show main menu
        if user_data.verification_status == VerificationStatus.VERIFIED:
            await Handlers._show_main_menu(update, context, user_data)
            return
        
        # Show verification channels
        channels_text = "\n".join([f"• {ch['name']}: {ch['link']}" 
                                   for ch in Config.REQUIRED_CHANNELS])
        
        welcome_bonus_usd = Utils.refi_to_usd(Config.WELCOME_BONUS)
        referral_bonus_usd = Utils.refi_to_usd(Config.REFERRAL_BONUS)
        
        await update.message.reply_text(
            f"🎉 *Welcome to REFi Earn Bot!*\n\n"
            f"💰 *Welcome Bonus:* {Utils.format_number(Config.WELCOME_BONUS)} REFi (${welcome_bonus_usd:.2f})\n"
            f"👥 *Referral Bonus:* {Utils.format_number(Config.REFERRAL_BONUS)} REFi (${referral_bonus_usd:.2f}) per friend\n\n"
            f"📢 *To start, you must join these channels:*\n{channels_text}\n\n"
            f"👇 Click 'Verify' after joining",
            reply_markup=Keyboards.channels(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== VERIFY ==========
    @staticmethod
    async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            if user_data.verification_status == VerificationStatus.VERIFIED:
                await Handlers._show_main_menu(update, context, user_data, query)
                return
            
            # Verify user
            user_data.verification_status = VerificationStatus.VERIFIED
            user_data.verified_at = time.time()
            user_data.balance += Config.WELCOME_BONUS
            user_data.total_earned += Config.WELCOME_BONUS
            
            # Process referral
            if user_data.referred_by:
                referrer = db.get_user(user_data.referred_by)
                if referrer:
                    db.add_referral(referrer.user_id, user_id)
                    try:
                        await context.bot.send_message(
                            chat_id=referrer.user_id,
                            text=(
                                f"🎉 *Congratulations!*\n\n"
                                f"Your friend {user_data.first_name} joined using your link!\n"
                                f"✨ You earned {Utils.format_number(Config.REFERRAL_BONUS)} REFi"
                            ),
                            parse_mode=ParseMode.MARKDOWN
                        )
                    except:
                        pass
            
            db.update_user(user_id,
                          verification_status=user_data.verification_status,
                          verified_at=user_data.verified_at,
                          balance=user_data.balance,
                          total_earned=user_data.total_earned)
            
            welcome_bonus_usd = Utils.refi_to_usd(Config.WELCOME_BONUS)
            balance_usd = Utils.refi_to_usd(user_data.balance)
            
            await query.edit_message_text(
                f"✅ *Verification Successful!*\n\n"
                f"✨ Added {Utils.format_number(Config.WELCOME_BONUS)} REFi (${welcome_bonus_usd:.2f}) to your balance\n"
                f"💰 Current balance: {Utils.format_number(user_data.balance)} REFi (${balance_usd:.2f})\n\n"
                f"👥 Share your referral link and earn {Utils.format_number(Config.REFERRAL_BONUS)} REFi per friend!",
                reply_markup=Keyboards.main(user_data),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            not_joined_text = "\n".join([f"• {ch}" for ch in not_joined])
            await query.edit_message_text(
                f"❌ *Verification Failed*\n\n"
                f"You haven't joined these channels yet:\n{not_joined_text}\n\n"
                f"Please join them and try again.",
                reply_markup=Keyboards.channels(),
                parse_mode=ParseMode.MARKDOWN
            )
    
    @staticmethod
    async def _check_channels(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> Tuple[bool, List[str]]:
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
                logger.error(f"Channel check failed: {e}")
                not_joined.append(channel['name'])
        return len(not_joined) == 0, not_joined
    
    # ========== MAIN MENU ==========
    @staticmethod
    async def main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        balance_usd = Utils.refi_to_usd(user_data.balance)
        total_earned_usd = Utils.refi_to_usd(user_data.total_earned)
        
        text = (
            f"🎯 *Main Menu*\n\n"
            f"💰 Balance: {Utils.format_number(user_data.balance)} REFi (${balance_usd:.2f})\n"
            f"👥 Referrals: {user_data.referrals_count}\n"
            f"📊 Total earned: {Utils.format_number(user_data.total_earned)} REFi (${total_earned_usd:.2f})\n\n"
            f"Choose an option below:"
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
    async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        ref_earned = user_data.referrals_count * Config.REFERRAL_BONUS
        balance_usd = Utils.refi_to_usd(user_data.balance)
        total_earned_usd = Utils.refi_to_usd(user_data.total_earned)
        ref_earned_usd = Utils.refi_to_usd(ref_earned)
        
        text = (
            f"💰 *Your Balance*\n\n"
            f"• REFi: `{Utils.format_number(user_data.balance)}`\n"
            f"• USD: `${balance_usd:.2f}`\n\n"
            f"📊 *Statistics*\n"
            f"• Total referrals: {user_data.referrals_count}\n"
            f"• Total earned: `{Utils.format_number(user_data.total_earned)}` REFi (${total_earned_usd:.2f})\n"
            f"• Referral earnings: `{Utils.format_number(ref_earned)}` REFi (${ref_earned_usd:.2f})\n"
            f"• Join date: {Utils.get_date(user_data.joined_at)}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== REFERRAL ==========
    @staticmethod
    async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        referral_bonus_usd = Utils.refi_to_usd(Config.REFERRAL_BONUS)
        welcome_bonus_usd = Utils.refi_to_usd(Config.WELCOME_BONUS)
        earned_usd = Utils.refi_to_usd(earned_from_refs)
        
        text = (
            f"🔗 *Your Referral Link*\n\n"
            f"`{link}`\n\n"
            f"🎁 *Rewards*\n"
            f"• You get: {Utils.format_number(Config.REFERRAL_BONUS)} REFi (${referral_bonus_usd:.2f}) per referral\n"
            f"• Friend gets: {Utils.format_number(Config.WELCOME_BONUS)} REFi (${welcome_bonus_usd:.2f})\n\n"
            f"📊 *Stats*\n"
            f"• Total clicks: {user_data.referral_clicks}\n"
            f"• Successful referrals: {user_data.referrals_count}\n"
            f"• Earnings from referrals: {Utils.format_number(earned_from_refs)} REFi (${earned_usd:.2f})\n\n"
            f"Share this link with your friends!"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== STATS ==========
    @staticmethod
    async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
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
            f"• Link clicks: {user_data.referral_clicks}\n\n"
            f"✅ *Status*\n"
            f"• Verified: {'✅' if user_data.verification_status == VerificationStatus.VERIFIED else '❌'}\n"
            f"• Wallet: {'✅ Set' if user_data.wallet_address else '❌ Not set'}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    # ========== WITHDRAW ==========
    @staticmethod
    async def withdraw(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        
        if not user_data:
            await query.edit_message_text("❌ Please send /start first")
            return
        
        if user_data.verification_status != VerificationStatus.VERIFIED:
            await query.edit_message_text(
                "❌ You need to verify your membership first!\n"
                "Send /start to begin verification."
            )
            return
        
        pending = [w for w in db.get_user_withdrawals(user_id) 
                  if w.status == WithdrawalStatus.PENDING]
        
        if len(pending) >= Config.MAX_PENDING_WITHDRAWALS:
            await query.edit_message_text(
                f"⚠️ *Pending Withdrawals Limit*\n\n"
                f"You already have {len(pending)} pending withdrawals.\n"
                f"Maximum allowed is {Config.MAX_PENDING_WITHDRAWALS}."
            )
            return
        
        balance_usd = Utils.refi_to_usd(user_data.balance)
        min_withdraw_usd = Utils.refi_to_usd(Config.MIN_WITHDRAW)
        
        await query.edit_message_text(
            f"💸 *Withdrawal*\n\n"
            f"💰 Your balance: {Utils.format_number(user_data.balance)} REFi (${balance_usd:.2f})\n"
            f"📉 Minimum: {Utils.format_number(Config.MIN_WITHDRAW)} REFi (${min_withdraw_usd:.2f})\n"
            f"⏳ Pending requests: {len(pending)}\n\n"
            f"Enter the amount you want to withdraw:",
            reply_markup=Keyboards.back(),
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['state'] = UserState.WAITING_WITHDRAW_AMOUNT
    
    @staticmethod
    async def handle_withdraw_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
        
        if amount < Config.MIN_WITHDRAW:
            needed = Config.MIN_WITHDRAW - amount
            await update.message.reply_text(
                f"⚠️ *Below Minimum Withdrawal*\n\n"
                f"Minimum: {Utils.format_number(Config.MIN_WITHDRAW)} REFi\n"
                f"Your balance: {Utils.format_number(user_data.balance)} REFi\n\n"
                f"You need {Utils.format_number(needed)} more REFi to withdraw."
            )
            context.user_data.pop('state', None)
            return
        
        if amount > user_data.balance:
            await update.message.reply_text(
                f"⚠️ *Insufficient Balance*\n\n"
                f"Your balance: {Utils.format_number(user_data.balance)} REFi\n"
                f"Requested: {Utils.format_number(amount)} REFi"
            )
            context.user_data.pop('state', None)
            return
        
        context.user_data['withdraw_amount'] = amount
        context.user_data['state'] = UserState.WAITING_WALLET_ADDRESS
        
        await update.message.reply_text(
            "📮 *Enter your wallet address*\n\n"
            "Please enter your Ethereum wallet address (starts with 0x):\n"
            "Example: `0x742d35Cc6634C0532925a3b844Bc454e4438f44e`",
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    async def handle_wallet_address(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        user_data = db.get_user(user_id)
        wallet = update.message.text.strip()
        
        if not user_data:
            await update.message.reply_text("❌ Please send /start first")
            return
        
        if not Utils.is_valid_eth_wallet(wallet):
            await update.message.reply_text(
                "❌ *Invalid wallet address*\n\n"
                "Please enter a valid Ethereum wallet address starting with 0x",
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
        
        # Create withdrawal
        withdrawal = db.create_withdrawal(user_id, amount, wallet)
        
        # Update user
        db.update_user(user_id, 
                      balance=user_data.balance,
                      wallet_address=wallet)
        
        context.user_data.pop('state', None)
        context.user_data.pop('withdraw_amount', None)
        
        amount_usd = Utils.refi_to_usd(amount)
        
        await update.message.reply_text(
            f"✅ *Withdrawal Request Submitted!*\n\n"
            f"📝 Request ID: `{withdrawal.request_id}`\n"
            f"💰 Amount: {Utils.format_number(amount)} REFi (${amount_usd:.2f})\n"
            f"📮 Wallet: `{Utils.short_wallet(wallet)}`\n\n"
            f"⏳ Status: *Pending Review*",
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
                        f"User: {user_data.first_name} (@{user_data.username})\n"
                        f"Amount: {Utils.format_number(amount)} REFi\n"
                        f"Wallet: {wallet}"
                    )
                )
            except:
                pass
    
    # ========== ADMIN ==========
    @staticmethod
    async def admin_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        
        if user.id not in Config.ADMIN_IDS:
            await update.message.reply_text("⛔ Unauthorized")
            return ConversationHandler.END
        
        if db.is_admin_session_valid(user.id):
            await Handlers._show_admin_panel(update, context)
            return ConversationHandler.END
        
        await update.message.reply_text(
            "🔐 *Admin Login*\n\nPlease enter the admin password:",
            parse_mode=ParseMode.MARKDOWN
        )
        
        return 1  # WAITING_ADMIN_PASS
    
    @staticmethod
    async def handle_admin_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        password = update.message.text
        
        if password == Config.ADMIN_PASSWORD:
            db.create_admin_session(user.id)
            
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
        stats = db.get_stats()
        uptime_seconds = stats['uptime']
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        text = (
            f"👑 *Admin Panel*\n\n"
            f"📊 *Statistics*\n"
            f"• Total users: {stats['total_users']}\n"
            f"• Verified users: {stats['users_verified']}\n"
            f"• Total balance: {Utils.format_number(stats['total_balance'])} REFi\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n"
            f"• Uptime: {hours}h {minutes}m\n\n"
            f"Choose an option:"
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
    async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        stats = db.get_stats()
        users = list(db.users.values())
        
        active_today = [u for u in users if u.last_active > time.time() - 86400]
        active_week = [u for u in users if u.last_active > time.time() - 604800]
        total_earned = sum(u.total_earned for u in users)
        
        uptime_seconds = stats['uptime']
        hours = uptime_seconds // 3600
        minutes = (uptime_seconds % 3600) // 60
        
        text = (
            f"📊 *Detailed Statistics*\n\n"
            f"👥 *Users*\n"
            f"• Total: {stats['total_users']}\n"
            f"• Verified: {stats['users_verified']}\n"
            f"• Active today: {len(active_today)}\n"
            f"• Active week: {len(active_week)}\n\n"
            f"💰 *Financial*\n"
            f"• Total balance: {Utils.format_number(stats['total_balance'])} REFi\n"
            f"• Total earned: {Utils.format_number(total_earned)} REFi\n"
            f"• Total withdrawn: {Utils.format_number(stats['total_withdrawn_amount'])} REFi\n"
            f"• Pending withdrawals: {stats['pending_withdrawals']}\n\n"
            f"📈 *Referrals*\n"
            f"• Total referrals: {stats['total_referrals']}\n\n"
            f"⏱️ *Bot Stats*\n"
            f"• Commands: {stats.get('commands_processed', 0)}\n"
            f"• Uptime: {hours}h {minutes}m"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.admin(),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    async def admin_withdrawals(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        pending = db.get_pending_withdrawals()
        
        if not pending:
            await query.edit_message_text(
                "✅ No pending withdrawals.",
                reply_markup=Keyboards.admin()
            )
            return
        
        text = "💰 *Pending Withdrawals*\n\n"
        
        for w in pending[:5]:
            user = db.get_user(w.user_id)
            user_name = user.first_name if user else "Unknown"
            text += (
                f"🆔 `{w.request_id[:8]}...`\n"
                f"👤 {user_name}\n"
                f"💰 {Utils.format_number(w.amount)} REFi\n"
                f"📅 {Utils.get_date(w.created_at)}\n\n"
            )
        
        if len(pending) > 5:
            text += f"*... and {len(pending) - 5} more*\n\n"
        
        keyboard = []
        for w in pending[:5]:
            keyboard.append([InlineKeyboardButton(
                f"Process {w.request_id[:8]}", 
                callback_data=f"withdrawal_{w.request_id}"
            )])
        
        keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="admin_panel")])
        
        await query.edit_message_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    async def admin_withdrawal_detail(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        request_id = data.replace('withdrawal_', '')
        
        withdrawal = db.get_withdrawal(request_id)
        if not withdrawal:
            await query.answer("❌ Withdrawal not found")
            return
        
        user = db.get_user(withdrawal.user_id)
        amount_usd = Utils.refi_to_usd(withdrawal.amount)
        
        text = (
            f"💰 *Withdrawal Details*\n\n"
            f"🆔 Request: `{withdrawal.request_id}`\n"
            f"👤 User: {user.first_name} (@{user.username})\n"
            f"💰 Amount: {Utils.format_number(withdrawal.amount)} REFi (${amount_usd:.2f})\n"
            f"📮 Wallet: `{withdrawal.wallet_address}`\n"
            f"📅 Created: {Utils.get_date(withdrawal.created_at)}\n"
            f"📊 Status: {withdrawal.status.value}"
        )
        
        await query.edit_message_text(
            text,
            reply_markup=Keyboards.withdrawal_actions(request_id),
            parse_mode=ParseMode.MARKDOWN
        )
    
    @staticmethod
    async def handle_withdrawal_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        data = query.data
        
        if data.startswith('approve_'):
            request_id = data[8:]
            action = 'approve'
        elif data.startswith('reject_'):
            request_id = data[7:]
            action = 'reject'
        else:
            return
        
        withdrawal = db.get_withdrawal(request_id)
        if not withdrawal:
            await query.answer("❌ Withdrawal not found")
            return
        
        user = db.get_user(withdrawal.user_id)
        
        if action == 'approve':
            db.process_withdrawal(request_id, update.effective_user.id, 
                                 WithdrawalStatus.APPROVED)
            
            await query.edit_message_text(
                f"✅ *Withdrawal Approved*\n\n"
                f"Request: `{request_id}`\n"
                f"User: {user.first_name}\n"
                f"Amount: {Utils.format_number(withdrawal.amount)} REFi",
                reply_markup=Keyboards.admin()
            )
            
            try:
                await context.bot.send_message(
                    chat_id=withdrawal.user_id,
                    text=f"✅ Your withdrawal of {Utils.format_number(withdrawal.amount)} REFi has been approved!"
                )
            except:
                pass
        else:
            db.process_withdrawal(request_id, update.effective_user.id,
                                 WithdrawalStatus.REJECTED)
            
            await query.edit_message_text(
                f"❌ *Withdrawal Rejected*\n\n"
                f"Request: `{request_id}`\n"
                f"User: {user.first_name}\n"
                f"Amount: {Utils.format_number(withdrawal.amount)} REFi\n\n"
                f"Funds returned to user.",
                reply_markup=Keyboards.admin()
            )
            
            try:
                await context.bot.send_message(
                    chat_id=withdrawal.user_id,
                    text=(
                        f"❌ Your withdrawal of {Utils.format_number(withdrawal.amount)} REFi was rejected.\n"
                        f"The amount has been returned to your balance."
                    )
                )
            except:
                pass
    
    @staticmethod
    async def admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "🔍 *Search User*\n\n"
            "Send me the User ID or username to search for.\n\n"
            "Examples:\n"
            "• `1653918641` (User ID)\n"
            "• `@username` (Username)",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['admin_search'] = True
    
    @staticmethod
    async def handle_admin_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query_text = update.message.text.strip()
        user = None
        
        if query_text.isdigit():
            user_id = int(query_text)
            user = db.get_user(user_id)
        else:
            username = query_text.lstrip('@').lower()
            for u in db.users.values():
                if u.username and u.username.lower() == username:
                    user = u
                    break
        
        if not user:
            await update.message.reply_text(f"❌ User not found: {query_text}")
            context.user_data.pop('admin_search', None)
            return
        
        balance_usd = Utils.refi_to_usd(user.balance)
        total_earned_usd = Utils.refi_to_usd(user.total_earned)
        
        text = (
            f"👤 *User Information*\n\n"
            f"• ID: `{user.user_id}`\n"
            f"• Username: @{user.username}\n"
            f"• Name: {user.first_name}\n"
            f"• Joined: {Utils.get_date(user.joined_at)}\n"
            f"• Last active: {Utils.get_date(user.last_active)}\n\n"
            f"💰 *Financial*\n"
            f"• Balance: {Utils.format_number(user.balance)} REFi (${balance_usd:.2f})\n"
            f"• Total earned: {Utils.format_number(user.total_earned)} REFi (${total_earned_usd:.2f})\n"
            f"• Total withdrawn: {Utils.format_number(user.total_withdrawn)} REFi\n\n"
            f"👥 *Referrals*\n"
            f"• Total: {user.referrals_count}\n"
            f"• Code: `{user.referral_code}`\n\n"
            f"✅ *Status*\n"
            f"• Verified: {'✅' if user.verification_status == VerificationStatus.VERIFIED else '❌'}\n"
            f"• Wallet: {user.wallet_address or 'Not set'}\n"
            f"• Admin: {'✅' if user.is_admin else '❌'}\n"
            f"• Banned: {'✅' if user.is_banned else '❌'}"
        )
        
        await update.message.reply_text(text, parse_mode=ParseMode.MARKDOWN)
        context.user_data.pop('admin_search', None)
    
    @staticmethod
    async def admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📢 *Broadcast Message*\n\n"
            "Send me the message you want to broadcast to all users.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        context.user_data['admin_broadcast'] = True
    
    @staticmethod
    async def handle_admin_broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
        message_text = update.message.text
        total_users = len(db.users)
        
        await update.message.reply_text(f"📢 Broadcasting to {total_users} users...")
        
        sent = 0
        failed = 0
        
        for user_id in db.users.keys():
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=message_text,
                    parse_mode=ParseMode.MARKDOWN
                )
                sent += 1
                if sent % 10 == 0:
                    await asyncio.sleep(0.5)
            except Exception as e:
                failed += 1
                logger.error(f"Broadcast failed to {user_id}: {e}")
        
        await update.message.reply_text(
            f"✅ *Broadcast Complete*\n\n"
            f"• Sent: {sent}\n"
            f"• Failed: {failed}",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=Keyboards.admin()
        )
        
        context.user_data.pop('admin_broadcast', None)
    
    @staticmethod
    async def admin_logout(update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        db.end_admin_session(user_id)
        
        await query.edit_message_text(
            "🔒 Logged out.",
            reply_markup=Keyboards.main()
        )
    
    @staticmethod
    async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await Handlers._show_admin_panel(update, context)
    
    # ========== UNKNOWN ==========
    @staticmethod
    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "❌ Unknown command. Use /start to begin."
        )
    
    # ========== ERROR ==========
    @staticmethod
    async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
        logger.error(f"Update {update} caused error {context.error}")

# ==================== MAIN ====================

def main():
    """Main function"""
    
    print("\n" + "="*60)
    print("🤖 REFi REFERRAL BOT - COMPLETE EDITION")
    print("="*60)
    print(f"📱 Bot Token: {Config.BOT_TOKEN[:15]}...")
    print(f"👤 Admin IDs: {Config.ADMIN_IDS}")
    print(f"💰 Welcome Bonus: {Utils.format_number(Config.WELCOME_BONUS)} REFi")
    print(f"👥 Referral Bonus: {Utils.format_number(Config.REFERRAL_BONUS)} REFi")
    print(f"💸 Min Withdraw: {Utils.format_number(Config.MIN_WITHDRAW)} REFi")
    print(f"👥 Total Users: {len(db.users)}")
    print("="*60 + "\n")
    
    # Create application
    defaults = Defaults(parse_mode=ParseMode.MARKDOWN)
    app = Application.builder().token(Config.BOT_TOKEN).defaults(defaults).build()
    
    # Admin login conversation
    admin_conv = ConversationHandler(
        entry_points=[CommandHandler("admin", Handlers.admin_login)],
        states={
            1: [MessageHandler(filters.TEXT & ~filters.COMMAND, Handlers.handle_admin_password)]
        },
        fallbacks=[]
    )
    
    # Add handlers
    app.add_handler(CommandHandler("start", Handlers.start))
    app.add_handler(admin_conv)
    app.add_handler(MessageHandler(filters.COMMAND, Handlers.unknown_command))
    
    # Callbacks
    app.add_handler(CallbackQueryHandler(Handlers.verify_callback, pattern="^verify$"))
    app.add_handler(CallbackQueryHandler(Handlers.main_menu, pattern="^main_menu$"))
    app.add_handler(CallbackQueryHandler(Handlers.balance, pattern="^balance$"))
    app.add_handler(CallbackQueryHandler(Handlers.referral, pattern="^referral$"))
    app.add_handler(CallbackQueryHandler(Handlers.stats, pattern="^stats$"))
    app.add_handler(CallbackQueryHandler(Handlers.withdraw, pattern="^withdraw$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_panel, pattern="^admin_panel$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_stats, pattern="^admin_stats$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_withdrawals, pattern="^admin_withdrawals$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_search, pattern="^admin_search$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_broadcast, pattern="^admin_broadcast$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_logout, pattern="^admin_logout$"))
    app.add_handler(CallbackQueryHandler(Handlers.admin_withdrawal_detail, pattern="^withdrawal_"))
    app.add_handler(CallbackQueryHandler(Handlers.handle_withdrawal_action, pattern="^(approve|reject)_"))
    
    # Message handlers
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_withdraw_amount,
        lambda ctx: ctx.user_data.get('state') == UserState.WAITING_WITHDRAW_AMOUNT
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_wallet_address,
        lambda ctx: ctx.user_data.get('state') == UserState.WAITING_WALLET_ADDRESS
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_admin_search,
        lambda ctx: ctx.user_data.get('admin_search')
    ))
    
    app.add_handler(MessageHandler(
        filters.TEXT & filters.ChatType.PRIVATE & ~filters.COMMAND,
        Handlers.handle_admin_broadcast,
        lambda ctx: ctx.user_data.get('admin_broadcast')
    ))
    
    # Error handler
    app.add_error_handler(Handlers.error_handler)
    
    # Start bot
    logger.info("🚀 Starting bot...")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    print("="*60 + "\n")
    
    app.run_polling()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Bot stopped by user")
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        logger.exception("Fatal error")

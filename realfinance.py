"""
Telegram Referral & Earn Bot
Single file bot for REFi token rewards
"""

import os
import logging
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
import firebase_admin
from firebase_admin import credentials, db
import json

# ================== CONFIGURATION ==================

# Bot Token - from environment variables
BOT_TOKEN = os.environ.get('BOT_TOKEN')
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN not set!")

# Firebase config (can be public)
FIREBASE_CONFIG = {
    "databaseURL": "https://your-project.firebaseio.com/"  # Put your database URL here
}

# Admin settings
ADMIN_IDS = [123456789, 987654321]  # Put admin user IDs here
ADMIN_PASSWORD = "Admin@2024"  # Admin password

# ================== TOKENOMICS ==================

# REFi token price (fixed)
COIN_PRICE = 0.000002  # $0.000002 per REFi (1 million REFi = $2)

# Rewards (1 million REFi each)
WELCOME_BONUS = 1_000_000  # 1,000,000 REFi welcome bonus
REFERRAL_BONUS = 1_000_000  # 1,000,000 REFi per referral

# Value display
MILLION_REFi_VALUE = 2.00  # 1 million REFi = $2.00

# Withdrawal settings
MIN_WITHDRAW = 5_000_000  # Minimum 5,000,000 REFi to withdraw
MIN_WITHDRAW_USD = 10.00  # $10.00 minimum

# Required channels
REQUIRED_CHANNELS = [
    {"name": "My Channel 1", "link": "https://t.me/mychannel1", "id": -1001234567890},
    {"name": "My Channel 2", "link": "https://t.me/mychannel2", "id": -1001234567891}
]

# Helper functions for conversion
def refi_to_usd(refi_amount: int) -> float:
    """Convert REFi to USD (1 million REFi = $2)"""
    return (refi_amount / 1_000_000) * 2.00

def usd_to_refi(usd_amount: float) -> int:
    """Convert USD to REFi"""
    return int((usd_amount / 2.00) * 1_000_000)

def format_number(num: int) -> str:
    """Format large numbers with commas"""
    return f"{num:,}"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ================== FIREBASE INIT ==================

# Initialize Firebase
try:
    firebase_admin.get_app()
except ValueError:
    # If not initialized, do it now
    cred = credentials.Certificate({
        "type": "service_account",
        "project_id": "your-project-id",
        "private_key_id": "your-private-key-id",
        "private_key": "your-private-key",
        "client_email": "your-client-email",
        "client_id": "your-client-id",
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    })
    firebase_admin.initialize_app(cred, FIREBASE_CONFIG)

ref = db.reference('/')

# ================== SESSION STORAGE ==================
active_sessions = {}  # For admin sessions
user_states = {}  # For user states (withdrawal, etc.)

# ================== HELPER FUNCTIONS ==================

def is_admin(user_id: int) -> bool:
    """Check if user is admin"""
    return user_id in ADMIN_IDS

def has_active_session(user_id: int) -> bool:
    """Check if admin has active session"""
    if user_id in active_sessions:
        if active_sessions[user_id] > time.time():
            return True
        else:
            del active_sessions[user_id]
    return False

def get_user_data(user_id: int) -> dict:
    """Get user data from Firebase"""
    user_ref = ref.child(f'users/{user_id}')
    return user_ref.get() or {}

def save_user_data(user_id: int, data: dict):
    """Save user data to Firebase"""
    ref.child(f'users/{user_id}').set(data)

def generate_referral_code(user_id: int) -> str:
    """Generate unique referral code"""
    import hashlib
    code = hashlib.md5(str(user_id).encode()).hexdigest()[:8]
    return code.upper()

def check_membership(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if user has joined all required channels"""
    try:
        for channel in REQUIRED_CHANNELS:
            member = context.bot.get_chat_member(chat_id=channel["id"], user_id=user_id)
            if member.status in ['left', 'kicked']:
                return False
        return True
    except Exception as e:
        logger.error(f"Error checking membership: {e}")
        return False

# ================== MESSAGES ==================

WELCOME_MESSAGE = """
🎉 *Welcome to REFi Earn Bot!*

💰 *Welcome Bonus:* {welcome:,} REFi (${welcome_usd:.2f})
👥 *Referral Bonus:* {referral:,} REFi (${referral_usd:.2f}) per friend

📢 To start, you must join these channels:
{channels}

👇 Click 'Verify' after joining
"""

MAIN_MENU_TEXT = """
✅ *Verification successful!*

💰 Your welcome bonus of {welcome:,} REFi (${welcome_usd:.2f}) has been added!

👥 Share your referral link with friends and earn {referral:,} REFi (${referral_usd:.2f}) each
"""

BALANCE_TEXT = """
💰 *Your Balance*

• *REFi:* {balance:,}
• *USD:* ${balance_usd:.2f}

📊 *Statistics:*
• Total referrals: {referrals}
• Total earned: {total_earned:,} REFi (${total_earned_usd:.2f})
• Referral earnings: {ref_earned:,} REFi (${ref_earned_usd:.2f})
"""

REFERRAL_TEXT = """
🔗 *Your Referral Link:*
`https://t.me/{{bot_username}}?start={code}`

📋 Copy and share with friends!

🎁 *Rewards:*
• You get: {referral:,} REFi (${referral_usd:.2f}) per referral
• Your friend

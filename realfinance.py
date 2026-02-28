#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - FINAL WORKING VERSION                                          ║
║     Telegram Referral & Earn Bot with All Features                               ║
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

# ==================== REQUESTS ====================
try:
    import requests
except ImportError:
    os.system("pip install requests==2.31.0")
    import requests

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAE8nFWsJCX-8tAmfxis6UFgVUfPLGLt5pA"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

COIN_NAME = "REFi"
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# ==================== DATABASE ====================
db_lock = threading.Lock()
db = {"users": {}, "withdrawals": {}, "admin_sessions": {}, "stats": {"start_time": time.time()}}

def save_db():
    with db_lock:
        try:
            with open("bot_data.json", "w") as f:
                json.dump(db, f)
        except: pass

def get_user(user_id):
    uid = str(user_id)
    with db_lock:
        if uid not in db["users"]:
            db["users"][uid] = {
                "id": uid, "username": "", "first_name": "",
                "joined_at": time.time(), "last_active": time.time(),
                "balance": 0, "total_earned": 0, "total_withdrawn": 0,
                "referral_code": ''.join(random.choices(string.ascii_uppercase + string.digits, k=8)),
                "referred_by": None, "referrals_count": 0, "referrals": {},
                "referral_clicks": 0, "verified": False,
                "wallet": None, "is_admin": int(uid) in ADMIN_IDS
            }
            save_db()
        return db["users"][uid]

def update_user(user_id, **kwargs):
    with db_lock:
        uid = str(user_id)
        if uid in db["users"]:
            db["users"][uid].update(kwargs)
            db["users"][uid]["last_active"] = time.time()
            save_db()

def get_user_by_code(code):
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def format_refi(refi):
    usd = (refi / 1_000_000) * 2.0
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "Not set"

def is_valid_wallet(w):
    return w and w.startswith('0x') and len(w) == 42

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 Join {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ VERIFY", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    kb = [
        [{"text": "💰 Balance", "callback_data": "bal"}, {"text": "🔗 Referral", "callback_data": "ref"}],
        [{"text": "💸 Withdraw", "callback_data": "wd"}, {"text": "📊 Stats", "callback_data": "stats"}]
    ]
    if not user.get("wallet"):
        kb.append([{"text": "👛 Set Wallet", "callback_data": "wallet"}])
    if user.get("is_admin"):
        kb.append([{"text": "👑 Admin", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

# ==================== TELEGRAM ====================
def send_msg(chat_id, text, kb=None):
    try:
        return requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except: return None

def edit_msg(chat_id, msg_id, text, kb=None):
    try:
        return requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": msg_id, "text": text,
            "parse_mode": "Markdown", "reply_markup": kb
        }, timeout=10)
    except: return None

def answer_cb(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except: pass

def get_chat_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
        return r.json().get("result", {}).get("status")
    except: return None

# ==================== HANDLERS ====================
user_states = {}

def handle_start(msg):
    chat_id = msg["chat"]["id"]
    user = msg["from"]
    uid = user["id"]
    text = msg.get("text", "")
    
    logger.info(f"▶️ Start: {uid}")
    
    # Referral
    args = text.split()
    if len(args) > 1:
        ref = args[1]
        referrer = get_user_by_code(ref)
        if referrer and referrer["id"] != str(uid):
            u = get_user(uid)
            if not u.get("referred_by"):
                update_user(uid, referred_by=referrer["id"])
                referrer["referral_clicks"] = referrer.get("referral_clicks", 0) + 1
                update_user(int(referrer["id"]), referral_clicks=referrer["referral_clicks"])
    
    u = get_user(uid)
    update_user(uid, username=user.get("username", ""), first_name=user.get("first_name", ""))
    
    if u.get("verified"):
        send_msg(chat_id, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    ch_txt = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    send_msg(chat_id,
        f"🎉 *Welcome!*\n💰 Welcome: {format_refi(WELCOME_BONUS)}\n👥 Referral: {format_refi(REFERRAL_BONUS)}/friend\n📢 Join:\n{ch_txt}",
        channels_kb())

def handle_verify(cb, uid, chat_id, msg_id):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_chat_member(ch["username"], uid)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        edit_msg(chat_id, msg_id, "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined]), channels_kb())
        return
    
    u = get_user(uid)
    if u.get("verified"):
        edit_msg(chat_id, msg_id, f"✅ Already verified!\n{format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    new_bal = u.get("balance", 0) + WELCOME_BONUS
    update_user(uid, verified=True, verified_at=time.time(), balance=new_bal,
                total_earned=u.get("total_earned", 0) + WELCOME_BONUS)
    
    if u.get("referred_by"):
        ref = get_user(int(u["referred_by"]))
        if ref:
            ref["balance"] += REFERRAL_BONUS
            ref["total_earned"] += REFERRAL_BONUS
            ref["referrals_count"] += 1
            ref["referrals"][str(uid)] = time.time()
            update_user(int(u["referred_by"]), balance=ref["balance"],
                       total_earned=ref["total_earned"], referrals_count=ref["referrals_count"])
            send_msg(int(u["referred_by"]), f"🎉 Friend joined! You earned {format_refi(REFERRAL_BONUS)}")
    
    edit_msg(chat_id, msg_id, f"✅ *Verified!*\n✨ +{format_refi(WELCOME_BONUS)}\n💰 {format_refi(new_bal)}", main_kb(u))

def handle_bal(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    edit_msg(chat_id, msg_id, f"💰 *Balance*\n• {format_refi(u.get('balance',0))}\n• Total: {format_refi(u.get('total_earned',0))}\n• Referrals: {u.get('referrals_count',0)}", back_kb())

def handle_ref(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    link = f"https://t.me/{BOT_USERNAME}?start={u.get('referral_code','')}"
    earned = u.get('referrals_count',0) * REFERRAL_BONUS
    edit_msg(chat_id, msg_id, f"🔗 *Your Link*\n`{link}`\n\n• You earn: {format_refi(REFERRAL_BONUS)}/friend\n• Clicks: {u.get('referral_clicks',0)}\n• Earned: {format_refi(earned)}", back_kb())

def handle_stats(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    edit_msg(chat_id, msg_id, f"📊 *Stats*\n• ID: `{uid}`\n• Balance: {format_refi(u.get('balance',0))}\n• Referrals: {u.get('referrals_count',0)}\n• Verified: {'✅' if u.get('verified') else '❌'}\n• Wallet: {short_wallet(u.get('wallet',''))}", back_kb())

def handle_wd(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    if not u.get("verified"): edit_msg(chat_id, msg_id, "❌ Verify first!", back_kb()); return
    if not u.get("wallet"): edit_msg(chat_id, msg_id, "⚠️ Set wallet first!", main_kb(u)); return
    bal = u.get("balance",0)
    if bal < MIN_WITHDRAW:
        edit_msg(chat_id, msg_id, f"⚠️ Min: {format_refi(MIN_WITHDRAW)}\nYour: {format_refi(bal)}", back_kb()); return
    edit_msg(chat_id, msg_id, f"💸 *Withdraw*\nBalance: {format_refi(bal)}\nMin: {format_refi(MIN_WITHDRAW)}\nWallet: {short_wallet(u['wallet'])}\n\nSend amount:")
    user_states[uid] = "wd"

def handle_wallet(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    cur = u.get("wallet","Not set")
    if cur != "Not set": cur = short_wallet(cur)
    edit_msg(chat_id, msg_id, f"👛 *Set Wallet*\nCurrent: {cur}\n\nSend ETH address (0x...):")
    user_states[uid] = "wallet"

def handle_back(cb, uid, chat_id, msg_id):
    u = get_user(uid)
    edit_msg(chat_id, msg_id, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_kb(u))

def handle_admin(cb, uid, chat_id, msg_id):
    if uid not in ADMIN_IDS: return
    edit_msg(chat_id, msg_id, "👑 *Admin*\n• Users: 1\n• Pending: 0", back_kb())

def handle_wallet_input(text, uid, chat_id):
    if is_valid_wallet(text):
        update_user(uid, wallet=text)
        u = get_user(uid)
        send_msg(chat_id, f"✅ *Wallet saved!*\n{short_wallet(text)}", main_kb(u))
    else:
        send_msg(chat_id, "❌ Invalid wallet! Must be 0x + 40 chars")

def handle_withdraw_input(text, uid, chat_id):
    try:
        amt = int(text.replace(',',''))
        u = get_user(uid)
        if amt < MIN_WITHDRAW: send_msg(chat_id, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
        elif amt > u.get("balance",0): send_msg(chat_id, f"❌ Insufficient balance")
        else:
            rid = f"W{int(time.time())}{uid}"
            with db_lock:
                db["withdrawals"][rid] = {"id": rid, "user_id": str(uid), "amount": amt, "wallet": u["wallet"], "status": "pending", "created_at": time.time()}
                save_db()
            update_user(uid, balance=u["balance"] - amt)
            send_msg(chat_id, f"✅ *Withdrawal requested!*\nID: {rid[:8]}...", main_kb(u))
    except: send_msg(chat_id, "❌ Invalid number")

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write("<h1>🤖 REFi Bot Running</h1>".encode('utf-8'))
    def log_message(self, *args): pass

def run_web():
    server = HTTPServer(('0.0.0.0', PORT), HealthHandler)
    logger.info(f"🌐 Web on {PORT}")
    server.serve_forever()

threading.Thread(target=run_web, daemon=True).start()

# ==================== MAIN ====================
def main():
    logger.info("🚀 Starting bot...")
    offset = 0
    
    # Clear any old sessions
    try:
        requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
        requests.get(f"{API_URL}/getUpdates", params={"offset": -1})
    except: pass
    
    while True:
        try:
            r = requests.post(f"{API_URL}/getUpdates", json={
                "offset": offset,
                "timeout": 30,
                "allowed_updates": ["message", "callback_query"]
            }, timeout=35)
            data = r.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    # Message
                    if "message" in update:
                        msg = update["message"]
                        if msg.get("text") == "/start":
                            handle_start(msg)
                        elif msg.get("text"):
                            uid = msg["from"]["id"]
                            state = user_states.get(uid)
                            if state == "wallet":
                                handle_wallet_input(msg["text"], uid, msg["chat"]["id"])
                                user_states.pop(uid, None)
                            elif state == "wd":
                                handle_withdraw_input(msg["text"], uid, msg["chat"]["id"])
                                user_states.pop(uid, None)
                    
                    # Callback
                    elif "callback_query" in update:
                        cb = update["callback_query"]
                        data = cb.get("data", "")
                        uid = cb["from"]["id"]
                        chat_id = cb["message"]["chat"]["id"]
                        msg_id = cb["message"]["message_id"]
                        
                        answer_cb(cb["id"])
                        
                        if data == "verify": handle_verify(cb, uid, chat_id, msg_id)
                        elif data == "bal": handle_bal(cb, uid, chat_id, msg_id)
                        elif data == "ref": handle_ref(cb, uid, chat_id, msg_id)
                        elif data == "stats": handle_stats(cb, uid, chat_id, msg_id)
                        elif data == "wd": handle_wd(cb, uid, chat_id, msg_id)
                        elif data == "wallet": handle_wallet(cb, uid, chat_id, msg_id)
                        elif data == "back": handle_back(cb, uid, chat_id, msg_id)
                        elif data == "admin": handle_admin(cb, uid, chat_id, msg_id)
                    
                    offset = update["update_id"] + 1
            elif data.get("error_code") == 409:
                logger.warning("⚠️ Conflict, resetting...")
                requests.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
                time.sleep(5)
                offset = 0
                    
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("👋 Stopped")

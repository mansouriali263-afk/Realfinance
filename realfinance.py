#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
╔══════════════════════════════════════════════════════════════════════════════════╗
║                                                                                  ║
║     🤖 REFi BOT - ULTIMATE FINAL EDITION v18.0                                   ║
║     Telegram Referral & Earn Bot with All Features                               ║
║                                                                                  ║
║     ✨ ALL FEATURES INCLUDED + FULLY COMPLETE CODE                                ║
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
from typing import Optional, List

# ==================== FIX PRINT BUFFERING ====================
print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

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

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFMPJRNrmnte_CzmGxGXFxwbSEi_MsDjt0"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

MAX_PENDING_WITHDRAWALS = 3
SESSION_TIMEOUT = 3600

# ==================== LOGGING ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s | %(message)s')
logger = logging.getLogger(__name__)

# ==================== HTTP SESSION ====================
session = requests.Session()
retries = Retry(total=3, backoff_factor=1)
session.mount('https://', HTTPAdapter(max_retries=retries))

# ==================== DATABASE ====================
db_lock = threading.Lock()
db = {"users": {}, "withdrawals": {}, "admin_sessions": {}, "stats": {"start_time": time.time()}}

def save_db():
    with db_lock:
        try:
            with open("bot_data.json", "w") as f:
                json.dump(db, f)
        except: pass

def load_db():
    try:
        if os.path.exists("bot_data.json"):
            with open("bot_data.json", "r") as f:
                db.update(json.load(f))
    except: pass
load_db()

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
                "wallet": None, "is_admin": int(uid) in ADMIN_IDS, "is_banned": False
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

def get_user_by_username(username):
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
            return u
    return None

def get_pending_withdrawals():
    return [w for w in db["withdrawals"].values() if w.get("status") == "pending"]

def get_user_withdrawals(user_id, status=None):
    uid = str(user_id)
    withdrawals = [w for w in db["withdrawals"].values() if w.get("user_id") == uid]
    if status:
        withdrawals = [w for w in withdrawals if w.get("status") == status]
    return sorted(withdrawals, key=lambda w: w.get("created_at", 0), reverse=True)

def create_withdrawal(user_id, amount, wallet):
    rid = f"W{int(time.time())}{user_id}{random.randint(1000,9999)}"
    with db_lock:
        db["withdrawals"][rid] = {
            "id": rid, "user_id": str(user_id), "amount": amount,
            "wallet": wallet, "status": "pending", "created_at": time.time()
        }
        save_db()
    return rid

def process_withdrawal(rid, admin_id, status):
    with db_lock:
        w = db["withdrawals"].get(rid)
        if not w or w["status"] != "pending":
            return False
        w["status"] = status
        w["processed_at"] = time.time()
        w["processed_by"] = admin_id
        if status == "rejected":
            user = db["users"].get(w["user_id"])
            if user:
                user["balance"] += w["amount"]
        save_db()
        return True

def is_admin_logged_in(admin_id):
    session = db["admin_sessions"].get(str(admin_id))
    if not session or session < time.time():
        return False
    return True

def admin_login(admin_id):
    db["admin_sessions"][str(admin_id)] = time.time() + SESSION_TIMEOUT
    save_db()

def admin_logout(admin_id):
    db["admin_sessions"].pop(str(admin_id), None)
    save_db()

def get_stats():
    users = db["users"].values()
    now = time.time()
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "banned": sum(1 for u in users if u.get("is_banned")),
        "active_today": sum(1 for u in users if u.get("last_active", 0) > now - 86400),
        "total_balance": sum(u.get("balance", 0) for u in users),
        "pending_withdrawals": len(get_pending_withdrawals()),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== UTILS ====================
def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "Not set"

def is_valid_wallet(w):
    return w and w.startswith('0x') and len(w) == 42

def get_date(t=None):
    return datetime.fromtimestamp(t if t else time.time()).strftime('%Y-%m-%d %H:%M')

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

def admin_kb():
    return {"inline_keyboard": [
        [{"text": "📊 Stats", "callback_data": "astats"}],
        [{"text": "💰 Pending", "callback_data": "apending"}],
        [{"text": "🔍 Search", "callback_data": "asearch"}],
        [{"text": "📢 Broadcast", "callback_data": "abcast"}],
        [{"text": "👥 Users", "callback_data": "ausers"}],
        [{"text": "🔒 Logout", "callback_data": "alogout"}]
    ]}

def withdrawal_kb(rid):
    return {"inline_keyboard": [
        [{"text": "✅ Approve", "callback_data": f"app_{rid}"}, {"text": "❌ Reject", "callback_data": f"rej_{rid}"}],
        [{"text": "🔙 Back", "callback_data": "apending"}]
    ]}

def user_actions_kb(uid, banned, admin):
    kb = []
    kb.append([{"text": "🔨 Ban" if not banned else "✅ Unban", "callback_data": f"ban_{uid}" if not banned else f"unban_{uid}"}])
    kb.append([{"text": "👑 Make Admin" if not admin else "👤 Remove Admin", "callback_data": f"mkadmin_{uid}" if not admin else f"rmadmin_{uid}"}])
    kb.append([{"text": "🔙 Back", "callback_data": "admin"}])
    return {"inline_keyboard": kb}

# ==================== TELEGRAM ====================
def send_msg(chat_id, text, kb=None):
    try:
        return session.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": "Markdown", "reply_markup": kb
        }, timeout=10)
    except: return None

def edit_msg(chat_id, msg_id, text, kb=None):
    try:
        return session.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id, "message_id": msg_id, "text": text,
            "parse_mode": "Markdown", "reply_markup": kb
        }, timeout=10)
    except: return None

def answer_cb(cb_id):
    try:
        session.post(f"{API_URL}/answerCallbackQuery", json={"callback_query_id": cb_id}, timeout=5)
    except: pass

def get_chat_member(chat_id, user_id):
    try:
        r = session.get(f"{API_URL}/getChatMember", params={"chat_id": chat_id, "user_id": user_id}, timeout=5)
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
            ref["balance"] = ref.get("balance", 0) + REFERRAL_BONUS
            ref["total_earned"] = ref.get("total_earned", 0) + REFERRAL_BONUS
            ref["referrals_count"] = ref.get("referrals_count", 0) + 1
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
    if not u.get("verified"): 
        edit_msg(chat_id, msg_id, "❌ Verify first!", back_kb())
        return
    if not u.get("wallet"): 
        edit_msg(chat_id, msg_id, "⚠️ Set wallet first!", main_kb(u))
        return
    bal = u.get("balance",0)
    if bal < MIN_WITHDRAW:
        edit_msg(chat_id, msg_id, f"⚠️ Min: {format_refi(MIN_WITHDRAW)}\nYour: {format_refi(bal)}", back_kb())
        return
    pending = get_user_withdrawals(uid, "pending")
    if len(pending) >= MAX_PENDING_WITHDRAWALS:
        edit_msg(chat_id, msg_id, f"⚠️ You have {len(pending)} pending withdrawals", back_kb())
        return
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
    if not is_admin_logged_in(uid):
        edit_msg(chat_id, msg_id, "🔐 Login with /admin", main_kb(get_user(uid)))
        return
    s = get_stats()
    edit_msg(chat_id, msg_id, f"👑 *Admin*\nUsers: {s['total_users']} (✅ {s['verified']})\nBalance: {format_refi(s['total_balance'])}\nPending: {s['pending_withdrawals']}", admin_kb())

# ==================== ADMIN HANDLERS ====================
def handle_admin_login(msg):
    cid = msg["chat"]["id"]
    uid = msg["from"]["id"]
    if uid not in ADMIN_IDS: 
        send_msg(cid, "⛔ Unauthorized")
        return
    if is_admin_logged_in(uid):
        s = get_stats()
        send_msg(cid, f"👑 *Admin*\nUsers: {s['total_users']}\nPending: {s['pending_withdrawals']}", admin_kb())
        return
    send_msg(cid, "🔐 Enter password:")
    user_states[uid] = "admin_login"

def handle_admin_login_input(txt, uid, cid):
    if txt == ADMIN_PASSWORD:
        admin_login(uid)
        send_msg(cid, "✅ Login successful!")
        s = get_stats()
        send_msg(cid, f"👑 *Admin*\nUsers: {s['total_users']}\nPending: {s['pending_withdrawals']}", admin_kb())
    else:
        send_msg(cid, "❌ Wrong password!")

def handle_admin_stats(cb, cid, mid):
    s = get_stats()
    edit_msg(cid, mid, f"📊 *Stats*\n👥 Users: {s['total_users']} (✅ {s['verified']})\n🚫 Banned: {s['banned']}\n📅 Active today: {s['active_today']}\n💰 Balance: {format_refi(s['total_balance'])}\n⏳ Pending: {s['pending_withdrawals']}", admin_kb())

def handle_admin_pending(cb, cid, mid):
    pending = get_pending_withdrawals()
    if not pending:
        edit_msg(cid, mid, "✅ No pending withdrawals", admin_kb())
        return
    txt = "💰 *Pending Withdrawals*\n\n"
    kb = {"inline_keyboard": []}
    for w in pending[:5]:
        u = get_user(int(w["user_id"]))
        txt += f"🆔 `{w['id'][:8]}`\n👤 {u.get('first_name','Unknown')}\n💰 {format_refi(w['amount'])}\n📅 {get_date(w['created_at'])}\n\n"
        kb["inline_keyboard"].append([{"text": f"Process {w['id'][:8]}", "callback_data": f"proc_{w['id']}"}])
    if len(pending) > 5:
        txt += f"*... and {len(pending)-5} more*\n\n"
    kb["inline_keyboard"].append([{"text": "🔙 Back", "callback_data": "admin"}])
    edit_msg(cid, mid, txt, kb)

def handle_process(cb, cid, mid, rid):
    w = db["withdrawals"].get(rid)
    if not w: return
    u = get_user(int(w["user_id"]))
    txt = f"💰 *Withdrawal Details*\n📝 Request: `{rid}`\n👤 {u.get('first_name','Unknown')} (@{u.get('username','')})\n💰 {format_refi(w['amount'])}\n📮 {w['wallet']}\n📅 {get_date(w['created_at'])}"
    edit_msg(cid, mid, txt, withdrawal_kb(rid))

def handle_approve(cb, aid, cid, mid, rid):
    if process_withdrawal(rid, aid, "approved"):
        w = db["withdrawals"].get(rid)
        if w:
            send_msg(int(w["user_id"]), f"✅ *Approved!*\nRequest: {rid[:8]}...\nAmount: {format_refi(w['amount'])}")
    handle_admin_pending(cb, cid, mid)

def handle_reject(cb, aid, cid, mid, rid):
    if process_withdrawal(rid, aid, "rejected"):
        w = db["withdrawals"].get(rid)
        if w:
            send_msg(int(w["user_id"]), f"❌ *Rejected*\nRequest: {rid[:8]}...\nAmount: {format_refi(w['amount'])}")
    handle_admin_pending(cb, cid, mid)

def handle_admin_search(cb, cid, mid):
    edit_msg(cid, mid, "🔍 *Send User ID or @username:*")
    user_states[cb["from"]["id"]] = "admin_search"

def handle_admin_search_input(txt, aid, cid):
    found = get_user(int(txt)) if txt.isdigit() else get_user_by_username(txt)
    if not found:
        send_msg(cid, f"❌ Not found: {txt}")
        return
    p = len(get_user_withdrawals(int(found["id"]), "pending"))
    txt = f"👤 *User Found*\nID: `{found['id']}`\nUsername: @{found.get('username','None')}\nName: {found.get('first_name','Unknown')}\nBalance: {format_refi(found.get('balance',0))}\nReferrals: {found.get('referrals_count',0)}\nVerified: {'✅' if found.get('verified') else '❌'}\nWallet: {short_wallet(found.get('wallet',''))}\nPending: {p}"
    send_msg(cid, txt, user_actions_kb(int(found["id"]), found.get("is_banned", False), found.get("is_admin", False)))

def handle_admin_broadcast(cb, cid, mid):
    edit_msg(cid, mid, f"📢 *Broadcast*\nSend message to {len(db['users'])} users:")
    user_states[cb["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(txt, aid, cid):
    send_msg(cid, f"📢 Broadcasting...")
    sent = 0
    failed = 0
    for uid in db["users"].keys():
        try:
            send_msg(int(uid), txt)
            sent += 1
            if sent % 10 == 0:
                time.sleep(0.5)
        except:
            failed += 1
    send_msg(cid, f"✅ *Done*\nSent: {sent}\nFailed: {failed}", admin_kb())

def handle_admin_users(cb, cid, mid):
    users = sorted(db["users"].values(), key=lambda u: u.get("joined_at", 0), reverse=True)[:10]
    txt = "👥 *Recent Users*\n\n"
    for u in users:
        name = u.get("first_name", "Unknown")
        user = f"@{u.get('username','')}" if u.get('username') else "No username"
        v = "✅" if u.get("verified") else "❌"
        txt += f"{v} {name} {user}\n"
    txt += f"\nTotal: {len(db['users'])}"
    edit_msg(cid, mid, txt, admin_kb())

def handle_admin_logout(cb, aid, cid, mid):
    admin_logout(aid)
    u = get_user(aid)
    edit_msg(cid, mid, f"🔒 Logged out\n💰 {format_refi(u.get('balance',0))}", main_kb(u))

def handle_user_action(cb, aid, cid, mid, action, target):
    if action == "ban":
        update_user(target, is_banned=True)
    elif action == "unban":
        update_user(target, is_banned=False)
    elif action == "mkadmin":
        update_user(target, is_admin=True)
    elif action == "rmadmin":
        update_user(target, is_admin=False)
    handle_admin_search_input(str(target), aid, cid)

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(txt, uid, cid):
    if is_valid_wallet(txt):
        update_user(uid, wallet=txt)
        u = get_user(uid)
        send_msg(cid, f"✅ *Wallet saved!*\n{short_wallet(txt)}", main_kb(u))
    else:
        send_msg(cid, "❌ Invalid wallet! Must be 0x + 40 chars")

def handle_withdraw_input(txt, uid, cid):
    try:
        amt = int(txt.replace(',',''))
    except:
        send_msg(cid, "❌ Invalid number")
        return
    u = get_user(uid)
    if amt < MIN_WITHDRAW:
        send_msg(cid, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
    elif amt > u.get("balance",0):
        send_msg(cid, f"❌ Insufficient balance")
    else:
        rid = create_withdrawal(uid, amt, u["wallet"])
        update_user(uid, balance=u["balance"] - amt)
        send_msg(cid, f"✅ *Withdrawal requested!*\nID: {rid[:8]}...", main_kb(u))
        for aid in ADMIN_IDS:
            send_msg(aid, f"💰 *New Withdrawal*\nUser: {u.get('first_name','')} (@{u.get('username','')})\nAmount: {format_refi(amt)}\nWallet: {u['wallet']}\nID: {rid}")

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        s = get_stats()
        html = f"<h1>🤖 REFi Bot</h1><p>🟢 Running</p><p>Users: {s['total_users']}</p>"
        self.wfile.write(html.encode('utf-8'))
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
logger.info(f"🌐 Web on {PORT}")

# ==================== CLEAR OLD SESSIONS ====================
try:
    session.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
    session.get(f"{API_URL}/getUpdates", params={"offset": -1})
except: pass

# ==================== MAIN ====================
offset = 0
logger.info("🚀 Starting bot...")

while True:
    try:
        r = session.post(f"{API_URL}/getUpdates", json={
            "offset": offset, "timeout": 30, "allowed_updates": ["message", "callback_query"]
        }, timeout=35)
        data = r.json()
        
        if data.get("ok"):
            for update in data.get("result", []):
                if "message" in update:
                    msg = update["message"]
                    cid = msg["chat"]["id"]
                    uid = msg["from"]["id"]
                    txt = msg.get("text", "")
                    
                    if get_user(uid).get("is_banned"):
                        send_msg(cid, "⛔ You are banned")
                        offset = update["update_id"] + 1
                        continue
                    
                    if txt == "/start":
                        handle_start(msg)
                    elif txt == "/admin":
                        handle_admin_login(msg)
                    elif txt.startswith("/"):
                        send_msg(cid, "❌ Unknown command")
                    else:
                        state = user_states.get(uid)
                        if state == "wallet":
                            handle_wallet_input(txt, uid, cid)
                            user_states.pop(uid, None)
                        elif state == "wd":
                            handle_withdraw_input(txt, uid, cid)
                            user_states.pop(uid, None)
                        elif state == "admin_login":
                            handle_admin_login_input(txt, uid, cid)
                            user_states.pop(uid, None)
                        elif state == "admin_search":
                            handle_admin_search_input(txt, uid, cid)
                            user_states.pop(uid, None)
                        elif state == "admin_broadcast":
                            handle_admin_broadcast_input(txt, uid, cid)
                            user_states.pop(uid, None)
                
                elif "callback_query" in update:
                    cb = update["callback_query"]
                    d = cb.get("data", "")
                    uid = cb["from"]["id"]
                    cid = cb["message"]["chat"]["id"]
                    mid = cb["message"]["message_id"]
                    
                    answer_cb(cb["id"])
                    
                    if d == "verify": handle_verify(cb, uid, cid, mid)
                    elif d == "bal": handle_bal(cb, uid, cid, mid)
                    elif d == "ref": handle_ref(cb, uid, cid, mid)
                    elif d == "stats": handle_stats(cb, uid, cid, mid)
                    elif d == "wd": handle_wd(cb, uid, cid, mid)
                    elif d == "wallet": handle_wallet(cb, uid, cid, mid)
                    elif d == "back": handle_back(cb, uid, cid, mid)
                    elif d == "admin": handle_admin(cb, uid, cid, mid)
                    elif d == "astats": handle_admin_stats(cb, cid, mid)
                    elif d == "apending": handle_admin_pending(cb, cid, mid)
                    elif d == "asearch": handle_admin_search(cb, cid, mid)
                    elif d == "abcast": handle_admin_broadcast(cb, cid, mid)
                    elif d == "ausers": handle_admin_users(cb, cid, mid)
                    elif d == "alogout": handle_admin_logout(cb, uid, cid, mid)
                    elif d.startswith("proc_"): handle_process(cb, cid, mid, d[5:])
                    elif d.startswith("app_"): handle_approve(cb, uid, cid, mid, d[4:])
                    elif d.startswith("rej_"): handle_reject(cb, uid, cid, mid, d[4:])
                    elif d.startswith("ban_"): handle_user_action(cb, uid, cid, mid, "ban", int(d[4:]))
                    elif d.startswith("unban_"): handle_user_action(cb, uid, cid, mid, "unban", int(d[6:]))
                    elif d.startswith("mkadmin_"): handle_user_action(cb, uid, cid, mid, "mkadmin", int(d[8:]))
                    elif d.startswith("rmadmin_"): handle_user_action(cb, uid, cid, mid, "rmadmin", int(d[8:]))
                
                offset = update["update_id"] + 1
        elif data.get("error_code") == 409:
            logger.warning("⚠️ Conflict, resetting...")
            session.post(f"{API_URL}/deleteWebhook", json={"drop_pending_updates": True})
            time.sleep(5)
            offset = 0
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        time.sleep(5)

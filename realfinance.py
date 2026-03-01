#!/usr/bin/env python3
import requests
import time
import json
import os
import sys
import random
import string
import threading
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

print = lambda x: (sys.stdout.write(x + "\n"), sys.stdout.flush())[0]

# ==================== CONFIG ====================
BOT_TOKEN = "8720874613:AAFy_qzSTZVR_h8U6oUaFUr-pMy1xAKAXxc"
BOT_USERNAME = "Realfinancepaybot"
API_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
PORT = int(os.environ.get('PORT', 10000))

PAYMENT_CHANNEL = "@beefy_payment"  # قناة نشر طلبات السحب

WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== DATABASE ====================
db = {"users": {}}

try:
    with open("bot_data.json", "r") as f:
        db.update(json.load(f))
except:
    pass

def save():
    with open("bot_data.json", "w") as f:
        json.dump(db, f)

def get_user(uid):
    uid = str(uid)
    if uid not in db["users"]:
        chars = string.ascii_uppercase + string.digits
        db["users"][uid] = {
            "id": uid,
            "username": "",
            "first_name": "",
            "joined_at": time.time(),
            "balance": 0,
            "total_earned": 0,
            "total_withdrawn": 0,
            "referral_code": ''.join(random.choices(chars, k=8)),
            "referred_by": None,
            "referrals_count": 0,
            "referral_clicks": 0,
            "verified": False,
            "wallet": None,
        }
        save()
    return db["users"][uid]

def update_user(uid, **kwargs):
    if uid in db["users"]:
        db["users"][uid].update(kwargs)
        save()

def get_user_by_code(code):
    for u in db["users"].values():
        if u.get("referral_code") == code:
            return u
    return None

def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
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
    if user.get("wallet"):
        kb = [
            [{"text": "💰 Balance", "callback_data": "bal"},
             {"text": "🔗 Referral", "callback_data": "ref"}],
            [{"text": "📊 Stats", "callback_data": "stats"},
             {"text": "💸 Withdraw", "callback_data": "wd"}]
        ]
    else:
        kb = [
            [{"text": "💰 Balance", "callback_data": "bal"},
             {"text": "🔗 Referral", "callback_data": "ref"}],
            [{"text": "📊 Stats", "callback_data": "stats"},
             {"text": "👛 Wallet", "callback_data": "wallet"}]
        ]
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 Back", "callback_data": "back"}]]}

# ==================== TELEGRAM ====================
def send(chat_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except: pass

def edit(chat_id, msg_id, text, kb=None):
    try:
        requests.post(f"{API_URL}/editMessageText", json={
            "chat_id": chat_id,
            "message_id": msg_id,
            "text": text,
            "parse_mode": "Markdown",
            "reply_markup": kb
        }, timeout=10)
    except: pass

def answer(cb_id):
    try:
        requests.post(f"{API_URL}/answerCallbackQuery", json={
            "callback_query_id": cb_id
        }, timeout=5)
    except: pass

def get_member(chat_id, user_id):
    try:
        r = requests.get(f"{API_URL}/getChatMember", params={
            "chat_id": chat_id,
            "user_id": user_id
        }, timeout=5)
        return r.json().get("result", {}).get("status")
    except: return None

def post_to_channel(text):
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": PAYMENT_CHANNEL,
            "text": text,
            "parse_mode": "Markdown"
        }, timeout=10)
    except: pass

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 Web on {PORT}")

# ==================== HANDLERS ====================
states = {}

def handle_start(msg):
    cid = msg["chat"]["id"]
    user = msg["from"]
    uid = user["id"]
    text = msg.get("text", "")
    
    print(f"▶️ Start: {uid}")
    
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
        send(cid, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    ch_txt = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    send(cid,
        f"🎉 *Welcome!*\n💰 Welcome: {format_refi(WELCOME_BONUS)}\n👥 Referral: {format_refi(REFERRAL_BONUS)}/friend\n📢 Join:\n{ch_txt}",
        channels_kb())

def handle_verify(cb, uid, cid, mid):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_member(ch["username"], uid)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        edit(cid, mid, "❌ *Not joined:*\n" + "\n".join([f"• {ch}" for ch in not_joined]), channels_kb())
        return
    
    u = get_user(uid)
    if u.get("verified"):
        edit(cid, mid, f"✅ Already verified!\n{format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    new_bal = u.get("balance",0) + WELCOME_BONUS
    update_user(uid, verified=True, balance=new_bal,
                total_earned=u.get("total_earned",0)+WELCOME_BONUS)
    
    ref_by = u.get("referred_by")
    if ref_by:
        ref = get_user(int(ref_by))
        if ref:
            ref["balance"] = ref.get("balance",0) + REFERRAL_BONUS
            ref["total_earned"] = ref.get("total_earned",0) + REFERRAL_BONUS
            ref["referrals_count"] = ref.get("referrals_count",0) + 1
            update_user(int(ref_by), balance=ref["balance"], total_earned=ref["total_earned"],
                       referrals_count=ref["referrals_count"])
            send(int(ref_by), f"🎉 Friend joined! You earned {format_refi(REFERRAL_BONUS)}")
    
    edit(cid, mid, f"✅ *Verified!*\n✨ +{format_refi(WELCOME_BONUS)}\n💰 {format_refi(new_bal)}", main_kb(u))
    print(f"✅ User {uid} verified")

def handle_bal(cb, uid, cid, mid):
    u = get_user(uid)
    edit(cid, mid,
        f"💰 *Balance*\n• {format_refi(u.get('balance',0))}\n• Total: {format_refi(u.get('total_earned',0))}\n• Referrals: {u.get('referrals_count',0)}",
        back_kb())

def handle_ref(cb, uid, cid, mid):
    u = get_user(uid)
    link = f"https://t.me/{BOT_USERNAME}?start={u.get('referral_code','')}"
    earned = u.get('referrals_count',0) * REFERRAL_BONUS
    edit(cid, mid,
        f"🔗 *Your Link*\n`{link}`\n\n• You earn: {format_refi(REFERRAL_BONUS)}/friend\n• Clicks: {u.get('referral_clicks',0)}\n• Earned: {format_refi(earned)}",
        back_kb())

def handle_stats(cb, uid, cid, mid):
    u = get_user(uid)
    edit(cid, mid,
        f"📊 *Stats*\n• ID: `{uid}`\n• Balance: {format_refi(u.get('balance',0))}\n• Referrals: {u.get('referrals_count',0)}\n• Verified: {'✅' if u.get('verified') else '❌'}\n• Wallet: {short_wallet(u.get('wallet',''))}",
        back_kb())

def handle_wd(cb, uid, cid, mid):
    u = get_user(uid)
    if not u.get("verified"):
        edit(cid, mid, "❌ Verify first!", back_kb())
        return
    if not u.get("wallet"):
        edit(cid, mid, "⚠️ Set wallet first!", main_kb(u))
        return
    bal = u.get("balance",0)
    if bal < MIN_WITHDRAW:
        edit(cid, mid,
            f"⚠️ *Insufficient Balance*\nMin: {format_refi(MIN_WITHDRAW)}\nYour: {format_refi(bal)}",
            back_kb())
        return
    edit(cid, mid,
        f"💸 *Withdraw*\nBalance: {format_refi(bal)}\nMin: {format_refi(MIN_WITHDRAW)}\nWallet: {short_wallet(u['wallet'])}\n\nSend amount:")
    states[uid] = "wd"

def handle_wallet(cb, uid, cid, mid):
    u = get_user(uid)
    cur = u.get("wallet","Not set")
    if cur != "Not set":
        cur = short_wallet(cur)
    edit(cid, mid, f"👛 *Set Wallet*\nCurrent: {cur}\n\nSend ETH address (0x...):")
    states[uid] = "wallet"

def handle_back(cb, uid, cid, mid):
    u = get_user(uid)
    edit(cid, mid, f"🎯 *Menu*\n💰 {format_refi(u.get('balance',0))}", main_kb(u))

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(txt, uid, cid):
    if is_valid_wallet(txt):
        update_user(uid, wallet=txt)
        u = get_user(uid)
        send(cid, f"✅ *Wallet saved!*\n{short_wallet(txt)}", main_kb(u))
        print(f"👛 Wallet set for {uid}")
    else:
        send(cid, "❌ Invalid wallet! Must be 0x + 40 chars")

def handle_withdraw_input(txt, uid, cid):
    try:
        amt = int(txt.replace(",",""))
    except:
        send(cid, "❌ Invalid number")
        return
    u = get_user(uid)
    if amt < MIN_WITHDRAW:
        send(cid, f"❌ Min is {format_refi(MIN_WITHDRAW)}")
    elif amt > u.get("balance",0):
        send(cid, f"❌ Insufficient balance")
    else:
        update_user(uid, balance=u["balance"] - amt, total_withdrawn=u.get("total_withdrawn",0)+amt)
        
        channel_msg = (
            f"💰 *طلب سحب جديد*\n\n"
            f"👤 *المستخدم:* {u.get('first_name', 'Unknown')}\n"
            f"📱 *اليوزر:* @{u.get('username', 'None')}\n"
            f"🆔 *المعرف:* `{uid}`\n"
            f"📊 *الإحالات:* {u.get('referrals_count', 0)}\n"
            f"💵 *المبلغ:* {format_refi(amt)}\n"
            f"📮 *المحفظة:* `{u['wallet']}`\n"
            f"⏱️ *الوقت:* {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        post_to_channel(channel_msg)
        
        send(cid, f"✅ *Withdrawal request sent!*", main_kb(u))
        print(f"💰 Withdrawal: {uid} requested {amt} REFi")

# ==================== MAIN LOOP ====================
print("🚀 Starting bot...")
offset = 0

while True:
    try:
        r = requests.post(f"{API_URL}/getUpdates", json={
            "offset": offset,
            "timeout": 30,
            "allowed_updates": ["message", "callback_query"]
        }, timeout=35)
        data = r.json()
        
        if data.get("ok"):
            for upd in data.get("result", []):
                if "message" in upd:
                    msg = upd["message"]
                    cid = msg["chat"]["id"]
                    uid = msg["from"]["id"]
                    txt = msg.get("text", "")
                    
                    print(f"📩 Message from {uid}: {txt}")
                    
                    if txt == "/start":
                        handle_start(msg)
                    else:
                        state = states.get(uid)
                        if state == "wallet":
                            handle_wallet_input(txt, uid, cid)
                            states.pop(uid, None)
                        elif state == "wd":
                            handle_withdraw_input(txt, uid, cid)
                            states.pop(uid, None)
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    d = cb.get("data", "")
                    uid = cb["from"]["id"]
                    cid = cb["message"]["chat"]["id"]
                    mid = cb["message"]["message_id"]
                    
                    answer(cb["id"])
                    
                    if d == "verify": handle_verify(cb, uid, cid, mid)
                    elif d == "bal": handle_bal(cb, uid, cid, mid)
                    elif d == "ref": handle_ref(cb, uid, cid, mid)
                    elif d == "stats": handle_stats(cb, uid, cid, mid)
                    elif d == "wd": handle_wd(cb, uid, cid, mid)
                    elif d == "wallet": handle_wallet(cb, uid, cid, mid)
                    elif d == "back": handle_back(cb, uid, cid, mid)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"❌ Error: {e}")
        time.sleep(5)

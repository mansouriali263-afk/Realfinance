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

# قناة نشر طلبات السحب
PAYMENT_CHANNEL = "@beefy_payment"

# المعرفات المسموح لها بلوحة المشرف
ADMIN_IDS = [1653918641]
ADMIN_PASSWORD = "Ali97$"

# المكافآت
WELCOME_BONUS = 1_000_000
REFERRAL_BONUS = 1_000_000
MIN_WITHDRAW = 5_000_000
REFI_PER_MILLION = 2.0

# القنوات المطلوبة
REQUIRED_CHANNELS = [
    {"name": "REFi Distribution", "username": "@Realfinance_REFI", "link": "https://t.me/Realfinance_REFI"},
    {"name": "Airdrop Master VIP", "username": "@Airdrop_MasterVIP", "link": "https://t.me/Airdrop_MasterVIP"},
    {"name": "Daily Airdrop", "username": "@Daily_AirdropX", "link": "https://t.me/Daily_AirdropX"}
]

# ==================== DATABASE ====================
db = {"users": {}, "stats": {"total_users": 0, "total_withdrawn": 0, "start_time": time.time()}}

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
        db["stats"]["total_users"] = len(db["users"])
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

def get_user_by_username(username):
    username = username.lower().lstrip('@')
    for u in db["users"].values():
        if u.get("username", "").lower() == username:
            return u
    return None

def format_refi(refi):
    usd = (refi / 1_000_000) * REFI_PER_MILLION
    return f"{refi:,} REFi (~${usd:.2f})"

def short_wallet(w):
    return f"{w[:6]}...{w[-4:]}" if w and len(w) > 10 else "غير مضبوط"

def is_valid_wallet(w):
    return w and w.startswith('0x') and len(w) == 42

def get_stats():
    users = db["users"].values()
    now = time.time()
    return {
        "total_users": len(users),
        "verified": sum(1 for u in users if u.get("verified")),
        "total_balance": sum(u.get("balance", 0) for u in users),
        "total_withdrawn": db["stats"].get("total_withdrawn", 0),
        "uptime": int(now - db["stats"].get("start_time", now))
    }

# ==================== KEYBOARDS ====================
def channels_kb():
    kb = []
    for ch in REQUIRED_CHANNELS:
        kb.append([{"text": f"📢 انضم إلى {ch['name']}", "url": ch["link"]}])
    kb.append([{"text": "✅ تحقق من الاشتراك", "callback_data": "verify"}])
    return {"inline_keyboard": kb}

def main_kb(user):
    # الصف الأول: الرصيد والإحالة
    row1 = [{"text": "💰 الرصيد", "callback_data": "bal"},
            {"text": "🔗 رابط الإحالة", "callback_data": "ref"}]
    
    # الصف الثاني: الإحصائيات والمحفظة/السحب
    if user.get("wallet"):
        row2 = [{"text": "📊 إحصائياتي", "callback_data": "stats"},
                {"text": "💸 سحب", "callback_data": "wd"}]
    else:
        row2 = [{"text": "📊 إحصائياتي", "callback_data": "stats"},
                {"text": "👛 إضافة محفظة", "callback_data": "wallet"}]
    
    kb = [row1, row2]
    
    # زر المشرف (للمسؤولين فقط)
    if int(user["id"]) in ADMIN_IDS:
        kb.append([{"text": "👑 لوحة المشرف", "callback_data": "admin"}])
    
    return {"inline_keyboard": kb}

def back_kb():
    return {"inline_keyboard": [[{"text": "🔙 العودة", "callback_data": "back"}]]}

def admin_kb():
    return {"inline_keyboard": [
        [{"text": "📊 إحصائيات", "callback_data": "admin_stats"}],
        [{"text": "📢 بث رسالة", "callback_data": "admin_broadcast"}],
        [{"text": "🔒 تسجيل الخروج", "callback_data": "admin_logout"}]
    ]}

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

def broadcast_to_all(message):
    """إرسال رسالة لجميع المستخدمين"""
    sent = 0
    failed = 0
    for uid in db["users"].keys():
        try:
            send(int(uid), message)
            sent += 1
            if sent % 10 == 0:  # نتجنب الـ flood
                time.sleep(1)
        except:
            failed += 1
    return sent, failed

# ==================== WEB SERVER ====================
class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")
    def log_message(self, *args): pass

threading.Thread(target=lambda: HTTPServer(('0.0.0.0', PORT), HealthHandler).serve_forever(), daemon=True).start()
print(f"🌐 واجهة المراقبة على منفذ {PORT}")

# ==================== HANDLERS ====================
states = {}

def handle_start(msg):
    cid = msg["chat"]["id"]
    user = msg["from"]
    uid = user["id"]
    text = msg.get("text", "")
    
    print(f"▶️ بدء مستخدم جديد: {uid}")
    
    # التحقق من وجود كود إحالة
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
        welcome_text = (
            f"🎯 *مرحباً بعودتك يا {u.get('first_name', 'صديقي')}!*\n\n"
            f"💰 رصيدك الحالي: {format_refi(u.get('balance', 0))}\n"
            f"👥 عدد إحالاتك: {u.get('referrals_count', 0)}"
        )
        send(cid, welcome_text, main_kb(u))
        return
    
    # رسالة ترحيب للمستخدم الجديد
    channels_text = "\n".join([f"• {ch['name']}" for ch in REQUIRED_CHANNELS])
    welcome_text = (
        f"🎉 *أهلاً بك في بوت {BOT_USERNAME}!*\n\n"
        f"💰 مكافأة الترحيب: {format_refi(WELCOME_BONUS)}\n"
        f"👥 مكافأة الإحالة: {format_refi(REFERRAL_BONUS)} عن كل صديق\n\n"
        f"📢 للبدء، يجب الاشتراك في هذه القنوات أولاً:\n{channels_text}\n\n"
        f"👇 بعد الاشتراك، اضغط على زر التحقق"
    )
    send(cid, welcome_text, channels_kb())

def handle_verify(cb, uid, cid, mid):
    not_joined = []
    for ch in REQUIRED_CHANNELS:
        status = get_member(ch["username"], uid)
        if status not in ["member", "administrator", "creator"]:
            not_joined.append(ch["name"])
    
    if not_joined:
        error_text = "❌ *لم تشترك في القنوات التالية:*\n" + "\n".join([f"• {ch}" for ch in not_joined])
        edit(cid, mid, error_text, channels_kb())
        return
    
    u = get_user(uid)
    if u.get("verified"):
        edit(cid, mid, f"✅ لقد تم تحققك مسبقاً!\n{format_refi(u.get('balance',0))}", main_kb(u))
        return
    
    # إضافة مكافأة الترحيب
    new_bal = u.get("balance",0) + WELCOME_BONUS
    update_user(uid, verified=True, balance=new_bal, total_earned=u.get("total_earned",0)+WELCOME_BONUS)
    
    # معالجة الإحالة إذا وجدت
    ref_by = u.get("referred_by")
    if ref_by:
        ref = get_user(int(ref_by))
        if ref:
            ref["balance"] = ref.get("balance",0) + REFERRAL_BONUS
            ref["total_earned"] = ref.get("total_earned",0) + REFERRAL_BONUS
            ref["referrals_count"] = ref.get("referrals_count",0) + 1
            update_user(int(ref_by), balance=ref["balance"], total_earned=ref["total_earned"],
                       referrals_count=ref["referrals_count"])
            send(int(ref_by), f"🎉 *مبروك!*\nصديقك {u.get('first_name', 'أحد الأصدقاء')} انضم عبر رابطك!\n✨ ربحت {format_refi(REFERRAL_BONUS)}")
    
    success_text = (
        f"✅ *تم التحقق بنجاح!*\n\n"
        f"✨ أضفنا {format_refi(WELCOME_BONUS)} إلى رصيدك\n"
        f"💰 رصيدك الحالي: {format_refi(new_bal)}\n\n"
        f"👥 شارك رابطك مع أصدقائك واربح {format_refi(REFERRAL_BONUS)} عن كل صديق!"
    )
    edit(cid, mid, success_text, main_kb(u))
    print(f"✅ مستخدم {uid} تم تحقيقه بنجاح")

def handle_bal(cb, uid, cid, mid):
    u = get_user(uid)
    text = (
        f"💰 *رصيدك الحالي*\n\n"
        f"• الرصيد: {format_refi(u.get('balance', 0))}\n"
        f"• إجمالي الأرباح: {format_refi(u.get('total_earned', 0))}\n"
        f"• إجمالي المسحوبات: {format_refi(u.get('total_withdrawn', 0))}\n"
        f"• عدد إحالاتك: {u.get('referrals_count', 0)}"
    )
    edit(cid, mid, text, back_kb())

def handle_ref(cb, uid, cid, mid):
    u = get_user(uid)
    link = f"https://t.me/{BOT_USERNAME}?start={u.get('referral_code','')}"
    earned = u.get('referrals_count', 0) * REFERRAL_BONUS
    
    text = (
        f"🔗 *رابط الإحالة الخاص بك*\n\n"
        f"`{link}`\n\n"
        f"• تكسب {format_refi(REFERRAL_BONUS)} عن كل صديق\n"
        f"• عدد النقرات على رابطك: {u.get('referral_clicks', 0)}\n"
        f"• أرباحك من الإحالات: {format_refi(earned)}"
    )
    edit(cid, mid, text, back_kb())

def handle_stats(cb, uid, cid, mid):
    u = get_user(uid)
    joined = datetime.fromtimestamp(u.get("joined_at", 0)).strftime('%Y-%m-%d')
    
    text = (
        f"📊 *إحصائياتك الشخصية*\n\n"
        f"• معرفك: `{uid}`\n"
        f"• تاريخ الانضمام: {joined}\n"
        f"• الرصيد: {format_refi(u.get('balance', 0))}\n"
        f"• إجمالي الأرباح: {format_refi(u.get('total_earned', 0))}\n"
        f"• إجمالي المسحوبات: {format_refi(u.get('total_withdrawn', 0))}\n"
        f"• عدد الإحالات: {u.get('referrals_count', 0)}\n"
        f"• تم التحقق: {'✅' if u.get('verified') else '❌'}\n"
        f"• المحفظة: {short_wallet(u.get('wallet', ''))}"
    )
    edit(cid, mid, text, back_kb())

def handle_wd(cb, uid, cid, mid):
    u = get_user(uid)
    
    if not u.get("verified"):
        edit(cid, mid, "❌ *عذراً*، يجب التحقق من القنوات أولاً!", back_kb())
        return
    
    if not u.get("wallet"):
        edit(cid, mid, "⚠️ *يجب إضافة محفظة أولاً*\n\nاستخدم زر 'إضافة محفظة' من القائمة الرئيسية.", main_kb(u))
        return
    
    bal = u.get("balance", 0)
    if bal < MIN_WITHDRAW:
        needed = MIN_WITHDRAW - bal
        edit(cid, mid,
            f"⚠️ *الرصيد غير كافٍ للسحب*\n\n"
            f"الحد الأدنى: {format_refi(MIN_WITHDRAW)}\n"
            f"رصيدك الحالي: {format_refi(bal)}\n\n"
            f"تحتاج {format_refi(needed)} إضافية للسحب.\n"
            f"👥 ادعُ المزيد من الأصدقاء لزيادة رصيدك!",
            back_kb())
        return
    
    edit(cid, mid,
        f"💸 *طلب سحب*\n\n"
        f"رصيدك الحالي: {format_refi(bal)}\n"
        f"الحد الأدنى: {format_refi(MIN_WITHDRAW)}\n"
        f"محفظتك: `{short_wallet(u['wallet'])}`\n\n"
        f"📝 أرسل المبلغ الذي تريد سحبه:",
        back_kb())
    states[uid] = "wd"

def handle_wallet(cb, uid, cid, mid):
    u = get_user(uid)
    cur = u.get("wallet", "غير مضبوطة")
    if cur != "غير مضبوطة":
        cur = short_wallet(cur)
    
    text = (
        f"👛 *إضافة محفظة سحب*\n\n"
        f"محفظتك الحالية: {cur}\n\n"
        f"📝 أرسل عنوان محفظتك (Ethereum).\n"
        f"يجب أن يبدأ بـ `0x` وأن يكون بطول 42 رمزاً.\n\n"
        f"مثال:\n"
        f"`0x742d35Cc6634C0532925a3b844Bc454e4438f44e`"
    )
    edit(cid, mid, text)
    states[uid] = "wallet"

def handle_back(cb, uid, cid, mid):
    u = get_user(uid)
    text = f"🎯 *القائمة الرئيسية*\n\n💰 رصيدك: {format_refi(u.get('balance', 0))}"
    edit(cid, mid, text, main_kb(u))

# ==================== ADMIN HANDLERS ====================
def handle_admin(cb, uid, cid, mid):
    if uid not in ADMIN_IDS:
        answer(cb["id"])
        return
    
    # نتحقق إذا كان مسجل الدخول
    if states.get(f"admin_logged_{uid}"):
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *لوحة المشرف*\n\n"
            f"📊 *إحصائيات عامة*\n"
            f"• المستخدمين: {stats['total_users']}\n"
            f"• الموثقين: {stats['verified']}\n"
            f"• إجمالي الأرصدة: {format_refi(stats['total_balance'])}\n"
            f"• إجمالي المسحوبات: {format_refi(stats['total_withdrawn'])}\n"
            f"• مدة التشغيل: {hours} ساعة {minutes} دقيقة"
        )
        edit(cid, mid, text, admin_kb())
    else:
        edit(cid, mid, "🔐 *دخول المشرف*\n\nالرجاء إدخال كلمة السر:", back_kb())
        states[uid] = "admin_login"

def handle_admin_login_input(txt, uid, cid):
    if txt == ADMIN_PASSWORD:
        states[f"admin_logged_{uid}"] = True
        stats = get_stats()
        hours = stats['uptime'] // 3600
        minutes = (stats['uptime'] % 3600) // 60
        text = (
            f"👑 *لوحة المشرف*\n\n"
            f"📊 *إحصائيات عامة*\n"
            f"• المستخدمين: {stats['total_users']}\n"
            f"• الموثقين: {stats['verified']}\n"
            f"• إجمالي الأرصدة: {format_refi(stats['total_balance'])}\n"
            f"• إجمالي المسحوبات: {format_refi(stats['total_withdrawn'])}\n"
            f"• مدة التشغيل: {hours} ساعة {minutes} دقيقة"
        )
        send(cid, text, admin_kb())
    else:
        send(cid, "❌ كلمة سر خاطئة!")
    states.pop(uid, None)

def handle_admin_stats(cb, cid, mid):
    stats = get_stats()
    hours = stats['uptime'] // 3600
    minutes = (stats['uptime'] % 3600) // 60
    text = (
        f"📊 *إحصائيات تفصيلية*\n\n"
        f"👥 *المستخدمين*\n"
        f"• الإجمالي: {stats['total_users']}\n"
        f"• الموثقين: {stats['verified']}\n\n"
        f"💰 *الأرصدة*\n"
        f"• إجمالي الأرصدة: {format_refi(stats['total_balance'])}\n"
        f"• إجمالي المسحوبات: {format_refi(stats['total_withdrawn'])}\n\n"
        f"⏱️ *مدة التشغيل: {hours} ساعة {minutes} دقيقة*"
    )
    edit(cid, mid, text, admin_kb())

def handle_admin_broadcast(cb, cid, mid):
    edit(cid, mid, "📢 *بث رسالة*\n\nأرسل الرسالة التي تريد بثها لجميع المستخدمين:", back_kb())
    states[cb["from"]["id"]] = "admin_broadcast"

def handle_admin_broadcast_input(txt, uid, cid):
    send(cid, f"📢 جاري بث الرسالة إلى {len(db['users'])} مستخدم...")
    sent, failed = broadcast_to_all(txt)
    send(cid, f"✅ *تم البث*\n\nتم الإرسال: {sent}\nفشل: {failed}", admin_kb())
    states.pop(uid, None)

def handle_admin_logout(cb, uid, cid, mid):
    states.pop(f"admin_logged_{uid}", None)
    u = get_user(uid)
    send(cid, f"🔒 تم تسجيل الخروج\n\n💰 رصيدك: {format_refi(u.get('balance',0))}", main_kb(u))

# ==================== INPUT HANDLERS ====================
def handle_wallet_input(txt, uid, cid):
    if is_valid_wallet(txt):
        update_user(uid, wallet=txt)
        u = get_user(uid)
        send(cid, f"✅ *تم حفظ المحفظة بنجاح!*\n\n{short_wallet(txt)}", main_kb(u))
        print(f"👛 مستخدم {uid} أضاف محفظة")
    else:
        send(cid, "❌ *عنوان محفظة غير صالح!*\n\nيجب أن يبدأ بـ `0x` وأن يكون بطول 42 رمزاً.")

def handle_withdraw_input(txt, uid, cid):
    try:
        amt = int(txt.replace(",","").strip())
    except:
        send(cid, "❌ *رقم غير صالح*\n\nالرجاء إدخال رقم صحيح.")
        return
    
    u = get_user(uid)
    
    if amt < MIN_WITHDRAW:
        send(cid, f"❌ *المبلغ أقل من الحد الأدنى*\n\nالحد الأدنى: {format_refi(MIN_WITHDRAW)}")
        return
    
    if amt > u.get("balance", 0):
        send(cid, f"❌ *رصيد غير كاف*\n\nرصيدك الحالي: {format_refi(u.get('balance', 0))}")
        return
    
    # خصم الرصيد وتسجيل السحب
    new_balance = u["balance"] - amt
    new_withdrawn = u.get("total_withdrawn", 0) + amt
    update_user(uid, balance=new_balance, total_withdrawn=new_withdrawn)
    db["stats"]["total_withdrawn"] = db["stats"].get("total_withdrawn", 0) + amt
    save()
    
    # تحضير رسالة النشر في القناة
    channel_msg = (
        f"💰 *طلب سحب جديد*\n\n"
        f"👤 *المستخدم:* {u.get('first_name', 'غير معروف')}\n"
        f"📱 *اليوزر:* @{u.get('username', 'لا يوجد')}\n"
        f"🆔 *المعرف:* `{uid}`\n"
        f"📊 *عدد الإحالات:* {u.get('referrals_count', 0)}\n"
        f"💵 *المبلغ:* {format_refi(amt)}\n"
        f"📮 *المحفظة:* `{u['wallet']}`\n"
        f"⏱️ *الوقت:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    post_to_channel(channel_msg)
    
    # إشعار المستخدم
    send(cid, f"✅ *تم تقديم طلب السحب بنجاح!*\n\nالمبلغ: {format_refi(amt)}\nسيتم مراجعة طلبك قريباً.", main_kb(u))
    print(f"💰 مستخدم {uid} طلب سحب {amt} REFi")

# ==================== MAIN LOOP ====================
print("🚀 بدء تشغيل البوت...")
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
                    
                    print(f"📩 رسالة من {uid}: {txt[:50]}...")
                    
                    if txt == "/start":
                        handle_start(msg)
                    else:
                        # معالجة حالات الإدخال
                        if states.get(uid) == "wallet":
                            handle_wallet_input(txt, uid, cid)
                            states.pop(uid, None)
                        elif states.get(uid) == "wd":
                            handle_withdraw_input(txt, uid, cid)
                            states.pop(uid, None)
                        elif states.get(uid) == "admin_login":
                            handle_admin_login_input(txt, uid, cid)
                        elif states.get(uid) == "admin_broadcast":
                            handle_admin_broadcast_input(txt, uid, cid)
                        else:
                            send(cid, "❌ أمر غير معروف. استخدم /start للبدء.")
                
                elif "callback_query" in upd:
                    cb = upd["callback_query"]
                    d = cb.get("data", "")
                    uid = cb["from"]["id"]
                    cid = cb["message"]["chat"]["id"]
                    mid = cb["message"]["message_id"]
                    
                    answer(cb["id"])
                    
                    # معالجة الأزرار
                    if d == "verify": handle_verify(cb, uid, cid, mid)
                    elif d == "bal": handle_bal(cb, uid, cid, mid)
                    elif d == "ref": handle_ref(cb, uid, cid, mid)
                    elif d == "stats": handle_stats(cb, uid, cid, mid)
                    elif d == "wd": handle_wd(cb, uid, cid, mid)
                    elif d == "wallet": handle_wallet(cb, uid, cid, mid)
                    elif d == "back": handle_back(cb, uid, cid, mid)
                    elif d == "admin": handle_admin(cb, uid, cid, mid)
                    elif d == "admin_stats": handle_admin_stats(cb, cid, mid)
                    elif d == "admin_broadcast": handle_admin_broadcast(cb, cid, mid)
                    elif d == "admin_logout": handle_admin_logout(cb, uid, cid, mid)
                
                offset = upd["update_id"] + 1
    except Exception as e:
        print(f"❌ خطأ: {e}")
        time.sleep(5)

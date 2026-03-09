// ==================== REFi BOT - ULTIMATE FINAL VERSION WITH CACHE ====================
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const express = require('express');
const https = require('https');
const app = express();
const PORT = process.env.PORT || 10000;

// ==================== CONFIG ====================
const token = process.env.BOT_TOKEN;  // هذا السطر فقط
const botUsername = 'RealnetworkPaybot';
// متغير لتخزين معلومات البوت
let botMe = null;

// تكوين البوت مع إعدادات متقدمة
const bot = new TelegramBot(token, { 
    polling: {
        interval: 300,
        autoStart: true,
        params: {
            timeout: 30
        }
    }
});

// إصلاح مشكلة 409 Conflict
bot.deleteWebHook().then(() => {
    console.log('✅ Webhook deleted');
    return bot.getUpdates({ offset: -1 });
}).then(() => {
    console.log('✅ Cleared all updates');
}).catch(err => {
    console.log('⚠️ Cleanup error:', err.message);
});

// اختبار التوكن وتخزين معلومات البوت
bot.getMe().then(me => {
    botMe = me;
    console.log(`✅ Bot connected: @${me.username} (ID: ${me.id})`);
}).catch(err => {
    console.log('❌ Token error:', err.message);
    process.exit(1);
});

// ==================== CONSTANTS ====================
const WELCOME_BONUS = 500_000;
const REFERRAL_BONUS = 500_000;
const MIN_WITHDRAW = 5_000_000;
const ADMIN_IDS = [1653918641];
const ADMIN_PASSWORD = 'Ali97$';
const PAYMENT_GROUP = -1002166185833;  // مجموعة المدفوعات (المشرفين)

// القنوات المطلوبة
const REQUIRED_CHANNELS = [
    { name: 'REFi Network update', username: '@Realfinance_REFI' },
    { name: 'Group Distribution', username: '@REFI_Group' },
    { name: 'Airdrop Master VIP', username: '@Airdrop_MasterVIP' },
    { name: 'Daily Airdrop', username: '@Daily_AirdropX' }
];

// حساب تويتر (اختياري)
const TWITTER_ACCOUNT = {
    name: 'Daily Airdrop on X',
    username: '@Daily_AirdropX',
    url: 'https://x.com/Daily_AirdropX'
};

// ==================== PROFESSIONAL CACHE SYSTEM ====================
class CacheSystem {
    constructor() {
        this.cache = new Map();              // { userId: userData }
        this.lastAccess = new Map();         // { userId: timestamp }
        this.maxCacheSize = 1000;            // حد أقصى 1000 مستخدم في الذاكرة
        this.cacheTTL = 30 * 60 * 1000;       // 30 دقيقة كحد أقصى في الكاش
        this.hits = 0;
        this.misses = 0;
        this.evictions = 0;
    }

    // إضافة مستخدم للكاش
    set(userId, userData) {
        const uid = String(userId);
        
        // إذا كان الكاش ممتلئ، نحذف الأقدم
        if (this.cache.size >= this.maxCacheSize) {
            this.evictOldest();
        }
        
        this.cache.set(uid, { ...userData });  // نسخة عميقة بسيطة
        this.lastAccess.set(uid, Date.now());
    }

    // جلب مستخدم من الكاش
    get(userId) {
        const uid = String(userId);
        const cached = this.cache.get(uid);
        
        if (cached) {
            // تحديث وقت آخر وصول
            this.lastAccess.set(uid, Date.now());
            this.hits++;
            return { ...cached };  // نسخة لمنع التعديل المباشر
        }
        
        this.misses++;
        return null;
    }

    // تحديث مستخدم في الكاش
    update(userId, updates) {
        const uid = String(userId);
        const cached = this.cache.get(uid);
        
        if (cached) {
            // دمج التحديثات مع البيانات الموجودة
            Object.assign(cached, updates);
            this.lastAccess.set(uid, Date.now());
            return true;
        }
        
        return false;
    }

    // حذف مستخدم من الكاش
    delete(userId) {
        const uid = String(userId);
        this.cache.delete(uid);
        this.lastAccess.delete(uid);
    }

    // حذف الأقدم من الكاش
    evictOldest() {
        let oldestId = null;
        let oldestTime = Infinity;
        
        for (const [id, time] of this.lastAccess.entries()) {
            if (time < oldestTime) {
                oldestTime = time;
                oldestId = id;
            }
        }
        
        if (oldestId) {
            this.cache.delete(oldestId);
            this.lastAccess.delete(oldestId);
            this.evictions++;
            console.log(`🧹 Cache eviction: User ${oldestId} removed (oldest)`);
        }
    }

    // تنظيف الكاش منتهي الصلاحية
    cleanExpired() {
        const now = Date.now();
        let expiredCount = 0;
        
        for (const [id, time] of this.lastAccess.entries()) {
            if (now - time > this.cacheTTL) {
                this.cache.delete(id);
                this.lastAccess.delete(id);
                expiredCount++;
            }
        }
        
        if (expiredCount > 0) {
            console.log(`🧹 Cache cleaned: ${expiredCount} expired users removed`);
        }
    }

    // إحصائيات الكاش
    getStats() {
        return {
            size: this.cache.size,
            maxSize: this.maxCacheSize,
            hits: this.hits,
            misses: this.misses,
            evictions: this.evictions,
            hitRate: this.hits + this.misses > 0 
                ? (this.hits / (this.hits + this.misses) * 100).toFixed(2) + '%'
                : '0%'
        };
    }

    // هل المستخدم في الكاش؟
    has(userId) {
        return this.cache.has(String(userId));
    }
}

// إنشاء نظام الكاش
const userCache = new CacheSystem();

// تنظيف الكاش كل 10 دقائق
setInterval(() => {
    userCache.cleanExpired();
    const stats = userCache.getStats();
    console.log(`📊 Cache Stats: ${stats.size}/${stats.maxSize} users | Hit rate: ${stats.hitRate} | Evictions: ${stats.evictions}`);
}, 10 * 60 * 1000);

// ==================== DATABASE ====================
let db = { 
    users: {}, 
    withdrawals: {}, 
    admin_sessions: {}, 
    stats: { 
        total_users: 0, 
        total_withdrawn: 0, 
        start_time: Date.now() / 1000 
    } 
};

try {
    db = JSON.parse(fs.readFileSync('bot_data.json'));
    console.log(`✅ Loaded ${Object.keys(db.users).length} users from local file`);
} catch { 
    console.log('⚠️ No existing data, starting fresh'); 
}

function saveDB() { 
    try {
        fs.writeFileSync('bot_data.json', JSON.stringify(db, null, 2));
        console.log('💾 Database saved to local file');
    } catch (error) {
        console.log('❌ Error saving database:', error.message);
    }
}

// ==================== USER FUNCTIONS WITH CACHE ====================
function getUser(userId) {
    const uid = String(userId);
    
    // 1. حاول تجيب من الكاش أولاً
    const cachedUser = userCache.get(uid);
    if (cachedUser) {
        return cachedUser;
    }
    
    // 2. إذا ما في كاش، جيب من قاعدة البيانات
    if (!db.users[uid]) {
        // مستخدم جديد
        db.users[uid] = {
            id: uid,
            username: '',
            first_name: '',
            joined_at: Date.now() / 1000,
            balance: 0,
            total_earned: 0,
            total_withdrawn: 0,
            referred_by: null,
            referrals_count: 0,
            referral_clicks: 0,
            verified: false,
            wallet: null,
            twitter_followed: false,
            pending_state: null
        };
        db.stats.total_users = Object.keys(db.users).length;
        saveDB();
        console.log(`✅ New user created: ${uid}`);
    }
    
    // 3. خزن في الكاش للاستخدام المستقبلي
    userCache.set(uid, db.users[uid]);
    
    return { ...db.users[uid] };  // نسخة لمنع التعديل المباشر
}

function updateUser(userId, updates) {
    const uid = String(userId);
    
    // 1. حدث في قاعدة البيانات
    if (db.users[uid]) {
        db.users[uid] = { ...db.users[uid], ...updates };
        saveDB();
        
        // 2. حدث في الكاش إذا كان موجود
        userCache.update(uid, updates);
        
        console.log(`✅ User ${uid} updated:`, Object.keys(updates));
    }
}

// ==================== WITHDRAWAL FUNCTIONS ====================
function getUserWithdrawals(userId, status = null) {
    try {
        const uid = String(userId);
        if (!db || !db.withdrawals) return [];
        
        let withdrawals = Object.values(db.withdrawals).filter(w => w && w.user_id === uid);
        if (status) {
            withdrawals = withdrawals.filter(w => w && w.status === status);
        }
        return withdrawals.sort((a, b) => (b.created_at || 0) - (a.created_at || 0));
    } catch (error) {
        console.log('❌ Error in getUserWithdrawals:', error.message);
        return [];
    }
}

// ==================== WITHDRAWAL FUNCTION (باستخدام HTML) ====================
async function requestWithdrawal(userId, amount, wallet) {
    const uid = String(userId);
    const user = db.users[uid];
    if (!user) return false;
    
    // خصم الرصيد
    const newBalance = (user.balance || 0) - amount;
    const newWithdrawn = (user.total_withdrawn || 0) + amount;
    
    updateUser(userId, { 
        balance: newBalance, 
        total_withdrawn: newWithdrawn,
        pending_state: null 
    });
    
    // تحديث إحصائيات السحوبات
    db.stats.total_withdrawn = (db.stats.total_withdrawn || 0) + amount;
    saveDB();
    
    // تجهيز معرف الطلب
    const requestId = `WD${Math.floor(Date.now() / 1000)}${uid.slice(-4)}`;
    
    // تجهيز تاريخ الطلب
    const now = new Date();
    const dateStr = now.toLocaleDateString('en-US');
    const timeStr = now.toLocaleTimeString('en-US');
    
    // تجهيز رابط المستخدم
    const userLink = user.username 
        ? `@${user.username}` 
        : `<a href="tg://user?id=${userId}">Click to contact</a>`;
    
    // رسالة المجموعة - باستخدام HTML بدلاً من Markdown
    const groupMessage = 
        `🆕 <b>New Withdrawal Request</b>\n\n` +
        `━━━━━━━━━━━━━━━━━━━━\n\n` +
        `👤 <b>User:</b> ${user.first_name || 'Unknown'}\n` +
        `🆔 <b>User ID:</b> <code>${userId}</code>\n` +
        `📱 <b>Username:</b> ${userLink}\n` +
        `👥 <b>Referrals:</b> ${user.referrals_count || 0}\n` +
        `💰 <b>Amount:</b> ${formatRefi(amount)}\n` +
        `📮 <b>Wallet Address:</b> <code>${wallet}</code>\n\n` +
        `📅 <b>Date:</b> ${dateStr} - ${timeStr}\n` +
        `🆔 <b>Request ID:</b> <code>${requestId}</code>\n\n` +
        `━━━━━━━━━━━━━━━━━━━━\n\n` +
        `🔹 <b>To process:</b> Copy the wallet address above and send payment\n` +
        `🔹 <b>Fast processing:</b> Payment is usually made 1-30 minutes after this message is posted`;
    
    // محاولة إرسال للمجموعة
    try {
        console.log(`📢 Attempting to send to group ${PAYMENT_GROUP}...`);
        
        const sentMessage = await bot.sendMessage(PAYMENT_GROUP, groupMessage, { 
            parse_mode: 'HTML',
            disable_web_page_preview: true
        });
        
        console.log(`✅ Message sent successfully! Message ID: ${sentMessage.message_id}`);
        
        // إرسال تأكيد للمستخدم
        await bot.sendMessage(userId,
            `✅ <b>Withdrawal Request Submitted!</b>\n\n` +
            `💰 Amount: ${formatRefi(amount)}\n` +
            `📮 Wallet: <code>${wallet}</code>\n\n` +
            `Your request has been sent to the admins. You will be notified once processed.`,
            { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
        );
        
        return true;
        
    } catch (error) {
        console.log('❌ FAILED TO SEND TO GROUP!');
        console.log('Error code:', error.code);
        console.log('Error message:', error.message);
        
        // إذا فشل الإرسال، نرجع الرصيد للمستخدم
        console.log('💰 Refunding user...');
        updateUser(userId, { 
            balance: user.balance,
            total_withdrawn: user.total_withdrawn,
            pending_state: 'waiting_amount'
        });
        
        // إرسال رسالة خطأ للمستخدم
        await bot.sendMessage(userId,
            `❌ <b>Error</b>\n\n` +
            `Could not process your request. Please try again later or contact support.`,
            { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
        );
        
        return false;
    }
}

// ==================== ADMIN SESSION ====================
function isAdminLoggedIn(adminId) { 
    if (!ADMIN_IDS.includes(Number(adminId))) return false;
    return (db.admin_sessions[String(adminId)] || 0) > Date.now() / 1000; 
}

function adminLogin(adminId) { 
    if (!ADMIN_IDS.includes(Number(adminId))) return false;
    db.admin_sessions[String(adminId)] = Date.now() / 1000 + 3600; 
    saveDB(); 
    console.log(`🔐 Admin ${adminId} logged in`);
    return true;
}

function adminLogout(adminId) { 
    delete db.admin_sessions[String(adminId)]; 
    saveDB(); 
    console.log(`🔒 Admin ${adminId} logged out`);
}

// ==================== STATS ====================
function getStats() {
    const users = Object.values(db.users);
    const now = Date.now() / 1000;
    return {
        total_users: users.length,
        verified: users.filter(u => u.verified).length,
        total_balance: users.reduce((s, u) => s + (u.balance || 0), 0),
        total_earned: users.reduce((s, u) => s + (u.total_earned || 0), 0),
        total_withdrawn: db.stats.total_withdrawn || 0,
        pending_withdrawals: 0,
        total_referrals: users.reduce((s, u) => s + (u.referrals_count || 0), 0),
        twitter_followers: users.filter(u => u.twitter_followed).length,
        uptime: now - (db.stats.start_time || now)
    };
}

// ==================== FORMATTING (لـ HTML) ====================
function formatRefi(refi) {
    try {
        const amount = Number(refi) || 0;
        const usd = (amount / 1000000) * 2;
        return `${amount.toLocaleString()} REFi (~$${usd.toFixed(2)})`;
    } catch (error) {
        console.log('❌ Error in formatRefi:', error.message);
        return `${refi || 0} REFi`;
    }
}

function shortWallet(w) { 
    if (!w || typeof w !== 'string') return 'Not set';
    if (w.length < 10) return w;
    return `${w.slice(0, 6)}...${w.slice(-4)}`; 
}

function isValidWallet(w) { 
    return w && typeof w === 'string' && w.startsWith('0x') && w.length === 42; 
}

// ==================== CHANNEL CHECK ====================
async function checkChannels(userId) {
    for (const ch of REQUIRED_CHANNELS) {
        try {
            const member = await bot.getChatMember(ch.username, userId);
            if (!['member', 'administrator', 'creator'].includes(member.status)) return false;
        } catch { 
            return false; 
        }
    }
    return true;
}

// ==================== KEYBOARDS ====================
function channelsKeyboard() {
    const keyboard = [];
    REQUIRED_CHANNELS.forEach(ch => {
        keyboard.push([{ 
            text: `📢 Join ${ch.name}`, 
            url: `https://t.me/${ch.username.substring(1)}` 
        }]);
    });
    keyboard.push([{ 
        text: `🐦 Follow on X`, 
        url: TWITTER_ACCOUNT.url 
    }]);
    keyboard.push([{ 
        text: '✅ VERIFY MEMBERSHIP', 
        callback_data: 'verify' 
    }]);
    return { inline_keyboard: keyboard };
}

function bottomReplyKeyboard(userId) {
    const user = db.users[String(userId)] || {};
    
    const row1 = ['💰 Balance', '🔗 Referral', '📊 Stats'];
    const row2 = ['💸 Withdraw'];
    
    const keyboard = [row1, row2];
    
    if (ADMIN_IDS.includes(Number(userId)) && isAdminLoggedIn(Number(userId))) {
        keyboard.push(['👑 Admin Panel']);
    }
    
    return {
        reply_markup: {
            keyboard: keyboard,
            resize_keyboard: true,
            one_time_keyboard: false,
            persistent: true
        }
    };
}

function removeKeyboard() {
    return {
        reply_markup: {
            remove_keyboard: true
        }
    };
}

function adminInlineKeyboard() {
    return {
        inline_keyboard: [
            [{ text: '📊 Statistics', callback_data: 'admin_stats' }],
            [{ text: '📢 Broadcast', callback_data: 'admin_broadcast' }],
            [{ text: '👥 Users List', callback_data: 'admin_users' }],
            [{ text: '🔒 Logout', callback_data: 'admin_logout' }]
        ]
    };
}

// ==================== SMART KEEP ALIVE SYSTEM ====================
class SmartKeepAlive {
    constructor() {
        this.pingCount = 0;
        this.lastActivity = Date.now();
        this.isActive = true;
    }

    start() {
        console.log('🔄 Smart Keep Alive System Started');
        
        // بينغ كل 10 دقائق
        setInterval(() => {
            this.sendPing();
        }, 10 * 60 * 1000);

        // تتبع النشاط
        bot.on('message', () => this.recordActivity());
        bot.on('callback_query', () => this.recordActivity());
    }

    recordActivity() {
        this.lastActivity = Date.now();
        this.isActive = true;
    }

    sendPing() {
        this.pingCount++;
        const url = process.env.RENDER_EXTERNAL_URL || `http://localhost:${PORT}`;
        const time = new Date().toLocaleTimeString();
        
        https.get(`${url}/health`, (res) => {
            console.log(`🏓 Keep-alive ping #${this.pingCount} at ${time} | Status: ${res.statusCode}`);
        }).on('error', (err) => {
            console.log(`⚠️ Ping #${this.pingCount} failed:`, err.message);
        });

        // صحي البوت نفسه
        bot.getMe().then(() => {}).catch(() => {});
    }
}

// شغل نظام البقاء
const keepAlive = new SmartKeepAlive();
keepAlive.start();

// ==================== MAIN HANDLER - /start ====================
bot.onText(/\/start(?:\s+(.+))?/, async (msg, match) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const username = msg.from.username || '';
    const firstName = msg.from.first_name || '';
    const referrerId = match[1] ? parseInt(match[1]) : null;
    
    console.log(`\n▶️ START: User ${userId}`);
    
    let user = getUser(userId);
    updateUser(userId, { username, first_name: firstName });
    
    if (referrerId && referrerId !== userId && !user.referred_by) {
        console.log(`🔍 Referral from: ${referrerId}`);
        updateUser(userId, { referred_by: referrerId });
        
        const referrer = db.users[String(referrerId)];
        if (referrer) {
            updateUser(referrerId, { referral_clicks: (referrer.referral_clicks || 0) + 1 });
            try {
                await bot.sendMessage(referrerId, 
                    `👋 <b>Someone clicked your referral link!</b>\n\nThey'll get ${formatRefi(REFERRAL_BONUS)} when they verify.`,
                    { parse_mode: 'HTML' }
                );
            } catch (e) {}
        }
    }
    
    if (user.verified) {
        await bot.sendMessage(chatId, 
            `🎯 <b>Welcome Back!</b>\n\n💰 Balance: ${formatRefi(user.balance)}`,
            { 
                parse_mode: 'HTML', 
                ...bottomReplyKeyboard(userId) 
            }
        );
        return;
    }
    
    const channelsText = REQUIRED_CHANNELS.map(ch => `• ${ch.name}`).join('\n');
    await bot.sendMessage(chatId, 
        `🎉 <b>Welcome to Real finance pay bot!</b>\n\n` +
        `💰 <b>Welcome Bonus:</b> ${formatRefi(WELCOME_BONUS)}\n` +
        `👥 <b>Referral Bonus:</b> ${formatRefi(REFERRAL_BONUS)} per friend\n\n` +
        `📢 <b>To start, you must join these channels first:</b>\n${channelsText}\n\n` +
        `🐦 <i>Optional:</i> Follow on X for updates\n\n` +
        `👇 After joining, click the VERIFY button`,
        { 
            parse_mode: 'HTML', 
            reply_markup: channelsKeyboard()
        }
    );
});

// ==================== ADMIN COMMAND ====================
bot.onText(/\/admin/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    
    console.log(`\n🔐 ADMIN: User ${userId} tried to access admin panel`);
    
    if (!ADMIN_IDS.includes(Number(userId))) {
        await bot.sendMessage(chatId,
            `⛔ <b>Unauthorized Access</b>\n\nYou are not authorized to use this command.`,
            { parse_mode: 'HTML' }
        );
        return;
    }
    
    if (isAdminLoggedIn(userId)) {
        const stats = getStats();
        const hours = Math.floor(stats.uptime / 3600);
        const minutes = Math.floor((stats.uptime % 3600) / 60);
        
        await bot.sendMessage(chatId,
            `👑 <b>Admin Panel</b>\n\n` +
            `📊 <b>Statistics</b>\n` +
            `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
            `• Twitter followers: ${stats.twitter_followers}\n` +
            `• Balance: ${formatRefi(stats.total_balance)}\n` +
            `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
            `• Total referrals: ${stats.total_referrals}\n` +
            `• Uptime: ${hours}h ${minutes}m`,
            { parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
        );
        return;
    }
    
    await bot.sendMessage(chatId,
        "🔐 <b>Admin Login</b>\n\nPlease enter the admin password:",
        { parse_mode: 'HTML', ...removeKeyboard() }
    );
    
    updateUser(userId, { pending_state: 'admin_login' });
});

// ==================== CALLBACK QUERY HANDLER ====================
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;
    const msgId = query.message.message_id;
    
    console.log(`🔍 Callback: ${data} from user ${userId}`);
    
    try {
        // ===== VERIFY =====
        if (data === 'verify') {
            await bot.answerCallbackQuery(query.id);
            
            const joined = await checkChannels(userId);
            const user = db.users[String(userId)];
            
            if (!user) {
                await bot.editMessageText(
                    `❌ User not found`,
                    { chat_id: chatId, message_id: msgId }
                );
                return;
            }
            
            if (joined && !user.verified) {
                const newBalance = (user.balance || 0) + WELCOME_BONUS;
                updateUser(userId, { 
                    verified: true, 
                    balance: newBalance, 
                    total_earned: (user.total_earned || 0) + WELCOME_BONUS 
                });
                
                if (user.referred_by) {
                    const referrerId = user.referred_by;
                    const referrer = db.users[String(referrerId)];
                    if (referrer) {
                        updateUser(referrerId, { 
                            balance: (referrer.balance || 0) + REFERRAL_BONUS,
                            referrals_count: (referrer.referrals_count || 0) + 1
                        });
                        
                        try {
                            await bot.sendMessage(Number(referrerId), 
                                `🎉 <b>You earned ${formatRefi(REFERRAL_BONUS)} from a referral!</b>`,
                                { parse_mode: 'HTML' }
                            );
                        } catch (e) {}
                    }
                }
                
                await bot.editMessageText(
                    `✅ <b>Verification Successful!</b>\n\n✨ Added ${formatRefi(WELCOME_BONUS)}\n💰 Balance: ${formatRefi(newBalance)}`,
                    { 
                        chat_id: chatId, 
                        message_id: msgId, 
                        parse_mode: 'HTML' 
                    }
                );
                
                await bot.sendMessage(chatId,
                    `👇 Use the buttons below:`,
                    bottomReplyKeyboard(userId)
                );
                
            } else if (user.verified) {
                await bot.editMessageText(
                    `✅ You're already verified!`,
                    { chat_id: chatId, message_id: msgId, parse_mode: 'HTML' }
                );
                
                await bot.sendMessage(chatId,
                    `👇 Use the buttons below:`,
                    bottomReplyKeyboard(userId)
                );
            } else {
                const channelsText = REQUIRED_CHANNELS.map(ch => `• ${ch.name}`).join('\n');
                await bot.editMessageText(
                    `❌ <b>Not joined yet!</b>\n\nPlease join:\n${channelsText}`,
                    { 
                        chat_id: chatId, 
                        message_id: msgId, 
                        parse_mode: 'HTML',
                        reply_markup: channelsKeyboard() 
                    }
                );
            }
        }
        
        // ===== WITHDRAW NOW =====
        else if (data === 'withdraw_now') {
            await bot.answerCallbackQuery(query.id);
            
            const user = db.users[String(userId)];
            if (!user) return;
            
            await bot.deleteMessage(chatId, msgId).catch(() => {});
            
            if (!user.verified) {
                await bot.sendMessage(chatId,
                    `❌ <b>Please verify first!</b>\n\nYou need to join the channels and click VERIFY.`,
                    { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            if (!user.wallet) {
                await bot.sendMessage(chatId,
                    `👛 <b>Wallet Required</b>\n\nPlease send your BEP20 wallet address.`,
                    { parse_mode: 'HTML', ...removeKeyboard() }
                );
                updateUser(userId, { pending_state: 'waiting_wallet' });
                return;
            }
            
            if ((user.balance || 0) < MIN_WITHDRAW) {
                const needed = MIN_WITHDRAW - (user.balance || 0);
                await bot.sendMessage(chatId,
                    `⚠️ <b>Insufficient Balance</b>\n\n` +
                    `Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
                    `Your balance: ${formatRefi(user.balance || 0)}\n\n` +
                    `You need <b>${formatRefi(needed)}</b> more to withdraw.`,
                    { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            await bot.sendMessage(chatId,
                `💸 <b>Withdrawal Request</b>\n\n` +
                `Balance: ${formatRefi(user.balance || 0)}\n` +
                `Minimum: ${formatRefi(MIN_WITHDRAW)}\n` +
                `Wallet: ${shortWallet(user.wallet)}\n\n` +
                `📝 <b>Enter amount:</b>`,
                { parse_mode: 'HTML', ...removeKeyboard() }
            );
            
            updateUser(userId, { pending_state: 'waiting_amount' });
        }
        
        // ===== BACK TO MENU =====
        else if (data === 'back_to_menu') {
            await bot.answerCallbackQuery(query.id);
            await bot.deleteMessage(chatId, msgId).catch(() => {});
            const user = db.users[String(userId)];
            await bot.sendMessage(chatId,
                `🎯 <b>Main Menu</b>\n\n💰 Balance: ${formatRefi(user?.balance || 0)}`,
                { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
            );
        }
        
        // ===== ADMIN STATISTICS =====
        else if (data === 'admin_stats') {
            await bot.answerCallbackQuery(query.id);
            
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const stats = getStats();
            await bot.editMessageText(
                `📊 <b>Statistics</b>\n\n` +
                `Users: ${stats.total_users}\n` +
                `Verified: ${stats.verified}\n` +
                `Twitter: ${stats.twitter_followers}\n` +
                `Balance: ${formatRefi(stats.total_balance)}\n`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
            );
        }
        
        // ===== ADMIN BROADCAST =====
        else if (data === 'admin_broadcast') {
            await bot.answerCallbackQuery(query.id);
            
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            await bot.editMessageText(
                "📢 <b>Broadcast</b>\n\nSend the message you want to broadcast to all users:",
                { 
                    chat_id: chatId, 
                    message_id: msgId, 
                    parse_mode: 'HTML', 
                    reply_markup: { 
                        inline_keyboard: [[{ text: '🔙 Cancel', callback_data: 'admin_back' }]] 
                    } 
                }
            );
            updateUser(userId, { pending_state: 'admin_broadcast' });
        }
        
        // ===== ADMIN USERS =====
        else if (data === 'admin_users') {
            await bot.answerCallbackQuery(query.id);
            
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const users = Object.values(db.users)
                .sort((a, b) => (b.joined_at || 0) - (a.joined_at || 0))
                .slice(0, 10);
            
            let text = "👥 <b>Recent Users</b>\n\n";
            users.forEach(u => {
                const name = u.first_name || 'Unknown';
                const username = u.username ? `@${u.username}` : 'No username';
                const verified = u.verified ? '✅' : '❌';
                const twitter = u.twitter_followed ? '🐦' : '';
                const joined = u.joined_at ? new Date(u.joined_at * 1000).toLocaleDateString() : 'Unknown';
                text += `${verified}${twitter} ${name} ${username}\n📅 ${joined} | 💰 ${formatRefi(u.balance || 0)}\n\n`;
            });
            text += `\n📊 <b>Total users: ${Object.keys(db.users).length}</b>`;
            
            await bot.editMessageText(
                text,
                { chat_id: chatId, message_id: msgId, parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
            );
        }
        
        // ===== ADMIN BACK =====
        else if (data === 'admin_back') {
            await bot.answerCallbackQuery(query.id);
            
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const stats = getStats();
            await bot.editMessageText(
                `👑 <b>Admin Panel</b>\n\n` +
                `📊 <b>Statistics</b>\n` +
                `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                `• Twitter: ${stats.twitter_followers}\n` +
                `• Balance: ${formatRefi(stats.total_balance)}\n` +
                `• Referrals: ${stats.total_referrals}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
            );
        }
        
        // ===== ADMIN LOGOUT =====
        else if (data === 'admin_logout') {
            await bot.answerCallbackQuery(query.id);
            
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            adminLogout(userId);
            const user = db.users[String(userId)];
            await bot.editMessageText(
                `🔒 <b>Logged Out</b>\n\n💰 Balance: ${formatRefi(user?.balance || 0)}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'HTML', reply_markup: bottomReplyKeyboard(userId) }
            );
        }
        
        else {
            await bot.answerCallbackQuery(query.id, { text: 'Unknown command', show_alert: false });
            console.log(`⚠️ Unknown callback: ${data}`);
        }
        
    } catch (error) {
        console.error('❌ Error in callback:', error);
        try {
            await bot.answerCallbackQuery(query.id, { text: '❌ Error occurred', show_alert: false });
        } catch (e) {}
    }
});

// ==================== MESSAGE HANDLER ====================
bot.on('message', async (msg) => {
    if (msg.text?.startsWith('/')) return;
    if (msg.text === '✅ VERIFY MEMBERSHIP') return;
    
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const text = msg.text;
    
    console.log(`📩 Message: ${text} from ${userId}`);
    
    const user = db.users[String(userId)];
    if (!user) return;
    
    try {
        if (text === '💰 Balance') {
            await bot.sendMessage(chatId,
                `💰 <b>Your Balance</b>\n\n` +
                `• Current: ${formatRefi(user.balance || 0)}\n` +
                `• Total earned: ${formatRefi(user.total_earned || 0)}\n` +
                `• Total withdrawn: ${formatRefi(user.total_withdrawn || 0)}\n` +
                `• Referrals: ${user.referrals_count || 0}`,
                { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '🔗 Referral') {
            const link = `https://t.me/${botUsername}?start=${userId}`;
            const earned = (user.referrals_count || 0) * REFERRAL_BONUS;
            
            await bot.sendMessage(chatId,
                `🔗 <b>Your Referral Link</b>\n\n<code>${link}</code>\n\n` +
                `• Link clicks: ${user.referral_clicks || 0}\n` +
                `• Successful referrals: ${user.referrals_count || 0}\n` +
                `• Earnings from referrals: ${formatRefi(earned)}`,
                { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '📊 Stats') {
            const joined = user.joined_at ? new Date(user.joined_at * 1000).toLocaleDateString() : 'Unknown';
            
            await bot.sendMessage(chatId,
                `📊 <b>Your Statistics</b>\n\n` +
                `• ID: <code>${userId}</code>\n` +
                `• Joined: ${joined}\n` +
                `• Balance: ${formatRefi(user.balance || 0)}\n` +
                `• Total earned: ${formatRefi(user.total_earned || 0)}\n` +
                `• Referrals: ${user.referrals_count || 0}\n` +
                `• Link clicks: ${user.referral_clicks || 0}\n` +
                `• Verified: ${user.verified ? '✅' : '❌'}\n` +
                `• Wallet: ${user.wallet ? shortWallet(user.wallet) : 'Not set'}`,
                { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '💸 Withdraw') {
            if (!user.verified) {
                await bot.sendMessage(chatId,
                    `❌ <b>Please verify first!</b>\n\nYou need to join the channels and click VERIFY.`,
                    { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            if (!user.wallet) {
                await bot.sendMessage(chatId,
                    `👛 <b>Wallet Required</b>\n\nPlease send your BEP20 wallet address.\nIt must start with <code>0x</code> and be 42 characters long.`,
                    { parse_mode: 'HTML', ...removeKeyboard() }
                );
                updateUser(userId, { pending_state: 'waiting_wallet' });
                return;
            }
            
            if ((user.balance || 0) < MIN_WITHDRAW) {
                const needed = MIN_WITHDRAW - (user.balance || 0);
                await bot.sendMessage(chatId,
                    `⚠️ <b>Insufficient Balance</b>\n\n` +
                    `Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
                    `Your balance: ${formatRefi(user.balance || 0)}\n\n` +
                    `You need <b>${formatRefi(needed)}</b> more to withdraw.`,
                    { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            await bot.sendMessage(chatId,
                `💸 <b>Withdrawal Request</b>\n\n` +
                `Balance: ${formatRefi(user.balance || 0)}\n` +
                `Minimum: ${formatRefi(MIN_WITHDRAW)}\n` +
                `Wallet: ${shortWallet(user.wallet)}\n\n` +
                `📝 <b>Enter amount:</b>`,
                { parse_mode: 'HTML', ...removeKeyboard() }
            );
            
            updateUser(userId, { pending_state: 'waiting_amount' });
        }
        
        else if (text === '👑 Admin Panel') {
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.sendMessage(chatId, `⛔ <b>Unauthorized Access</b>`, { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) });
                return;
            }
            
            if (!isAdminLoggedIn(userId)) {
                await bot.sendMessage(chatId, "🔐 <b>Admin Login</b>\n\nPlease use /admin command to login.", { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) });
                return;
            }
            
            const stats = getStats();
            const hours = Math.floor(stats.uptime / 3600);
            const minutes = Math.floor((stats.uptime % 3600) / 60);
            
            await bot.sendMessage(chatId,
                `👑 <b>Admin Panel</b>\n\n` +
                `📊 <b>Statistics</b>\n` +
                `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                `• Twitter followers: ${stats.twitter_followers}\n` +
                `• Balance: ${formatRefi(stats.total_balance)}\n` +
                `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
                `• Total referrals: ${stats.total_referrals}\n` +
                `• Uptime: ${hours}h ${minutes}m`,
                { parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
            );
        }
        
        else if (user.pending_state === 'waiting_wallet') {
            if (isValidWallet(text)) {
                updateUser(userId, { wallet: text, pending_state: null });
                await bot.sendMessage(chatId,
                    `✅ <b>Wallet saved!</b>\n\n${shortWallet(text)}`,
                    { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) }
                );
                console.log(`👛 Wallet set for ${userId}`);
                
                await bot.sendMessage(chatId,
                    `💸 Would you like to make a withdrawal now?`,
                    {
                        reply_markup: {
                            inline_keyboard: [
                                [{ text: '✅ Yes, withdraw now', callback_data: 'withdraw_now' }],
                                [{ text: '🔙 Back to menu', callback_data: 'back_to_menu' }]
                            ]
                        }
                    }
                );
            } else {
                await bot.sendMessage(chatId,
                    "❌ <b>Invalid wallet address!</b>\n\nMust start with 0x and be 42 characters.",
                    { parse_mode: 'HTML' }
                );
            }
        }
        
        else if (user.pending_state === 'waiting_amount') {
            const amount = parseInt(text.replace(/,/g, ''));
            if (isNaN(amount)) {
                await bot.sendMessage(chatId, "❌ Invalid amount");
                return;
            }
            
            if (amount < MIN_WITHDRAW) {
                await bot.sendMessage(chatId, `❌ Minimum is ${formatRefi(MIN_WITHDRAW)}`);
                return;
            }
            
            if (amount > (user.balance || 0)) {
                await bot.sendMessage(chatId, `❌ Insufficient balance`);
                return;
            }
            
            // استدعاء دالة طلب السحب الجديدة التي ترسل للمجموعة
            const success = await requestWithdrawal(userId, amount, user.wallet);
            
            if (success) {
                console.log(`💰 Withdrawal: ${userId} requested ${amount} REFi (sent to group)`);
            }
        }
        
        else if (user.pending_state === 'admin_login') {
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.sendMessage(chatId, `⛔ <b>Unauthorized</b>`, { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) });
                updateUser(userId, { pending_state: null });
                return;
            }
            
            if (text === ADMIN_PASSWORD) {
                adminLogin(userId);
                updateUser(userId, { pending_state: null });
                
                const stats = getStats();
                const hours = Math.floor(stats.uptime / 3600);
                const minutes = Math.floor((stats.uptime % 3600) / 60);
                
                await bot.sendMessage(chatId,
                    `✅ <b>Login Successful!</b>\n\n` +
                    `👑 <b>Admin Panel</b>\n\n` +
                    `📊 <b>Statistics</b>\n` +
                    `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                    `• Twitter followers: ${stats.twitter_followers}\n` +
                    `• Balance: ${formatRefi(stats.total_balance)}\n` +
                    `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
                    `• Uptime: ${hours}h ${minutes}m`,
                    { parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
                );
            } else {
                await bot.sendMessage(chatId, "❌ <b>Wrong password!</b>", { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) });
                updateUser(userId, { pending_state: null });
            }
        }
        
        else if (user.pending_state === 'admin_broadcast') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.sendMessage(chatId, `⛔ <b>Unauthorized</b>`, { parse_mode: 'HTML', ...bottomReplyKeyboard(userId) });
                updateUser(userId, { pending_state: null });
                return;
            }
            
            updateUser(userId, { pending_state: null });
            await bot.sendMessage(chatId, `📢 Broadcasting to ${Object.keys(db.users).length} users...`);
            
            let sent = 0;
            let failed = 0;
            
            for (const uid of Object.keys(db.users)) {
                try {
                    await bot.sendMessage(Number(uid), text, { parse_mode: 'HTML' });
                    sent++;
                    if (sent % 10 === 0) {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                } catch (e) {
                    failed++;
                }
            }
            
            await bot.sendMessage(chatId,
                `✅ <b>Broadcast Complete</b>\n\nSent: ${sent}\nFailed: ${failed}`,
                { parse_mode: 'HTML', reply_markup: adminInlineKeyboard() }
            );
        }
        
    } catch (error) {
        console.error('❌ Error in message handler:', error);
    }
});

// ==================== WEB SERVER ====================
app.get('/', (req, res) => {
    const stats = getStats();
    const cacheStats = userCache.getStats();
    res.send(`
        <html>
            <head>
                <title>🤖 REFi Bot</title>
                <style>
                    body { font-family: Arial; text-align: center; padding: 50px; 
                           background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                           color: white; }
                    .status { display: inline-block; padding: 10px 20px; 
                              background: rgba(0,255,0,0.2); border-radius: 50px; }
                    .stats { margin-top: 20px; font-size: 14px; }
                </style>
            </head>
            <body>
                <h1>🤖 REFi Bot</h1>
                <div class="status">🟢 RUNNING</div>
                <p>@${botUsername}</p>
                <p>Users: ${stats.total_users} | Verified: ${stats.verified}</p>
                <div class="stats">
                    <p>📊 Cache: ${cacheStats.size}/${cacheStats.maxSize} users</p>
                    <p>🎯 Hit rate: ${cacheStats.hitRate}</p>
                    <p>🗑️ Evictions: ${cacheStats.evictions}</p>
                </div>
                <p>${new Date().toLocaleString()}</p>
            </body>
        </html>
    `);
});

app.get('/health', (req, res) => {
    res.send('OK');
});

app.get('/status', (req, res) => {
    const stats = getStats();
    const cacheStats = userCache.getStats();
    res.json({
        status: 'running',
        time: new Date().toISOString(),
        stats: {
            users: stats.total_users,
            verified: stats.verified
        },
        cache: cacheStats
    });
});

app.get('/cache-stats', (req, res) => {
    res.json(userCache.getStats());
});

app.listen(PORT, () => {
    console.log(`🌐 Web server started on port ${PORT}`);
});

// ==================== START ====================
console.log('\n' + '='.repeat(60));
console.log('🚀 REFi BOT - ULTIMATE FINAL VERSION WITH CACHE');
console.log('='.repeat(60));
console.log(`📱 Bot: @${botUsername}`);
console.log(`👤 Admin ID: ${ADMIN_IDS[0]}`);
console.log(`💰 Welcome: ${formatRefi(WELCOME_BONUS)}`);
console.log(`👥 Referral: ${formatRefi(REFERRAL_BONUS)}`);
console.log(`💸 Min withdraw: ${formatRefi(MIN_WITHDRAW)}`);
console.log(`📢 Payment Group ID: ${PAYMENT_GROUP}`);
console.log(`📊 Cache max size: 1000 users`);
console.log('='.repeat(60));

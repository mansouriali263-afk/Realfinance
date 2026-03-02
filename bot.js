// ==================== REFi BOT - FINAL ULTIMATE VERSION ====================
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const express = require('express');
const app = express();
const PORT = process.env.PORT || 10000;

// ==================== CONFIG ====================
const token = '7823073143:AAGdGquDK2Ee-wOp5bGzS6dx2y92wRBOVJw';
const botUsername = 'RealnetworkPaybot';

// تكوين البوت مع إعدادات متقدمة للـ polling
const bot = new TelegramBot(token, { 
    polling: true,
    polling: {
        interval: 300,
        autoStart: true,
        params: {
            timeout: 30
        }
    }
});

// Fix 409 conflict - force kill any existing sessions
bot.deleteWebHook().then(() => {
    console.log('✅ Webhook deleted');
    return bot.getUpdates({ offset: -1 });
}).then(() => {
    console.log('✅ Cleared all updates');
}).catch(err => {
    console.log('⚠️ Cleanup error:', err.message);
});

// Test token
bot.getMe().then(me => {
    console.log(`✅ Bot connected: @${me.username}`);
}).catch(err => {
    console.log('❌ Token error:', err.message);
    process.exit(1);
});

// ==================== CONSTANTS ====================
const WELCOME_BONUS = 1_000_000;
const REFERRAL_BONUS = 1_000_000;
const MIN_WITHDRAW = 5_000_000;
const ADMIN_IDS = [1653918641];
const ADMIN_PASSWORD = 'Ali97$';
const PAYMENT_CHANNEL = '@beefy_payment';

// Required channels (Telegram)
const REQUIRED_CHANNELS = [
    { name: 'REFi Distribution', username: '@Realfinance_REFI' },
    { name: 'Airdrop Master VIP', username: '@Airdrop_MasterVIP' },
    { name: 'Daily Airdrop', username: '@Daily_AirdropX' }
];

// Twitter account (يظهر فقط في أول رسالة)
const TWITTER_ACCOUNT = {
    name: 'Daily Airdrop on X',
    username: '@Daily_AirdropX',
    url: 'https://x.com/Daily_AirdropX'
};

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
    console.log(`✅ Loaded ${Object.keys(db.users).length} users`);
} catch { 
    console.log('⚠️ No existing data, starting fresh'); 
}

function saveDB() { 
    fs.writeFileSync('bot_data.json', JSON.stringify(db, null, 2)); 
}

// ==================== USER FUNCTIONS ====================
function getUser(userId) {
    const uid = String(userId);
    if (!db.users[uid]) {
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
    return db.users[uid];
}

function updateUser(userId, updates) {
    const uid = String(userId);
    if (db.users[uid]) {
        db.users[uid] = { ...db.users[uid], ...updates };
        saveDB();
        console.log(`✅ User ${uid} updated:`, updates);
    }
}

// ==================== WITHDRAWAL FUNCTIONS ====================
function getPendingWithdrawals() { 
    return Object.values(db.withdrawals).filter(w => w.status === 'pending'); 
}

function getUserWithdrawals(userId, status = null) {
    const uid = String(userId);
    let withdrawals = Object.values(db.withdrawals).filter(w => w.user_id === uid);
    if (status) {
        withdrawals = withdrawals.filter(w => w.status === status);
    }
    return withdrawals.sort((a, b) => b.created_at - a.created_at);
}

function createWithdrawal(userId, amount, wallet) {
    const uid = String(userId);
    const rid = `W${Math.floor(Date.now() / 1000)}${uid}${Math.floor(Math.random() * 9000) + 1000}`;
    db.withdrawals[rid] = {
        id: rid,
        user_id: uid,
        amount: amount,
        wallet: wallet,
        status: 'pending',
        created_at: Date.now() / 1000
    };
    saveDB();
    return rid;
}

function processWithdrawal(rid, adminId, status) {
    const w = db.withdrawals[rid];
    if (!w || w.status !== 'pending') return false;
    
    w.status = status;
    w.processed_at = Date.now() / 1000;
    w.processed_by = adminId;
    
    if (status === 'rejected') {
        const user = db.users[w.user_id];
        if (user) {
            user.balance += w.amount;
        }
    }
    saveDB();
    return true;
}

// ==================== ADMIN SESSION ====================
function isAdminLoggedIn(adminId) { 
    if (!ADMIN_IDS.includes(Number(adminId))) return false;
    return db.admin_sessions[String(adminId)] > Date.now() / 1000; 
}

function adminLogin(adminId) { 
    if (!ADMIN_IDS.includes(Number(adminId))) return false;
    db.admin_sessions[String(adminId)] = Date.now() / 1000 + 3600; 
    saveDB(); 
    return true;
}

function adminLogout(adminId) { 
    delete db.admin_sessions[String(adminId)]; 
    saveDB(); 
}

// ==================== STATS ====================
function getStats() {
    const users = Object.values(db.users);
    const now = Date.now() / 1000;
    return {
        total_users: users.length,
        verified: users.filter(u => u.verified).length,
        total_balance: users.reduce((s, u) => s + u.balance, 0),
        total_earned: users.reduce((s, u) => s + u.total_earned, 0),
        total_withdrawn: db.stats.total_withdrawn || 0,
        pending_withdrawals: getPendingWithdrawals().length,
        total_referrals: users.reduce((s, u) => s + (u.referrals_count || 0), 0),
        twitter_followers: users.filter(u => u.twitter_followed).length,
        uptime: now - db.stats.start_time
    };
}

// ==================== FORMATTING ====================
function formatRefi(refi) { 
    const usd = (refi / 1000000) * 2; 
    return `${refi.toLocaleString()} REFi (~$${usd.toFixed(2)})`; 
}

function shortWallet(w) { 
    return w ? `${w.slice(0, 6)}...${w.slice(-4)}` : 'Not set'; 
}

function isValidWallet(w) { 
    return w && w.startsWith('0x') && w.length === 42; 
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
            [{ text: '💰 Pending Withdrawals', callback_data: 'admin_pending' }],
            [{ text: '📢 Broadcast', callback_data: 'admin_broadcast' }],
            [{ text: '👥 Users List', callback_data: 'admin_users' }],
            [{ text: '🔒 Logout', callback_data: 'admin_logout' }]
        ]
    };
}

function withdrawalInlineKeyboard(rid) {
    return {
        inline_keyboard: [
            [
                { text: '✅ Approve', callback_data: `approve_${rid}` },
                { text: '❌ Reject', callback_data: `reject_${rid}` }
            ],
            [{ text: '🔙 Back', callback_data: 'admin_pending' }]
        ]
    };
}

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
                    `👋 *Someone clicked your referral link!*\n\nThey'll get ${formatRefi(REFERRAL_BONUS)} when they verify.`,
                    { parse_mode: 'Markdown' }
                );
            } catch (e) {}
        }
    }
    
    if (user.verified) {
        await bot.sendMessage(chatId, 
            `🎯 *Welcome Back!*\n\n💰 Balance: ${formatRefi(user.balance)}`,
            { 
                parse_mode: 'Markdown', 
                ...bottomReplyKeyboard(userId) 
            }
        );
        return;
    }
    
    const channelsText = REQUIRED_CHANNELS.map(ch => `• ${ch.name}`).join('\n');
    await bot.sendMessage(chatId, 
        `🎉 *Welcome to Realfinancepaybot!*\n\n` +
        `💰 *Welcome Bonus:* ${formatRefi(WELCOME_BONUS)}\n` +
        `👥 *Referral Bonus:* ${formatRefi(REFERRAL_BONUS)} per friend\n\n` +
        `📢 *To start, you must join these channels first:*\n${channelsText}\n\n` +
        `🐦 *Optional:* Follow on X for updates\n\n` +
        `👇 After joining, click the VERIFY button`,
        { 
            parse_mode: 'Markdown', 
            reply_markup: channelsKeyboard()
        }
    );
});

// ==================== ADMIN COMMAND HANDLER ====================
bot.onText(/\/admin/, async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    
    console.log(`\n🔐 ADMIN: User ${userId} tried to access admin panel`);
    
    if (!ADMIN_IDS.includes(Number(userId))) {
        await bot.sendMessage(chatId,
            `⛔ *Unauthorized Access*\n\nYou are not authorized to use this command.`,
            { parse_mode: 'Markdown' }
        );
        console.log(`❌ Unauthorized admin access attempt by ${userId}`);
        return;
    }
    
    if (isAdminLoggedIn(userId)) {
        const stats = getStats();
        const hours = Math.floor(stats.uptime / 3600);
        const minutes = Math.floor((stats.uptime % 3600) / 60);
        
        await bot.sendMessage(chatId,
            `👑 *Admin Panel*\n\n` +
            `📊 *Statistics*\n` +
            `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
            `• Twitter followers: ${stats.twitter_followers}\n` +
            `• Balance: ${formatRefi(stats.total_balance)}\n` +
            `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
            `• Pending withdrawals: ${stats.pending_withdrawals}\n` +
            `• Total referrals: ${stats.total_referrals}\n` +
            `• Uptime: ${hours}h ${minutes}m`,
            { parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
        );
        return;
    }
    
    await bot.sendMessage(chatId,
        "🔐 *Admin Login*\n\nPlease enter the admin password:",
        { parse_mode: 'Markdown', ...removeKeyboard() }
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
            const joined = await checkChannels(userId);
            const user = db.users[String(userId)];
            
            if (joined && !user.verified) {
                const newBalance = user.balance + WELCOME_BONUS;
                updateUser(userId, { 
                    verified: true, 
                    balance: newBalance, 
                    total_earned: user.total_earned + WELCOME_BONUS 
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
                            await bot.sendMessage(referrerId, 
                                `🎉 *You earned ${formatRefi(REFERRAL_BONUS)}!*`,
                                { parse_mode: 'Markdown' }
                            );
                        } catch (e) {}
                    }
                }
                
                await bot.editMessageText(
                    `✅ *Verification Successful!*\n\n✨ Added ${formatRefi(WELCOME_BONUS)}\n💰 Balance: ${formatRefi(newBalance)}`,
                    { 
                        chat_id: chatId, 
                        message_id: msgId, 
                        parse_mode: 'Markdown' 
                    }
                );
                
                await bot.sendMessage(chatId,
                    `👇 Use the buttons below:`,
                    { ...bottomReplyKeyboard(userId) }
                );
                
            } else if (user.verified) {
                await bot.editMessageText(
                    `✅ You're already verified!`,
                    { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown' }
                );
                
                await bot.sendMessage(chatId,
                    `👇 Use the buttons below:`,
                    { ...bottomReplyKeyboard(userId) }
                );
            } else {
                const channelsText = REQUIRED_CHANNELS.map(ch => `• ${ch.name}`).join('\n');
                await bot.editMessageText(
                    `❌ *Not joined yet!*\n\nPlease join:\n${channelsText}`,
                    { 
                        chat_id: chatId, 
                        message_id: msgId, 
                        parse_mode: 'Markdown',
                        reply_markup: channelsKeyboard() 
                    }
                );
            }
            
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== WITHDRAW NOW =====
        else if (data === 'withdraw_now') {
            const user = db.users[String(userId)];
            if (!user) return;
            
            await bot.deleteMessage(chatId, msgId);
            
            if (!user.verified) {
                await bot.sendMessage(chatId,
                    `❌ *Please verify first!*\n\nYou need to join the channels and click VERIFY.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                await bot.answerCallbackQuery(query.id);
                return;
            }
            
            if (!user.wallet) {
                await bot.sendMessage(chatId,
                    `👛 *Wallet Required*\n\nPlease send your BEP20 wallet address.`,
                    { parse_mode: 'Markdown', ...removeKeyboard() }
                );
                updateUser(userId, { pending_state: 'waiting_wallet' });
                await bot.answerCallbackQuery(query.id);
                return;
            }
            
            if (user.balance < MIN_WITHDRAW) {
                const needed = MIN_WITHDRAW - user.balance;
                await bot.sendMessage(chatId,
                    `⚠️ *Insufficient Balance*\n\n` +
                    `Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
                    `Your balance: ${formatRefi(user.balance)}\n\n` +
                    `You need **${formatRefi(needed)}** more to withdraw.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                await bot.answerCallbackQuery(query.id);
                return;
            }
            
            const pending = getUserWithdrawals(userId, 'pending');
            if (pending.length >= 3) {
                await bot.sendMessage(chatId,
                    `⚠️ You have ${pending.length} pending requests.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                await bot.answerCallbackQuery(query.id);
                return;
            }
            
            await bot.sendMessage(chatId,
                `💸 *Withdrawal Request*\n\n` +
                `Balance: ${formatRefi(user.balance)}\n` +
                `Minimum: ${formatRefi(MIN_WITHDRAW)}\n` +
                `Wallet: ${shortWallet(user.wallet)}\n\n` +
                `📝 *Enter amount:*`,
                { parse_mode: 'Markdown', ...removeKeyboard() }
            );
            
            updateUser(userId, { pending_state: 'waiting_amount' });
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== BACK TO MENU =====
        else if (data === 'back_to_menu') {
            await bot.deleteMessage(chatId, msgId);
            const user = db.users[String(userId)];
            await bot.sendMessage(chatId,
                `🎯 *Main Menu*\n\n💰 Balance: ${formatRefi(user.balance)}`,
                { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== ADMIN STATISTICS =====
        else if (data === 'admin_stats') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const stats = getStats();
            await bot.editMessageText(
                `📊 *Statistics*\n\n` +
                `Users: ${stats.total_users}\n` +
                `Verified: ${stats.verified}\n` +
                `Twitter: ${stats.twitter_followers}\n` +
                `Balance: ${formatRefi(stats.total_balance)}\n` +
                `Pending: ${stats.pending_withdrawals}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== ADMIN PENDING WITHDRAWALS =====
        else if (data === 'admin_pending') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const pending = getPendingWithdrawals();
            
            if (pending.length === 0) {
                await bot.editMessageText(
                    "✅ No pending withdrawals",
                    { chat_id: chatId, message_id: msgId, reply_markup: adminInlineKeyboard() }
                );
                await bot.answerCallbackQuery(query.id);
                return;
            }
            
            let text = "💰 *Pending Withdrawals*\n\n";
            const keyboard = { inline_keyboard: [] };
            
            pending.slice(0, 5).forEach(w => {
                const user = db.users[w.user_id] || { first_name: 'Unknown', username: '' };
                text += `🆔 \`${w.id.slice(0, 8)}...\`\n`;
                text += `👤 ${user.first_name} (@${user.username || 'None'})\n`;
                text += `💰 ${formatRefi(w.amount)}\n`;
                text += `📅 ${new Date(w.created_at * 1000).toLocaleString()}\n\n`;
                
                keyboard.inline_keyboard.push([
                    { text: `Process ${w.id.slice(0, 8)}`, callback_data: `process_${w.id}` }
                ]);
            });
            
            if (pending.length > 5) {
                text += `*... and ${pending.length - 5} more*\n\n`;
            }
            
            keyboard.inline_keyboard.push([{ text: '🔙 Back', callback_data: 'admin_back' }]);
            
            await bot.editMessageText(
                text,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: keyboard }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== PROCESS WITHDRAWAL =====
        else if (data.startsWith('process_')) {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const rid = data.slice(8);
            const w = db.withdrawals[rid];
            if (!w) return;
            
            const user = db.users[w.user_id] || { first_name: 'Unknown', username: '' };
            
            await bot.editMessageText(
                `💰 *Withdrawal Details*\n\n` +
                `📝 Request: \`${rid}\`\n` +
                `👤 User: ${user.first_name} (@${user.username || 'None'})\n` +
                `💰 Amount: ${formatRefi(w.amount)}\n` +
                `📮 Wallet: \`${w.wallet}\`\n` +
                `📅 Created: ${new Date(w.created_at * 1000).toLocaleString()}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: withdrawalInlineKeyboard(rid) }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== APPROVE WITHDRAWAL =====
        else if (data.startsWith('approve_')) {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const rid = data.slice(7);
            if (processWithdrawal(rid, userId, 'approved')) {
                const w = db.withdrawals[rid];
                if (w) {
                    try {
                        await bot.sendMessage(Number(w.user_id),
                            `✅ *Withdrawal Approved!*\n\nAmount: ${formatRefi(w.amount)}`
                        );
                        
                        const user = db.users[w.user_id] || {};
                        const channelMsg = 
                            `✅ *Withdrawal Approved*\n\n` +
                            `👤 User: ${user.first_name || 'Unknown'} (@${user.username || 'None'})\n` +
                            `🆔 ID: \`${w.user_id}\`\n` +
                            `💰 Amount: ${formatRefi(w.amount)}\n` +
                            `📮 Wallet: \`${w.wallet}\``;
                        
                        await bot.sendMessage(PAYMENT_CHANNEL, channelMsg, { parse_mode: 'Markdown' });
                        console.log(`📢 Posted to channel: ${PAYMENT_CHANNEL}`);
                    } catch (e) {
                        console.log('❌ Failed to post to channel:', e.message);
                    }
                }
            }
            
            await bot.answerCallbackQuery(query.id, { text: '✅ Approved' });
            
            // Refresh pending list
            const pending = getPendingWithdrawals();
            if (pending.length === 0) {
                await bot.editMessageText(
                    "✅ No pending withdrawals",
                    { chat_id: chatId, message_id: msgId, reply_markup: adminInlineKeyboard() }
                );
            } else {
                // Re-run admin_pending
                const newQuery = { ...query, data: 'admin_pending' };
                bot.emit('callback_query', newQuery);
            }
        }
        
        // ===== REJECT WITHDRAWAL =====
        else if (data.startsWith('reject_')) {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const rid = data.slice(6);
            if (processWithdrawal(rid, userId, 'rejected')) {
                const w = db.withdrawals[rid];
                if (w) {
                    try {
                        await bot.sendMessage(Number(w.user_id),
                            `❌ *Withdrawal Rejected*\n\nAmount returned: ${formatRefi(w.amount)}`
                        );
                        
                        const user = db.users[w.user_id] || {};
                        const channelMsg = 
                            `❌ *Withdrawal Rejected*\n\n` +
                            `👤 User: ${user.first_name || 'Unknown'} (@${user.username || 'None'})\n` +
                            `🆔 ID: \`${w.user_id}\`\n` +
                            `💰 Amount: ${formatRefi(w.amount)}\n` +
                            `📮 Wallet: \`${w.wallet}\``;
                        
                        await bot.sendMessage(PAYMENT_CHANNEL, channelMsg, { parse_mode: 'Markdown' });
                        console.log(`📢 Posted to channel: ${PAYMENT_CHANNEL}`);
                    } catch (e) {
                        console.log('❌ Failed to post to channel:', e.message);
                    }
                }
            }
            
            await bot.answerCallbackQuery(query.id, { text: '❌ Rejected' });
            
            // Refresh pending list
            const pending = getPendingWithdrawals();
            if (pending.length === 0) {
                await bot.editMessageText(
                    "✅ No pending withdrawals",
                    { chat_id: chatId, message_id: msgId, reply_markup: adminInlineKeyboard() }
                );
            } else {
                // Re-run admin_pending
                const newQuery = { ...query, data: 'admin_pending' };
                bot.emit('callback_query', newQuery);
            }
        }
        
        // ===== ADMIN BACK =====
        else if (data === 'admin_back') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const stats = getStats();
            await bot.editMessageText(
                `👑 *Admin Panel*\n\n` +
                `📊 *Statistics*\n` +
                `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                `• Twitter: ${stats.twitter_followers}\n` +
                `• Balance: ${formatRefi(stats.total_balance)}\n` +
                `• Pending: ${stats.pending_withdrawals}\n` +
                `• Referrals: ${stats.total_referrals}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== ADMIN BROADCAST =====
        else if (data === 'admin_broadcast') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            await bot.editMessageText(
                "📢 *Broadcast*\n\nSend the message you want to broadcast to all users:",
                { 
                    chat_id: chatId, 
                    message_id: msgId, 
                    parse_mode: 'Markdown', 
                    reply_markup: { 
                        inline_keyboard: [[{ text: '🔙 Cancel', callback_data: 'admin_back' }]] 
                    } 
                }
            );
            updateUser(userId, { pending_state: 'admin_broadcast' });
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== ADMIN USERS =====
        else if (data === 'admin_users') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            const users = Object.values(db.users)
                .sort((a, b) => b.joined_at - a.joined_at)
                .slice(0, 10);
            
            let text = "👥 *Recent Users*\n\n";
            users.forEach(u => {
                const name = u.first_name || 'Unknown';
                const username = u.username ? `@${u.username}` : 'No username';
                const verified = u.verified ? '✅' : '❌';
                const twitter = u.twitter_followed ? '🐦' : '';
                const joined = new Date(u.joined_at * 1000).toLocaleDateString();
                text += `${verified}${twitter} ${name} ${username}\n📅 ${joined} | 💰 ${formatRefi(u.balance)}\n\n`;
            });
            text += `\n📊 *Total users: ${Object.keys(db.users).length}*`;
            
            await bot.editMessageText(
                text,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        // ===== ADMIN LOGOUT =====
        else if (data === 'admin_logout') {
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.answerCallbackQuery(query.id, { text: '⛔ Unauthorized', show_alert: true });
                return;
            }
            
            adminLogout(userId);
            const user = db.users[String(userId)];
            await bot.editMessageText(
                `🔒 *Logged Out*\n\n💰 Balance: ${formatRefi(user.balance)}`,
                { chat_id: chatId, message_id: msgId, parse_mode: 'Markdown', reply_markup: bottomReplyKeyboard(userId) }
            );
            await bot.answerCallbackQuery(query.id);
        }
        
        else {
            await bot.answerCallbackQuery(query.id);
        }
        
    } catch (error) {
        console.error('❌ Error in callback:', error.message);
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
    
    console.log(`📩 Reply: ${text} from ${userId}`);
    
    const user = db.users[String(userId)];
    if (!user) return;
    
    try {
        if (text === '💰 Balance') {
            await bot.sendMessage(chatId,
                `💰 *Your Balance*\n\n` +
                `• Current: ${formatRefi(user.balance)}\n` +
                `• Total earned: ${formatRefi(user.total_earned)}\n` +
                `• Total withdrawn: ${formatRefi(user.total_withdrawn)}\n` +
                `• Referrals: ${user.referrals_count || 0}`,
                { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '🔗 Referral') {
            const link = `https://t.me/${botUsername}?start=${userId}`;
            const earned = (user.referrals_count || 0) * REFERRAL_BONUS;
            
            await bot.sendMessage(chatId,
                `🔗 *Your Referral Link*\n\n\`${link}\`\n\n` +
                `• Link clicks: ${user.referral_clicks || 0}\n` +
                `• Successful referrals: ${user.referrals_count || 0}\n` +
                `• Earnings from referrals: ${formatRefi(earned)}`,
                { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '📊 Stats') {
            const joined = new Date(user.joined_at * 1000).toLocaleDateString();
            
            await bot.sendMessage(chatId,
                `📊 *Your Statistics*\n\n` +
                `• ID: \`${userId}\`\n` +
                `• Joined: ${joined}\n` +
                `• Balance: ${formatRefi(user.balance)}\n` +
                `• Total earned: ${formatRefi(user.total_earned)}\n` +
                `• Referrals: ${user.referrals_count || 0}\n` +
                `• Link clicks: ${user.referral_clicks || 0}\n` +
                `• Verified: ${user.verified ? '✅' : '❌'}\n` +
                `• Wallet: ${user.wallet ? shortWallet(user.wallet) : 'Not set'}`,
                { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
            );
        }
        
        else if (text === '💸 Withdraw') {
            if (!user.verified) {
                await bot.sendMessage(chatId,
                    `❌ *Please verify first!*\n\nYou need to join the channels and click VERIFY.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            if (!user.wallet) {
                await bot.sendMessage(chatId,
                    `👛 *Wallet Required*\n\nPlease send your BEP20 wallet address.\nIt must start with \`0x\` and be 42 characters long.`,
                    { parse_mode: 'Markdown', ...removeKeyboard() }
                );
                updateUser(userId, { pending_state: 'waiting_wallet' });
                return;
            }
            
            if (user.balance < MIN_WITHDRAW) {
                const needed = MIN_WITHDRAW - user.balance;
                await bot.sendMessage(chatId,
                    `⚠️ *Insufficient Balance*\n\n` +
                    `Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
                    `Your balance: ${formatRefi(user.balance)}\n\n` +
                    `You need **${formatRefi(needed)}** more to withdraw.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            const pending = getUserWithdrawals(userId, 'pending');
            if (pending.length >= 3) {
                await bot.sendMessage(chatId,
                    `⚠️ You have ${pending.length} pending requests.`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
                );
                return;
            }
            
            await bot.sendMessage(chatId,
                `💸 *Withdrawal Request*\n\n` +
                `Balance: ${formatRefi(user.balance)}\n` +
                `Minimum: ${formatRefi(MIN_WITHDRAW)}\n` +
                `Wallet: ${shortWallet(user.wallet)}\n\n` +
                `📝 *Enter amount:*`,
                { parse_mode: 'Markdown', ...removeKeyboard() }
            );
            
            updateUser(userId, { pending_state: 'waiting_amount' });
        }
        
        else if (text === '👑 Admin Panel') {
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.sendMessage(chatId, `⛔ *Unauthorized Access*`, { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) });
                return;
            }
            
            if (!isAdminLoggedIn(userId)) {
                await bot.sendMessage(chatId, "🔐 *Admin Login*\n\nPlease use /admin command to login.", { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) });
                return;
            }
            
            const stats = getStats();
            const hours = Math.floor(stats.uptime / 3600);
            const minutes = Math.floor((stats.uptime % 3600) / 60);
            
            await bot.sendMessage(chatId,
                `👑 *Admin Panel*\n\n` +
                `📊 *Statistics*\n` +
                `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                `• Twitter followers: ${stats.twitter_followers}\n` +
                `• Balance: ${formatRefi(stats.total_balance)}\n` +
                `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
                `• Pending withdrawals: ${stats.pending_withdrawals}\n` +
                `• Total referrals: ${stats.total_referrals}\n` +
                `• Uptime: ${hours}h ${minutes}m`,
                { parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
            );
        }
        
        else if (user.pending_state === 'waiting_wallet') {
            if (isValidWallet(text)) {
                updateUser(userId, { wallet: text, pending_state: null });
                await bot.sendMessage(chatId,
                    `✅ *Wallet saved!*\n\n${shortWallet(text)}`,
                    { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
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
                    "❌ *Invalid wallet address!*\n\nMust start with 0x and be 42 characters.",
                    { parse_mode: 'Markdown' }
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
            
            if (amount > user.balance) {
                await bot.sendMessage(chatId, `❌ Insufficient balance`);
                return;
            }
            
            const rid = createWithdrawal(userId, amount, user.wallet);
            const newBalance = user.balance - amount;
            const newWithdrawn = (user.total_withdrawn || 0) + amount;
            updateUser(userId, { 
                balance: newBalance, 
                total_withdrawn: newWithdrawn,
                pending_state: null 
            });
            db.stats.total_withdrawn = (db.stats.total_withdrawn || 0) + amount;
            saveDB();
            
            const channelMsg = 
                `💰 *New Withdrawal Request*\n\n` +
                `👤 User: ${user.first_name || 'Unknown'} (@${user.username || 'None'})\n` +
                `🆔 ID: \`${userId}\`\n` +
                `📊 Referrals: ${user.referrals_count || 0}\n` +
                `💵 Amount: ${formatRefi(amount)}\n` +
                `📮 Wallet: \`${user.wallet}\`\n` +
                `🆔 Request ID: \`${rid}\``;
            
            try {
                await bot.sendMessage(PAYMENT_CHANNEL, channelMsg, { parse_mode: 'Markdown' });
                console.log(`📢 Posted to channel: ${PAYMENT_CHANNEL}`);
            } catch (e) {
                console.log('❌ Failed to post to channel:', e.message);
            }
            
            await bot.sendMessage(chatId,
                `✅ *Withdrawal Request Submitted!*\n\nRequest ID: \`${rid.slice(0, 8)}...\``,
                { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) }
            );
            
            console.log(`💰 Withdrawal: ${userId} requested ${amount} REFi`);
        }
        
        else if (user.pending_state === 'admin_login') {
            if (!ADMIN_IDS.includes(Number(userId))) {
                await bot.sendMessage(chatId, `⛔ *Unauthorized*`, { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) });
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
                    `✅ *Login Successful!*\n\n` +
                    `👑 *Admin Panel*\n\n` +
                    `📊 *Statistics*\n` +
                    `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
                    `• Twitter followers: ${stats.twitter_followers}\n` +
                    `• Balance: ${formatRefi(stats.total_balance)}\n` +
                    `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
                    `• Pending: ${stats.pending_withdrawals}\n` +
                    `• Uptime: ${hours}h ${minutes}m`,
                    { parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
                );
            } else {
                await bot.sendMessage(chatId, "❌ *Wrong password!*", { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) });
                updateUser(userId, { pending_state: null });
            }
        }
        
        else if (user.pending_state === 'admin_broadcast') {
            if (!ADMIN_IDS.includes(Number(userId)) || !isAdminLoggedIn(userId)) {
                await bot.sendMessage(chatId, `⛔ *Unauthorized*`, { parse_mode: 'Markdown', ...bottomReplyKeyboard(userId) });
                updateUser(userId, { pending_state: null });
                return;
            }
            
            updateUser(userId, { pending_state: null });
            await bot.sendMessage(chatId, `📢 Broadcasting to ${Object.keys(db.users).length} users...`);
            
            let sent = 0;
            let failed = 0;
            
            for (const uid of Object.keys(db.users)) {
                try {
                    await bot.sendMessage(Number(uid), text, { parse_mode: 'Markdown' });
                    sent++;
                    if (sent % 10 === 0) {
                        await new Promise(resolve => setTimeout(resolve, 1000));
                    }
                } catch (e) {
                    failed++;
                }
            }
            
            await bot.sendMessage(chatId,
                `✅ *Broadcast Complete*\n\nSent: ${sent}\nFailed: ${failed}`,
                { parse_mode: 'Markdown', reply_markup: adminInlineKeyboard() }
            );
        }
        
    } catch (error) {
        console.error('❌ Error in message handler:', error.message);
    }
});

// ==================== WEB SERVER ====================
app.get('/', (req, res) => {
    const stats = getStats();
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
                </style>
            </head>
            <body>
                <h1>🤖 REFi Bot</h1>
                <div class="status">🟢 RUNNING</div>
                <p>@${botUsername}</p>
                <p>Users: ${stats.total_users} | Verified: ${stats.verified}</p>
                <p>Pending: ${stats.pending_withdrawals}</p>
                <p>${new Date().toLocaleString()}</p>
            </body>
        </html>
    `);
});

app.get('/health', (req, res) => res.send('OK'));

app.listen(PORT, () => {
    console.log(`🌐 Web server started on port ${PORT}`);
});

// ==================== START ====================
console.log('\n' + '='.repeat(60));
console.log('🚀 REFi BOT - FINAL ULTIMATE VERSION');
console.log('='.repeat(60));
console.log(`📱 Bot: @${botUsername}`);
console.log(`👤 Admin IDs: ${ADMIN_IDS.join(', ')}`);
console.log(`💰 Welcome: ${formatRefi(WELCOME_BONUS)}`);
console.log(`👥 Referral: ${formatRefi(REFERRAL_BONUS)}`);
console.log(`💸 Min withdraw: ${formatRefi(MIN_WITHDRAW)}`);
console.log(`📢 Payment channel: ${PAYMENT_CHANNEL}`);
console.log('='.repeat(60));

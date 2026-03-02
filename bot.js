// ==================== REFi BOT - BOTTOM NAVIGATION VERSION ====================
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const express = require('express');
const app = express();
const PORT = process.env.PORT || 10000;

// ==================== CONFIG ====================
const token = process.env.BOT_TOKEN || '7823073143:AAHP0N0-_BwakdWG_QblRD8z8I8e6pY7gmY';
const botUsername = 'RealnetworkPaybot';
const bot = new TelegramBot(token, { polling: true });

const WELCOME_BONUS = 1000000;
const REFERRAL_BONUS = 1000000;
const MIN_WITHDRAW = 5000000;

// Admin settings
const ADMIN_IDS = [1653918641];
const ADMIN_PASSWORD = 'Ali97$';

// Required channels
const REQUIRED_CHANNELS = [
    { name: 'REFi Distribution', username: '@Realfinance_REFI' },
    { name: 'Airdrop Master VIP', username: '@Airdrop_MasterVIP' },
    { name: 'Daily Airdrop', username: '@Daily_AirdropX' }
];

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
} catch (err) {
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
    const session = db.admin_sessions[String(adminId)];
    return session && session > Date.now() / 1000;
}

function adminLogin(adminId) {
    db.admin_sessions[String(adminId)] = (Date.now() / 1000) + 3600;
    saveDB();
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
        total_balance: users.reduce((sum, u) => sum + u.balance, 0),
        total_earned: users.reduce((sum, u) => sum + u.total_earned, 0),
        total_withdrawn: db.stats.total_withdrawn || 0,
        pending_withdrawals: getPendingWithdrawals().length,
        total_referrals: users.reduce((sum, u) => sum + (u.referrals_count || 0), 0),
        uptime: now - db.stats.start_time
    };
}

// ==================== FORMATTING ====================
function formatRefi(refi) {
    const usd = (refi / 1000000) * 2;
    return `${refi.toLocaleString()} REFi (~$${usd.toFixed(2)})`;
}

function shortWallet(wallet) {
    if (!wallet || wallet.length < 10) return 'Not set';
    return `${wallet.slice(0, 6)}...${wallet.slice(-4)}`;
}

function isValidWallet(wallet) {
    return wallet && wallet.startsWith('0x') && wallet.length === 42;
}

// ==================== KEYBOARDS ====================
function channelsKeyboard() {
    // Floating buttons for channels (before verification)
    const keyboard = [];
    REQUIRED_CHANNELS.forEach(ch => {
        keyboard.push([{ 
            text: `📢 Join ${ch.name}`, 
            url: `https://t.me/${ch.username.substring(1)}` 
        }]);
    });
    keyboard.push([{ 
        text: '✅ VERIFY MEMBERSHIP', 
        callback_data: 'verify' 
    }]);
    return { inline_keyboard: keyboard };
}

function bottomNavigation(userId) {
    // Bottom navigation menu (always at the bottom) - Like the image
    const user = db.users[String(userId)] || {};
    
    // Create bottom navigation similar to the image
    const keyboard = [
        [
            { text: '💰 Balance', callback_data: 'bal' },
            { text: '🔗 Referral', callback_data: 'ref' }
        ],
        [
            { text: '📊 Stats', callback_data: 'stats' },
            { text: '👛 Wallet', callback_data: 'wallet' }
        ]
    ];
    
    // Add withdraw button if wallet exists
    if (user.wallet) {
        keyboard[1][1] = { text: '💸 Withdraw', callback_data: 'wd' };
    }
    
    // Add admin button for admins
    if (ADMIN_IDS.includes(Number(userId)) && isAdminLoggedIn(Number(userId))) {
        keyboard.push([{ text: '👑 Admin Panel', callback_data: 'admin' }]);
    }
    
    return { inline_keyboard: keyboard };
}

function backButton() {
    return { inline_keyboard: [[{ text: '🔙 Back to Menu', callback_data: 'back' }]] };
}

function cancelButton() {
    return { inline_keyboard: [[{ text: '❌ Cancel', callback_data: 'back' }]] };
}

function adminKeyboard() {
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

function withdrawalKeyboard(rid) {
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

// ==================== CHECK CHANNEL MEMBERSHIP ====================
async function checkChannels(userId) {
    for (const ch of REQUIRED_CHANNELS) {
        try {
            const member = await bot.getChatMember(ch.username, userId);
            if (!['member', 'administrator', 'creator'].includes(member.status)) {
                return { allJoined: false, notJoined: [ch.name] };
            }
        } catch (err) {
            return { allJoined: false, notJoined: [ch.name] };
        }
    }
    return { allJoined: true, notJoined: [] };
}

// ==================== HANDLERS ====================
// /start command
bot.onText(/\/start(?:\s+(.+))?/, async (msg, match) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const username = msg.from.username || '';
    const firstName = msg.from.first_name || '';
    const referrerId = match[1] ? parseInt(match[1]) : null;
    
    console.log(`\n▶️ START: User ${userId}`);
    
    // Get or create user
    let user = getUser(userId);
    updateUser(userId, { username, first_name: firstName });
    
    // Handle referral
    if (referrerId && referrerId !== userId && !user.referred_by) {
        console.log(`🔍 Referral from: ${referrerId}`);
        updateUser(userId, { referred_by: referrerId });
        
        const referrer = db.users[String(referrerId)];
        if (referrer) {
            updateUser(referrerId, { 
                referral_clicks: (referrer.referral_clicks || 0) + 1 
            });
            
            try {
                await bot.sendMessage(referrerId, 
                    `👋 *Someone clicked your referral link!*\n\n` +
                    `They haven't verified yet. Once they verify, you'll get ${formatRefi(REFERRAL_BONUS)}!`,
                    { parse_mode: 'Markdown' }
                );
            } catch (e) {
                console.log(`Could not notify referrer: ${e.message}`);
            }
        }
    }
    
    // Check if already verified
    if (user.verified) {
        await bot.sendMessage(chatId, 
            `🎯 *Welcome Back!*\n\n💰 Balance: ${formatRefi(user.balance)}`,
            { parse_mode: 'Markdown', reply_markup: bottomNavigation(userId) }
        );
        return;
    }
    
    // Check channels
    const { allJoined, notJoined } = await checkChannels(userId);
    
    if (allJoined) {
        // Add welcome bonus
        const newBalance = user.balance + WELCOME_BONUS;
        updateUser(userId, { 
            verified: true, 
            balance: newBalance, 
            total_earned: user.total_earned + WELCOME_BONUS 
        });
        console.log(`✅ Welcome bonus added: ${WELCOME_BONUS}`);
        
        // Process referral
        if (user.referred_by) {
            const referrerId = user.referred_by;
            const referrer = db.users[String(referrerId)];
            if (referrer) {
                const refNewBalance = (referrer.balance || 0) + REFERRAL_BONUS;
                updateUser(referrerId, { 
                    balance: refNewBalance,
                    total_earned: (referrer.total_earned || 0) + REFERRAL_BONUS,
                    referrals_count: (referrer.referrals_count || 0) + 1
                });
                
                try {
                    await bot.sendMessage(referrerId, 
                        `🎉 *Congratulations!*\n\n` +
                        `Your friend ${firstName || 'Someone'} just verified!\n` +
                        `✨ You earned ${formatRefi(REFERRAL_BONUS)}!`,
                        { parse_mode: 'Markdown' }
                    );
                } catch (e) {
                    console.log(`Could not notify referrer: ${e.message}`);
                }
            }
        }
        
        await bot.sendMessage(chatId, 
            `✅ *Verification Successful!*\n\n` +
            `✨ Added ${formatRefi(WELCOME_BONUS)} to your balance\n` +
            `💰 Current balance: ${formatRefi(newBalance)}`,
            { parse_mode: 'Markdown', reply_markup: bottomNavigation(userId) }
        );
    } else {
        // ===== THIS IS THE CHANNELS VERIFICATION MESSAGE =====
        const channelsText = REQUIRED_CHANNELS.map(ch => `• ${ch.name}`).join('\n');
        
        await bot.sendMessage(chatId, 
            `🎉 *Welcome to Realfinancepaybot!*\n\n` +
            `💰 *Welcome Bonus:* ${formatRefi(WELCOME_BONUS)}\n` +
            `👥 *Referral Bonus:* ${formatRefi(REFERRAL_BONUS)} per friend\n\n` +
            `📢 *To start, you must join these channels first:*\n` +
            `${channelsText}\n\n` +
            `👇 After joining, click the VERIFY button`,
            { 
                parse_mode: 'Markdown', 
                reply_markup: channelsKeyboard() 
            }
        );
    }
});

// Callback queries
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;
    const msgId = query.message.message_id;
    
    await bot.answerCallbackQuery(query.id);
    console.log(`🔍 Callback: ${data} from user ${userId}`);
    
    // Ensure user exists
    getUser(userId);
    
    // ===== VERIFY =====
    if (data === 'verify') {
        const { allJoined, notJoined } = await checkChannels(userId);
        
        if (allJoined) {
            const user = db.users[String(userId)];
            
            if (!user.verified) {
                const newBalance = user.balance + WELCOME_BONUS;
                updateUser(userId, { 
                    verified: true, 
                    balance: newBalance, 
                    total_earned: user.total_earned + WELCOME_BONUS 
                });
                
                // Process referral
                if (user.referred_by) {
                    const referrerId = user.referred_by;
                    const referrer = db.users[String(referrerId)];
                    if (referrer) {
                        updateUser(referrerId, { 
                            balance: (referrer.balance || 0) + REFERRAL_BONUS,
                            total_earned: (referrer.total_earned || 0) + REFERRAL_BONUS,
                            referrals_count: (referrer.referrals_count || 0) + 1
                        });
                        
                        try {
                            await bot.sendMessage(referrerId, 
                                `🎉 *Congratulations!*\n\nYour friend just verified!\n✨ You earned ${formatRefi(REFERRAL_BONUS)}!`,
                                { parse_mode: 'Markdown' }
                            );
                        } catch (e) {}
                    }
                }
                
                await bot.editMessageText(
                    `✅ *Verification Successful!*\n\n` +
                    `✨ Added ${formatRefi(WELCOME_BONUS)}\n` +
                    `💰 Current balance: ${formatRefi(newBalance)}`,
                    {
                        chat_id: chatId,
                        message_id: msgId,
                        parse_mode: 'Markdown',
                        reply_markup: bottomNavigation(userId)
                    }
                );
            }
        } else {
            await bot.editMessageText(
                `❌ *You haven't joined these channels:*\n${notJoined.join('\n')}`,
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: channelsKeyboard()
                }
            );
        }
    }
    
    // ===== BALANCE =====
    else if (data === 'bal') {
        const user = db.users[String(userId)];
        await bot.editMessageText(
            `💰 *Your Balance*\n\n` +
            `• Current: ${formatRefi(user.balance)}\n` +
            `• Total earned: ${formatRefi(user.total_earned)}\n` +
            `• Total withdrawn: ${formatRefi(user.total_withdrawn)}\n` +
            `• Referrals: ${user.referrals_count || 0}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backButton()
            }
        );
    }
    
    // ===== REFERRAL =====
    else if (data === 'ref') {
        const user = db.users[String(userId)];
        const link = `https://t.me/${botUsername}?start=${userId}`;
        const earned = (user.referrals_count || 0) * REFERRAL_BONUS;
        
        await bot.editMessageText(
            `🔗 *Your Referral Link*\n\n` +
            `\`${link}\`\n\n` +
            `• Link clicks: ${user.referral_clicks || 0}\n` +
            `• Successful referrals: ${user.referrals_count || 0}\n` +
            `• Earnings from referrals: ${formatRefi(earned)}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backButton()
            }
        );
    }
    
    // ===== STATS =====
    else if (data === 'stats') {
        const user = db.users[String(userId)];
        const joined = new Date(user.joined_at * 1000).toLocaleDateString();
        
        await bot.editMessageText(
            `📊 *Your Statistics*\n\n` +
            `• ID: \`${userId}\`\n` +
            `• Joined: ${joined}\n` +
            `• Balance: ${formatRefi(user.balance)}\n` +
            `• Total earned: ${formatRefi(user.total_earned)}\n` +
            `• Referrals: ${user.referrals_count || 0}\n` +
            `• Link clicks: ${user.referral_clicks || 0}\n` +
            `• Verified: ${user.verified ? '✅' : '❌'}\n` +
            `• Wallet: ${user.wallet ? shortWallet(user.wallet) : 'Not set'}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backButton()
            }
        );
    }
    
    // ===== WALLET =====
    else if (data === 'wallet') {
        const user = db.users[String(userId)];
        const current = user.wallet ? shortWallet(user.wallet) : 'Not set';
        
        await bot.editMessageText(
            `👛 *Set Withdrawal Wallet*\n\n` +
            `Current wallet: ${current}\n\n` +
            `Please send your BEP20 wallet address.\n` +
            `It must start with \`0x\` and be 42 characters long.\n\n` +
            `Example:\n` +
            `\`0x742d35Cc6634C0532925a3b844Bc454e4438f44e\``,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: cancelButton()
            }
        );
        updateUser(userId, { pending_state: 'waiting_wallet' });
    }
    
    // ===== WITHDRAW =====
    else if (data === 'wd') {
        const user = db.users[String(userId)];
        
        if (!user.verified) {
            await bot.editMessageText(
                "❌ *Please verify first!*\n\nYou need to join the channels and verify your membership.",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: backButton()
                }
            );
            return;
        }
        
        if (!user.wallet) {
            await bot.editMessageText(
                "⚠️ *Wallet Required*\n\nYou need to set a wallet address first.\nPlease use the 👛 Set Wallet button.",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: bottomNavigation(userId)
                }
            );
            return;
        }
        
        if (user.balance < MIN_WITHDRAW) {
            const needed = MIN_WITHDRAW - user.balance;
            await bot.editMessageText(
                `⚠️ *Insufficient Balance*\n\n` +
                `• Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
                `• Your balance: ${formatRefi(user.balance)}\n\n` +
                `You need **${formatRefi(needed)}** more to withdraw.\n\n` +
                `💡 Invite more friends to earn more REFi!`,
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: bottomNavigation(userId)
                }
            );
            return;
        }
        
        // Check pending withdrawals
        const pending = getUserWithdrawals(userId, 'pending');
        if (pending.length >= 3) {
            await bot.editMessageText(
                `⚠️ *Pending Withdrawals Limit*\n\n` +
                `You already have ${pending.length} pending withdrawal requests.\n` +
                `Maximum allowed is 3.\n\n` +
                `Please wait for them to be processed before requesting more.`,
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: bottomNavigation(userId)
                }
            );
            return;
        }
        
        await bot.editMessageText(
            `💸 *Withdrawal Request*\n\n` +
            `• Your balance: ${formatRefi(user.balance)}\n` +
            `• Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}\n` +
            `• Your wallet: \`${shortWallet(user.wallet)}\`\n\n` +
            `📝 *Please enter the amount you want to withdraw:*`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: cancelButton()
            }
        );
        updateUser(userId, { pending_state: 'waiting_amount' });
    }
    
    // ===== BACK =====
    else if (data === 'back') {
        const user = db.users[String(userId)];
        await bot.editMessageText(
            `🎯 *Main Menu*\n\n💰 Balance: ${formatRefi(user.balance)}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: bottomNavigation(userId)
            }
        );
        updateUser(userId, { pending_state: null });
    }
    
    // ===== ADMIN =====
    else if (data === 'admin') {
        if (!ADMIN_IDS.includes(userId)) return;
        
        if (!isAdminLoggedIn(userId)) {
            await bot.editMessageText(
                "🔐 *Admin Login*\n\nPlease enter the admin password:",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    parse_mode: 'Markdown',
                    reply_markup: backButton()
                }
            );
            updateUser(userId, { pending_state: 'admin_login' });
            return;
        }
        
        const stats = getStats();
        const hours = Math.floor(stats.uptime / 3600);
        const minutes = Math.floor((stats.uptime % 3600) / 60);
        
        await bot.editMessageText(
            `👑 *Admin Panel*\n\n` +
            `📊 *Statistics*\n` +
            `• Users: ${stats.total_users} (✅ ${stats.verified})\n` +
            `• Total balance: ${formatRefi(stats.total_balance)}\n` +
            `• Total withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
            `• Pending withdrawals: ${stats.pending_withdrawals}\n` +
            `• Total referrals: ${stats.total_referrals}\n` +
            `• Uptime: ${hours}h ${minutes}m`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: adminKeyboard()
            }
        );
    }
    
    // ===== ADMIN STATS =====
    else if (data === 'admin_stats') {
        const stats = getStats();
        const hours = Math.floor(stats.uptime / 3600);
        const minutes = Math.floor((stats.uptime % 3600) / 60);
        
        await bot.editMessageText(
            `📊 *Detailed Statistics*\n\n` +
            `👥 *Users*\n` +
            `• Total: ${stats.total_users}\n` +
            `• Verified: ${stats.verified}\n\n` +
            `💰 *Balances*\n` +
            `• Total balance: ${formatRefi(stats.total_balance)}\n` +
            `• Total earned: ${formatRefi(stats.total_earned)}\n` +
            `• Total withdrawn: ${formatRefi(stats.total_withdrawn)}\n\n` +
            `⏳ *Pending Withdrawals: ${stats.pending_withdrawals}*\n` +
            `👥 *Total Referrals: ${stats.total_referrals}*\n\n` +
            `⏱️ *Uptime: ${hours}h ${minutes}m*`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: adminKeyboard()
            }
        );
    }
    
    // ===== ADMIN PENDING =====
    else if (data === 'admin_pending') {
        const pending = getPendingWithdrawals();
        
        if (pending.length === 0) {
            await bot.editMessageText(
                "✅ No pending withdrawals",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    reply_markup: adminKeyboard()
                }
            );
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
        
        keyboard.inline_keyboard.push([{ text: '🔙 Back', callback_data: 'admin' }]);
        
        await bot.editMessageText(
            text,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: keyboard
            }
        );
    }
    
    // ===== PROCESS WITHDRAWAL =====
    else if (data.startsWith('process_')) {
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
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: withdrawalKeyboard(rid)
            }
        );
    }
    
    // ===== APPROVE WITHDRAWAL =====
    else if (data.startsWith('approve_')) {
        const rid = data.slice(7);
        if (processWithdrawal(rid, userId, 'approved')) {
            const w = db.withdrawals[rid];
            if (w) {
                try {
                    await bot.sendMessage(Number(w.user_id),
                        `✅ *Withdrawal Approved!*\n\n` +
                        `Request: \`${rid.slice(0, 8)}...\`\n` +
                        `Amount: ${formatRefi(w.amount)}`
                    );
                } catch (e) {}
            }
        }
        // Refresh pending list
        const pending = getPendingWithdrawals();
        if (pending.length === 0) {
            await bot.editMessageText(
                "✅ No pending withdrawals",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    reply_markup: adminKeyboard()
                }
            );
        } else {
            bot.emit('callback_query', { 
                ...query, 
                data: 'admin_pending' 
            });
        }
    }
    
    // ===== REJECT WITHDRAWAL =====
    else if (data.startsWith('reject_')) {
        const rid = data.slice(6);
        if (processWithdrawal(rid, userId, 'rejected')) {
            const w = db.withdrawals[rid];
            if (w) {
                try {
                    await bot.sendMessage(Number(w.user_id),
                        `❌ *Withdrawal Rejected*\n\n` +
                        `Request: \`${rid.slice(0, 8)}...\`\n` +
                        `Amount returned: ${formatRefi(w.amount)}`
                    );
                } catch (e) {}
            }
        }
        // Refresh pending list
        const pending = getPendingWithdrawals();
        if (pending.length === 0) {
            await bot.editMessageText(
                "✅ No pending withdrawals",
                {
                    chat_id: chatId,
                    message_id: msgId,
                    reply_markup: adminKeyboard()
                }
            );
        } else {
            bot.emit('callback_query', { 
                ...query, 
                data: 'admin_pending' 
            });
        }
    }
    
    // ===== ADMIN BROADCAST =====
    else if (data === 'admin_broadcast') {
        await bot.editMessageText(
            "📢 *Broadcast*\n\nSend the message you want to broadcast to all users:",
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backButton()
            }
        );
        updateUser(userId, { pending_state: 'admin_broadcast' });
    }
    
    // ===== ADMIN USERS =====
    else if (data === 'admin_users') {
        const users = Object.values(db.users)
            .sort((a, b) => b.joined_at - a.joined_at)
            .slice(0, 10);
        
        let text = "👥 *Recent Users*\n\n";
        users.forEach(u => {
            const name = u.first_name || 'Unknown';
            const username = u.username ? `@${u.username}` : 'No username';
            const verified = u.verified ? '✅' : '❌';
            const joined = new Date(u.joined_at * 1000).toLocaleDateString();
            text += `${verified} ${name} ${username}\n📅 ${joined} | 💰 ${formatRefi(u.balance)}\n\n`;
        });
        text += `\n📊 *Total users: ${Object.keys(db.users).length}*`;
        
        await bot.editMessageText(
            text,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: adminKeyboard()
            }
        );
    }
    
    // ===== ADMIN LOGOUT =====
    else if (data === 'admin_logout') {
        adminLogout(userId);
        const user = db.users[String(userId)];
        await bot.editMessageText(
            `🔒 *Logged Out*\n\n💰 Balance: ${formatRefi(user.balance)}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: bottomNavigation(userId)
            }
        );
    }
});

// ==================== TEXT MESSAGES ====================
bot.on('message', async (msg) => {
    if (msg.text && msg.text.startsWith('/')) return;
    
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const text = msg.text;
    
    const user = db.users[String(userId)];
    if (!user) return;
    
    const pendingState = user.pending_state;
    
    // ===== WAITING FOR WALLET =====
    if (pendingState === 'waiting_wallet') {
        if (isValidWallet(text)) {
            updateUser(userId, { 
                wallet: text, 
                pending_state: null 
            });
            
            await bot.sendMessage(chatId,
                `✅ *Wallet saved successfully!*\n\n` +
                `Wallet: \`${shortWallet(text)}\`\n\n` +
                `You can now withdraw your REFi tokens.`,
                { parse_mode: 'Markdown', reply_markup: bottomNavigation(userId) }
            );
            console.log(`👛 User ${userId} saved wallet`);
        } else {
            await bot.sendMessage(chatId,
                `❌ *Invalid wallet address!*\n\n` +
                `Please send a valid BEP20 address starting with \`0x\` and 42 characters long.`,
                { parse_mode: 'Markdown' }
            );
        }
    }
    
    // ===== WAITING FOR WITHDRAWAL AMOUNT =====
    else if (pendingState === 'waiting_amount') {
        const amount = parseInt(text.replace(/,/g, ''));
        if (isNaN(amount)) {
            await bot.sendMessage(chatId, 
                "❌ *Invalid amount*\n\nPlease enter a valid number.",
                { parse_mode: 'Markdown' }
            );
            return;
        }
        
        if (amount < MIN_WITHDRAW) {
            await bot.sendMessage(chatId, 
                `❌ *Amount too low*\n\nMinimum withdrawal is ${formatRefi(MIN_WITHDRAW)}.`,
                { parse_mode: 'Markdown' }
            );
            return;
        }
        
        if (amount > user.balance) {
            await bot.sendMessage(chatId,
                `❌ *Insufficient balance*\n\nYour balance: ${formatRefi(user.balance)}.`,
                { parse_mode: 'Markdown' }
            );
            return;
        }
        
        // Process withdrawal
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
        
        // Post to payment channel
        const channelMsg = 
            `💰 *New Withdrawal Request*\n\n` +
            `👤 User: ${user.first_name || 'Unknown'} (@${user.username || 'None'})\n` +
            `🆔 ID: \`${userId}\`\n` +
            `📊 Referrals: ${user.referrals_count || 0}\n` +
            `💵 Amount: ${formatRefi(amount)}\n` +
            `📮 Wallet: \`${user.wallet}\`\n` +
            `🆔 Request ID: \`${rid}\``;
        
        try {
            await bot.sendMessage('@beefy_payment', channelMsg, { parse_mode: 'Markdown' });
        } catch (e) {
            console.log('Could not post to payment channel');
        }
        
        await bot.sendMessage(chatId,
            `✅ *Withdrawal Request Submitted!*\n\n` +
            `• Request ID: \`${rid.slice(0, 8)}...\`\n` +
            `• Amount: ${formatRefi(amount)}\n` +
            `• Status: *Pending Review*\n\n` +
            `You will be notified once processed.`,
            { parse_mode: 'Markdown', reply_markup: bottomNavigation(userId) }
        );
        
        console.log(`💰 User ${userId} requested withdrawal of ${amount} REFi`);
    }
    
    // ===== ADMIN LOGIN =====
    else if (pendingState === 'admin_login') {
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
                `• Balance: ${formatRefi(stats.total_balance)}\n` +
                `• Withdrawn: ${formatRefi(stats.total_withdrawn)}\n` +
                `• Pending: ${stats.pending_withdrawals}\n` +
                `• Uptime: ${hours}h ${minutes}m`,
                { parse_mode: 'Markdown', reply_markup: adminKeyboard() }
            );
        } else {
            await bot.sendMessage(chatId, "❌ *Wrong password!*", { parse_mode: 'Markdown' });
        }
    }
    
    // ===== ADMIN BROADCAST =====
    else if (pendingState === 'admin_broadcast') {
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
            `✅ *Broadcast Complete*\n\n` +
            `• Sent: ${sent}\n` +
            `• Failed: ${failed}`,
            { parse_mode: 'Markdown', reply_markup: adminKeyboard() }
        );
    }
});

// ==================== WEB SERVER ====================
app.get('/', (req, res) => {
    const stats = getStats();
    res.send(`
        <html>
            <head>
                <title>🤖 REFi Bot</title>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    body { 
                        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        min-height: 100vh;
                        margin: 0;
                        display: flex;
                        justify-content: center;
                        align-items: center;
                    }
                    .container {
                        text-align: center;
                        background: rgba(255, 255, 255, 0.1);
                        backdrop-filter: blur(10px);
                        padding: 2rem;
                        border-radius: 20px;
                        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
                    }
                    h1 { font-size: 2.5rem; margin-bottom: 1rem; }
                    .status {
                        display: inline-block;
                        padding: 0.5rem 1rem;
                        border-radius: 50px;
                        background: rgba(0, 255, 0, 0.2);
                        border: 1px solid rgba(0, 255, 0, 0.5);
                        margin: 1rem 0;
                    }
                    .stats {
                        display: grid;
                        grid-template-columns: repeat(2, 1fr);
                        gap: 1rem;
                        margin-top: 2rem;
                    }
                    .stat-card {
                        background: rgba(255, 255, 255, 0.1);
                        padding: 1rem;
                        border-radius: 10px;
                    }
                    .stat-value { font-size: 1.5rem; font-weight: bold; }
                    .stat-label { font-size: 0.9rem; opacity: 0.8; }
                </style>
            </head>
            <body>
                <div class="container">
                    <h1>🤖 REFi Bot</h1>
                    <div class="status">🟢 ONLINE</div>
                    <p>@${botUsername}</p>
                    
                    <div class="stats">
                        <div class="stat-card">
                            <div class="stat-value">${stats.total_users}</div>
                            <div class="stat-label">Users</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.verified}</div>
                            <div class="stat-label">Verified</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${stats.pending_withdrawals}</div>
                            <div class="stat-label">Pending</div>
                        </div>
                        <div class="stat-card">
                            <div class="stat-value">${Math.floor(stats.uptime / 3600)}h</div>
                            <div class="stat-label">Uptime</div>
                        </div>
                    </div>
                    
                    <p style="margin-top: 2rem; font-size: 0.8rem; opacity: 0.5;">
                        ${new Date().toLocaleString()}
                    </p>
                </div>
            </body>
        </html>
    `);
});

app.get('/health', (req, res) => res.send('OK'));

app.listen(PORT, () => {
    console.log(`🌐 Web server started on port ${PORT}`);
});

// ==================== START ====================
console.log('🚀 REFi Bot started successfully!');
console.log(`📱 Bot username: @${botUsername}`);
console.log(`💰 Welcome bonus: ${formatRefi(WELCOME_BONUS)}`);
console.log(`👥 Referral bonus: ${formatRefi(REFERRAL_BONUS)}`);
console.log(`💸 Minimum withdrawal: ${formatRefi(MIN_WITHDRAW)}`);

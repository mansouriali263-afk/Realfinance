// ==================== REFi BOT - JavaScript Version ====================
const TelegramBot = require('node-telegram-bot-api');
const fs = require('fs');
const express = require('express');
const app = express();

// ==================== CONFIG ====================
const token = '7823073143:AAEpY2NpDzs14u3V5RebgW-THiaHjeJRKpQ';
const bot = new TelegramBot(token, { polling: true });

const WELCOME_BONUS = 1000000;
const REFERRAL_BONUS = 1000000;

// ==================== DATABASE ====================
let db = { users: {} };

try {
    db = JSON.parse(fs.readFileSync('bot_data.json'));
    console.log(`✅ Loaded ${Object.keys(db.users).length} users`);
} catch (err) {
    console.log('⚠️ No existing data, starting fresh');
}

function saveDB() {
    fs.writeFileSync('bot_data.json', JSON.stringify(db, null, 2));
}

// ==================== KEYBOARDS ====================
function channelsKeyboard() {
    return {
        inline_keyboard: [
            [{ text: '📢 Join REFi Distribution', url: 'https://t.me/Realfinance_REFI' }],
            [{ text: '📢 Join Airdrop Master VIP', url: 'https://t.me/Airdrop_MasterVIP' }],
            [{ text: '📢 Join Daily Airdrop', url: 'https://t.me/Daily_AirdropX' }],
            [{ text: '✅ VERIFY MEMBERSHIP', callback_data: 'verify' }]
        ]
    };
}

function mainKeyboard(userId) {
    const user = db.users[userId] || { wallet: null };
    const keyboard = [
        [{ text: '💰 Balance', callback_data: 'bal' }],
        [{ text: '🔗 Referral', callback_data: 'ref' }],
        [{ text: '📊 Statistics', callback_data: 'stats' }]
    ];
    
    if (user.wallet) {
        keyboard.push([{ text: '💸 Withdraw', callback_data: 'wd' }]);
    } else {
        keyboard.push([{ text: '👛 Set Wallet', callback_data: 'wallet' }]);
    }
    
    return { inline_keyboard: keyboard };
}

function backKeyboard() {
    return {
        inline_keyboard: [[{ text: '🔙 Back to Menu', callback_data: 'back' }]]
    };
}

// ==================== HANDLERS ====================
bot.onText(/\/start(.+)?/, async (msg, match) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const referrerId = match[1] ? parseInt(match[1]) : null;
    
    console.log(`\n▶️ Start: ${userId}`);
    
    // Create user if not exists
    if (!db.users[userId]) {
        db.users[userId] = {
            balance: 0,
            total_earned: 0,
            referred_by: null,
            verified: false,
            referrals: 0,
            clicks: 0,
            wallet: null
        };
        saveDB();
        console.log(`✅ New user created: ${userId}`);
    }
    
    // Handle referral
    if (referrerId && referrerId !== userId && !db.users[userId].referred_by) {
        console.log(`🔍 Referral from: ${referrerId}`);
        db.users[userId].referred_by = referrerId;
        
        if (db.users[referrerId]) {
            db.users[referrerId].clicks = (db.users[referrerId].clicks || 0) + 1;
            saveDB();
            
            await bot.sendMessage(referrerId, 
                `👋 *Someone clicked your referral link!*\n\n` +
                `They haven't verified yet. Once they verify, you'll get 1,000,000 REFi!`,
                { parse_mode: 'Markdown' }
            );
        }
        saveDB();
    }
    
    // Check if user is verified
    if (db.users[userId].verified) {
        await bot.sendMessage(chatId, 
            `🎯 *Welcome back!*\n💰 Balance: ${db.users[userId].balance.toLocaleString()} REFi`,
            { parse_mode: 'Markdown', reply_markup: mainKeyboard(userId) }
        );
        return;
    }
    
    // Check channels
    const channels = ['@Realfinance_REFI', '@Airdrop_MasterVIP', '@Daily_AirdropX'];
    let allJoined = true;
    
    for (const channel of channels) {
        try {
            const member = await bot.getChatMember(channel, userId);
            if (!['member', 'administrator', 'creator'].includes(member.status)) {
                allJoined = false;
                break;
            }
        } catch (err) {
            allJoined = false;
        }
    }
    
    if (allJoined) {
        // Add welcome bonus
        db.users[userId].balance += WELCOME_BONUS;
        db.users[userId].total_earned += WELCOME_BONUS;
        db.users[userId].verified = true;
        saveDB();
        
        // Process referral
        if (db.users[userId].referred_by) {
            const referrerId = db.users[userId].referred_by;
            if (db.users[referrerId]) {
                db.users[referrerId].balance += REFERRAL_BONUS;
                db.users[referrerId].total_earned += REFERRAL_BONUS;
                db.users[referrerId].referrals = (db.users[referrerId].referrals || 0) + 1;
                saveDB();
                
                await bot.sendMessage(referrerId, 
                    `🎉 *Congratulations!*\n\n` +
                    `Your friend just verified!\n` +
                    `✨ You earned 1,000,000 REFi!`,
                    { parse_mode: 'Markdown' }
                );
            }
        }
        
        await bot.sendMessage(chatId, 
            `✅ *Verification Successful!*\n\n` +
            `✨ Added 1,000,000 REFi to your balance\n` +
            `💰 Current balance: ${db.users[userId].balance.toLocaleString()} REFi`,
            { parse_mode: 'Markdown', reply_markup: mainKeyboard(userId) }
        );
    } else {
        await bot.sendMessage(chatId, 
            `🎉 *Welcome to REFi Bot!*\n\n` +
            `💰 Welcome: 1,000,000 REFi (~$2.00)\n` +
            `👥 Referral: 1,000,000 REFi (~$2.00) per friend\n\n` +
            `📢 Join the channels below and click VERIFY:`,
            { parse_mode: 'Markdown', reply_markup: channelsKeyboard() }
        );
    }
});

// ==================== CALLBACK QUERIES ====================
bot.on('callback_query', async (query) => {
    const chatId = query.message.chat.id;
    const userId = query.from.id;
    const data = query.data;
    const msgId = query.message.message_id;
    
    // Answer callback immediately
    await bot.answerCallbackQuery(query.id);
    
    // Create user if not exists
    if (!db.users[userId]) {
        db.users[userId] = {
            balance: 0,
            total_earned: 0,
            referred_by: null,
            verified: false,
            referrals: 0,
            clicks: 0,
            wallet: null
        };
        saveDB();
    }
    
    // ===== VERIFY =====
    if (data === 'verify') {
        const channels = ['@Realfinance_REFI', '@Airdrop_MasterVIP', '@Daily_AirdropX'];
        let allJoined = true;
        let notJoined = [];
        
        for (const channel of channels) {
            try {
                const member = await bot.getChatMember(channel, userId);
                if (!['member', 'administrator', 'creator'].includes(member.status)) {
                    allJoined = false;
                    notJoined.push(channel);
                }
            } catch (err) {
                allJoined = false;
                notJoined.push(channel);
            }
        }
        
        if (allJoined) {
            if (!db.users[userId].verified) {
                db.users[userId].balance += WELCOME_BONUS;
                db.users[userId].total_earned += WELCOME_BONUS;
                db.users[userId].verified = true;
                saveDB();
                
                if (db.users[userId].referred_by) {
                    const referrerId = db.users[userId].referred_by;
                    if (db.users[referrerId]) {
                        db.users[referrerId].balance += REFERRAL_BONUS;
                        db.users[referrerId].total_earned += REFERRAL_BONUS;
                        db.users[referrerId].referrals = (db.users[referrerId].referrals || 0) + 1;
                        saveDB();
                        
                        await bot.sendMessage(referrerId, 
                            `🎉 *Congratulations!*\n\nYour friend just verified!\n✨ You earned 1,000,000 REFi!`,
                            { parse_mode: 'Markdown' }
                        );
                    }
                }
                
                await bot.editMessageText(
                    `✅ *Verification Successful!*\n\n✨ Added 1,000,000 REFi\n💰 Current balance: ${db.users[userId].balance.toLocaleString()} REFi`,
                    {
                        chat_id: chatId,
                        message_id: msgId,
                        parse_mode: 'Markdown',
                        reply_markup: mainKeyboard(userId)
                    }
                );
            }
        } else {
            await bot.editMessageText(
                `❌ *Not joined:*\n${notJoined.join('\n')}`,
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
        await bot.editMessageText(
            `💰 *Your Balance*\n\n` +
            `• Current: ${db.users[userId].balance.toLocaleString()} REFi\n` +
            `• Total earned: ${db.users[userId].total_earned.toLocaleString()} REFi\n` +
            `• Referrals: ${db.users[userId].referrals || 0}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backKeyboard()
            }
        );
    }
    
    // ===== REFERRAL =====
    else if (data === 'ref') {
        const link = `https://t.me/Realfinancepaybot?start=${userId}`;
        await bot.editMessageText(
            `🔗 *Your Referral Link*\n\n\`${link}\`\n\n` +
            `• Clicks: ${db.users[userId].clicks || 0}\n` +
            `• Referrals: ${db.users[userId].referrals || 0}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backKeyboard()
            }
        );
    }
    
    // ===== STATISTICS =====
    else if (data === 'stats') {
        await bot.editMessageText(
            `📊 *Your Statistics*\n\n` +
            `• Balance: ${db.users[userId].balance.toLocaleString()} REFi\n` +
            `• Total earned: ${db.users[userId].total_earned.toLocaleString()} REFi\n` +
            `• Referrals: ${db.users[userId].referrals || 0}\n` +
            `• Clicks: ${db.users[userId].clicks || 0}\n` +
            `• Verified: ${db.users[userId].verified ? '✅' : '❌'}`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: backKeyboard()
            }
        );
    }
    
    // ===== WALLET =====
    else if (data === 'wallet') {
        await bot.editMessageText(
            `👛 *Set Wallet*\n\n` +
            `Please send your Bep20 wallet address from trust wallet.\n` +
            `Must start with \`0x\` and be 42 characters long.\n\n` +
            `Example:\n` +
            `\`0x742d35Cc6634C0532925a3b844Bc454e4438f44e\``,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: { inline_keyboard: [[{ text: '❌ Cancel', callback_data: 'back' }]] }
            }
        );
        
        // Set state for wallet input
        db.users[userId].waiting_for = 'wallet';
        saveDB();
    }
    
    // ===== BACK =====
    else if (data === 'back') {
        await bot.editMessageText(
            `🎯 *Main Menu*\n\n💰 Balance: ${db.users[userId].balance.toLocaleString()} REFi`,
            {
                chat_id: chatId,
                message_id: msgId,
                parse_mode: 'Markdown',
                reply_markup: mainKeyboard(userId)
            }
        );
        
        // Clear any waiting state
        if (db.users[userId].waiting_for) {
            delete db.users[userId].waiting_for;
            saveDB();
        }
    }
});

// ==================== TEXT MESSAGES (for wallet input) ====================
bot.on('message', async (msg) => {
    const chatId = msg.chat.id;
    const userId = msg.from.id;
    const text = msg.text;
    
    // Ignore commands
    if (text.startsWith('/')) return;
    
    // Check if waiting for wallet
    if (db.users[userId] && db.users[userId].waiting_for === 'wallet') {
        // Validate wallet
        if (text.match(/^0x[a-fA-F0-9]{40}$/)) {
            db.users[userId].wallet = text;
            delete db.users[userId].waiting_for;
            saveDB();
            
            await bot.sendMessage(chatId,
                `✅ *Wallet saved!*\n\n${text.slice(0,6)}...${text.slice(-4)}`,
                { parse_mode: 'Markdown', reply_markup: mainKeyboard(userId) }
            );
        } else {
            await bot.sendMessage(chatId,
                `❌ *Invalid wallet address!*\n\nPlease send a valid Ethereum address starting with 0x and 42 characters long.`,
                { parse_mode: 'Markdown' }
            );
        }
    }
});

// ==================== WEB SERVER for Render ====================
app.get('/', (req, res) => res.send('🤖 REFi Bot is running!'));
app.get('/health', (req, res) => res.send('OK'));
app.listen(process.env.PORT || 3000, () => {
    console.log('🌐 Web server started on port', process.env.PORT || 3000);
});

console.log('🚀 REFi Bot started successfully!');
console.log(`📱 Bot username: @RealnetworkPaybot);

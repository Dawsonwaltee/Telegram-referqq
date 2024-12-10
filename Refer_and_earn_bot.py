import sqlite3
from telegram import Update, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# --- Database Setup ---
conn = sqlite3.connect("referral_bot.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    username TEXT,
    referral_code TEXT UNIQUE,
    referred_by TEXT,
    balance INTEGER DEFAULT 0
)""")
conn.commit()

# --- Admin Setup ---
ADMIN_IDS = [123456789]  # Replace with your Telegram User ID(s)

# --- Generate Referral Code ---
def generate_referral_code(user_id):
    return f"REF{user_id}"

# --- Helper: Check Admin ---
def is_admin(user_id):
    return user_id in ADMIN_IDS

# --- Start Command Handler ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "Guest"
    referred_by = None
    
    # Extract referral code
    if context.args:
        referred_by = context.args[0]
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    
    if not user:
        referral_code = generate_referral_code(user_id)
        cursor.execute("INSERT INTO users (user_id, username, referral_code, referred_by) VALUES (?, ?, ?, ?)",
                       (user_id, username, referral_code, referred_by))
        conn.commit()
        
        # Update referrer's balance
        if referred_by:
            cursor.execute("UPDATE users SET balance = balance + 10 WHERE referral_code = ?", (referred_by,))
            conn.commit()
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Welcome, {username}! Your referrer earned $10. Share your code to earn more."
            )
        else:
            await context.bot.send_message(
                chat_id=update.effective_chat.id,
                text=f"Welcome, {username}! Your referral code: {referral_code}. Invite friends to earn $10."
            )
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Welcome back, {username}! Your referral code is {user[2]}."
        )

# --- Balance Command ---
async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Your balance is ${user[0]}."
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Use /start to register.")

# --- Referral Command ---
async def referral(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    cursor.execute("SELECT referral_code FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    if user:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f"Your referral code: {user[0]}."
        )
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Use /start to register.")

# --- Admin: View Pending Payouts ---
async def payouts(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Unauthorized access.")
        return

    cursor.execute("SELECT user_id, username, balance FROM users WHERE balance > 0")
    users = cursor.fetchall()
    if users:
        message = "Pending Payouts:\n"
        for u in users:
            message += f"User ID: {u[0]}, Username: {u[1]}, Balance: ${u[2]}\n"
        await context.bot.send_message(chat_id=update.effective_chat.id, text=message)
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="No pending payouts.")

# --- Admin: Process Payment ---
async def pay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Unauthorized access.")
        return
    
    try:
        target_user_id = int(context.args[0])
        cursor.execute("UPDATE users SET balance = 0 WHERE user_id = ?", (target_user_id,))
        conn.commit()
        await context.bot.send_message(chat_id=update.effective_chat.id, text=f"Payout completed for User ID {target_user_id}.")
    except (IndexError, ValueError):
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Usage: /pay [user_id]")

# --- Main Function ---
def main():
    TOKEN = "7787699234:AAGfP_wCmsgFlnUcF_lTP_gnJj0Ojo71uIM"
    app = ApplicationBuilder().token(TOKEN).build()
    
    # Add Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("referral", referral))
    app.add_handler(CommandHandler("payouts", payouts))
    app.add_handler(CommandHandler("pay", pay))
    
    # Set Bot Commands
    app.bot.set_my_commands([
        BotCommand("start", "Start or register with the bot."),
        BotCommand("balance", "Check your balance."),
        BotCommand("referral", "Get your referral code."),
        BotCommand("payouts", "View pending payouts (admin only)."),
        BotCommand("pay", "Mark payout as completed (admin only).")
    ])
    
    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()

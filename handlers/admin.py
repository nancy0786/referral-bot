from telegram import Update
from telegram.ext import ContextTypes
from utils.db import get_user_data, save_user_data
from utils.config import load_config, save_config
import os, time, json

ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

def is_admin(user_id):
    return user_id in ADMIN_IDS

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)
    count = 0
    db_folder = "db"
    for file in os.listdir(db_folder):
        if file.endswith(".json"):
            user_id = int(file.replace(".json", ""))
            try:
                await context.bot.send_message(chat_id=user_id, text=message)
                count += 1
            except:
                pass
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

async def setwelcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /setwelcome <text>")
        return
    config = load_config()
    config["welcome_message"] = " ".join(context.args)
    save_config(config)
    await update.message.reply_text("✅ Welcome message updated.")

async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addcredits <user_id> <amount>")
        return
    user_id = int(context.args[0])
    amount = int(context.args[1])
    data = get_user_data(user_id)
    data["credits"] = data.get("credits", 0) + amount
    save_user_data(user_id, data)
    await update.message.reply_text(f"✅ Added {amount} credits to {user_id}.")

async def setplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /setplan <user_id> <plan_name> <days>")
        return
    user_id = int(context.args[0])
    plan = context.args[1]
    days = int(context.args[2])
    data = get_user_data(user_id)
    data["plan"] = plan
    data["plan_expiry"] = time.time() + days * 86400
    save_user_data(user_id, data)
    await update.message.reply_text(f"✅ Set plan '{plan}' for {user_id} for {days} days.")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    db_folder = "db"
    total_users = len([f for f in os.listdir(db_folder) if f.endswith(".json")])
    await update.message.reply_text(f"📊 Total users: {total_users}")

async def listusers(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    db_folder = "db"
    users = [f.replace(".json", "") for f in os.listdir(db_folder) if f.endswith(".json")]
    await update.message.reply_text("👥 Users:\n" + "\n".join(users))

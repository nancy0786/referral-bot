# handlers/admin.py

import os
import time
import json
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import (
    get_user,
    save_user,
    add_task,
    get_all_tasks,
    delete_task,
    get_video_categories,   # ✅ new
    save_video_categories   # ✅ new
)
from utils.config import load_config, save_config

# Replace with your admin IDs
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ------------------ ADMIN COMMANDS ------------------

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        await update.message.reply_text("Usage: /broadcast <message>")
        return
    message = " ".join(context.args)

    db_folder = "db"
    count = 0
    for file in os.listdir(db_folder):
        if file.endswith(".json"):
            try:
                user_id = int(file.replace(".json", ""))
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

    config_data = load_config()
    config_data["welcome_message"] = " ".join(context.args)
    save_config(config_data)
    await update.message.reply_text("✅ Welcome message updated.")


async def addcredits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 2:
        await update.message.reply_text("Usage: /addcredits <user_id> <amount>")
        return

    try:
        user_id = int(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text("❌ User ID and amount must be numbers.")
        return

    user_data = await get_user(user_id)
    user_data["credits"] = user_data.get("credits", 0) + amount
    await save_user(user_id, user_data)
    await update.message.reply_text(f"✅ Added {amount} credits to user {user_id}.")


async def setplan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if len(context.args) != 3:
        await update.message.reply_text("Usage: /setplan <user_id> <plan_name> <days>")
        return

    try:
        user_id = int(context.args[0])
        plan_name = context.args[1].capitalize()
        days = int(context.args[2])
    except ValueError:
        await update.message.reply_text("❌ Invalid arguments. User ID and days must be numbers.")
        return

    user_data = await get_user(user_id)
    now = int(time.time())
    expiry = now + days * 86400  # days in seconds
    user_data["plan"] = {"name": plan_name, "expires_at": expiry}

    await save_user(user_id, user_data)
    await update.message.reply_text(
        f"✅ Plan '{plan_name}' set for user {user_id} for {days} days."
    )


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


# ------------------ TASK MANAGEMENT ------------------

async def addtask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /addtask {\"title\": \"My Task\", \"link\": \"https://...\", \"reward\": 10}")

    try:
        task_json = " ".join(context.args)
        task = json.loads(task_json)

        if not all(k in task for k in ("title", "link", "reward")):
            return await update.message.reply_text("❌ Task must include title, link, and reward.")

        await add_task(task)  # ✅ now async
        await update.message.reply_text(f"✅ Task added: {task['title']}")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to add task: {e}")


async def viewtasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    tasks = await get_all_tasks()
    if not tasks:
        return await update.message.reply_text("⚠️ No tasks available.")

    message = "📋 Current Tasks:\n\n"
    for i, task in enumerate(tasks, start=1):
        message += f"{i}. {task['title']} (Reward: {task['reward']})\n"
    await update.message.reply_text(message)


async def deletetask(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    if not context.args:
        return await update.message.reply_text("Usage: /deletetask <task_number>")

    try:
        index = int(context.args[0]) - 1
        tasks = await get_all_tasks()
        if 0 <= index < len(tasks):
            removed = tasks[index]
            await delete_task(index)
            await update.message.reply_text(f"🗑️ Task removed: {removed['title']}")
        else:
            await update.message.reply_text("❌ Invalid task number.")
    except ValueError:
        await update.message.reply_text("❌ Task number must be a number.")

# ------------------ VIDEO LIST MANAGEMENT ------------------

async def videolist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command to set or update video categories list."""
    if not is_admin(update.effective_user.id):
        return

    if not context.args:
        # Show current list
        categories = get_video_categories()
        if not categories:
            return await update.message.reply_text("⚠️ No video categories set yet.")
        msg = "📂 Current Video Categories:\n\n"
        for cat, vids in categories.items():
            msg += f"🔹 {cat}: {vids}\n"
        return await update.message.reply_text(msg)

    # Admin provided new list to update
    try:
        categories_json = " ".join(context.args)
        categories = json.loads(categories_json)
        if not isinstance(categories, dict):
            return await update.message.reply_text("❌ Invalid format. Must be a JSON object.")
        save_video_categories(categories)
        await update.message.reply_text("✅ Video categories updated successfully.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to update categories: {e}")

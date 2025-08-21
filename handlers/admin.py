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
    add_or_update_category,
    delete_category,
    get_all_categories
)
from utils.config import load_config, save_config
from utils.db import add_or_update_category, delete_category, get_all_categories, add_redeem_code, get_redeem_code, mark_code_used


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

async def videolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin command: view or update video categories."""
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return await update.message.reply_text("❌ You are not authorized to use this command.")

    if not context.args:
        # Show current categories
        categories = get_all_categories()
        if not categories:
            return await update.message.reply_text("⚠️ No categories found.")

        msg = "📂 Current Video Categories:\n\n"
        for cat, vids in categories:
            msg += f"🔹 {cat}: {vids}\n"
        return await update.message.reply_text(msg)

    # Admin wants to add/update/delete
    action = context.args[0].lower()

    if action == "add" and len(context.args) >= 3:
        category_name = context.args[1]
        video_range = " ".join(context.args[2:])
        add_or_update_category(category_name, video_range)
        return await update.message.reply_text(f"✅ Category '{category_name}' updated with videos {video_range}")

    elif action == "delete" and len(context.args) == 2:
        category_name = context.args[1]
        delete_category(category_name)
        return await update.message.reply_text(f"🗑 Category '{category_name}' deleted.")

    elif action == "json":
        # Admin provides full JSON to update multiple categories at once
        try:
            categories_json = " ".join(context.args[1:])
            categories = json.loads(categories_json)

            if not isinstance(categories, dict):
                return await update.message.reply_text("❌ Invalid format. Must be a JSON object.")

            for cat, vids in categories.items():
                add_or_update_category(cat, vids)

            return await update.message.reply_text("✅ Video categories updated successfully.")
        except Exception as e:
            return await update.message.reply_text(f"❌ Error: {e}")

    else:
        return await update.message.reply_text(
            "❌ Usage:\n\n"
            "/videolist → Show all categories\n"
            "/videolist add <CategoryName> <VideoRange>\n"
            "/videolist delete <CategoryName>\n"
            "/videolist json <JSON_OBJECT>"
        )


# Video list command
async def videolist_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        return await update.message.reply_text("❌ You are not authorized.")

    if not context.args:
        categories = get_all_categories()
        if not categories:
            return await update.message.reply_text("⚠️ No categories found.")
        msg = "📂 Current Video Categories:\n\n"
        for cat, vids in categories:
            msg += f"🔹 {cat}: {vids}\n"
        return await update.message.reply_text(msg)

    action = context.args[0].lower()
    if action == "add" and len(context.args) >= 3:
        category_name = context.args[1]
        video_range = " ".join(context.args[2:])
        add_or_update_category(category_name, video_range)
        return await update.message.reply_text(f"✅ Category '{category_name}' updated with videos {video_range}")
    elif action == "delete" and len(context.args) == 2:
        category_name = context.args[1]
        delete_category(category_name)
        return await update.message.reply_text(f"🗑 Category '{category_name}' deleted.")
    else:
        return await update.message.reply_text("❌ Usage:\n"
                                               "/videolist → Show all categories\n"
                                               "/videolist add <CategoryName> <VideoRange>\n"
                                               "/videolist delete <CategoryName>")



# Add redeem command
async def addredeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):  # uses ENV-defined ADMIN_IDS
        return await update.message.reply_text("❌ You are not authorized.")

    if len(context.args) != 3:
        return await update.message.reply_text(
            "⚙️ Usage:\n"
            "/addredeem <CODE> <CREDITS> <HOURS>\n"
            "Example: /addredeem ABC123 50 24"
        )

    code = context.args[0].upper()
    try:
        credits = int(context.args[1])
        hours = int(context.args[2])
    except ValueError:
        return await update.message.reply_text("❌ Credits and Hours must be integers.")

    add_redeem_code(code, credits, hours)
    await update.message.reply_text(f"✅ Redeem code '{code}' added: {credits} credits, {hours}h premium.")

# handlers/tasks.py

import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from utils.db import get_user_data, save_user_data

# Example tasks
TASKS = [
    {"id": "join_channel", "title": "Join Our Partner Channel", "reward": 2, "type": "telegram_channel", "link": "https://t.me/partner_channel"},
    {"id": "join_group", "title": "Join Our Support Group", "reward": 2, "type": "telegram_group", "link": "https://t.me/partner_group"},
    {"id": "follow_instagram", "title": "Follow Instagram", "reward": 1, "type": "external", "link": "https://instagram.com/example"},
]


# Build keyboard dynamically
def build_task_keyboard(user_id):
    user_data = get_user_data(user_id)
    completed = user_data.get("tasks_completed", [])

    keyboard = []
    for task in TASKS:
        if task["id"] in completed:
            # Already completed
            keyboard.append([InlineKeyboardButton(f"✅ {task['title']} (Completed)", callback_data="done")])
        else:
            # Show only link initially
            keyboard.append([InlineKeyboardButton(f"🔗 {task['title']}", callback_data=f"open_{task['id']}")])
    return InlineKeyboardMarkup(keyboard)


# Show tasks
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    markup = build_task_keyboard(user_id)

    if update.message:
        await update.message.reply_text("📋 Complete tasks to earn rewards:", reply_markup=markup)
    else:
        await update.callback_query.edit_message_text("📋 Complete tasks to earn rewards:", reply_markup=markup)


# Handle "Open Link" click
async def handle_open_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    task_id = query.data.replace("open_", "")
    task = next((t for t in TASKS if t["id"] == task_id), None)

    if not task:
        await query.answer("⚠️ Task not found!", show_alert=True)
        return

    # Send the link
    await query.answer()
    await query.message.reply_text(f"🔗 Open this task: {task['title']}\n{task['link']}")

    # Wait 3 seconds then show Done button for THIS task
    await asyncio.sleep(3)

    user_data = get_user_data(user_id)
    completed = user_data.get("tasks_completed", [])

    keyboard = []
    for t in TASKS:
        if t["id"] in completed:
            keyboard.append([InlineKeyboardButton(f"✅ {t['title']} (Completed)", callback_data="done")])
        elif t["id"] == task_id:
            keyboard.append([InlineKeyboardButton(f"✅ Done (+{t['reward']} credits)", callback_data=f"task_done_{task_id}")])
        else:
            keyboard.append([InlineKeyboardButton(f"🔗 {t['title']}", callback_data=f"open_{t['id']}")])

    await query.message.edit_text("📋 Complete tasks to earn rewards:", reply_markup=InlineKeyboardMarkup(keyboard))


# Handle "Done" click
async def handle_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    task_id = query.data.replace("task_done_", "")

    user_data = get_user_data(user_id)

    if task_id in user_data.get("tasks_completed", []):
        await query.answer("✅ You already completed this task!", show_alert=True)
        return

    task = next((t for t in TASKS if t["id"] == task_id), None)
    if not task:
        await query.answer("⚠️ Task not found!", show_alert=True)
        return

    # Add credits
    user_data["credits"] += task["reward"]
    user_data["tasks_completed"].append(task_id)
    save_user_data(user_id, user_data)

    await query.answer(f"🎉 Task completed! +{task['reward']} credits", show_alert=True)

    # Refresh keyboard
    markup = build_task_keyboard(user_id)
    await query.message.edit_text("📋 Complete tasks to earn rewards:", reply_markup=markup)

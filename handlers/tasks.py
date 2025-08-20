# handlers/tasks.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.db import get_all_tasks, mark_task_completed, get_user

logger = logging.getLogger(__name__)

# ========================
# USER COMMAND: /tasks
# ========================
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tasks to the user."""
    user_id = str(update.effective_user.id)
    tasks = await get_all_tasks()
    user = await get_user(user_id)

    if not tasks:
        await update.message.reply_text("✅ No active tasks available right now.")
        return

    buttons = []
    for idx, task in enumerate(tasks, start=1):
        # Check if user already completed
        if task["id"] in user.get("tasks_completed", []):
            buttons.append([
                InlineKeyboardButton(f"✅ {task['title']} (Completed)", callback_data="done")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(f"🔗 {task['title']}", callback_data=f"open_{idx}"),
                InlineKeyboardButton(f"✅ Done (+{task['reward']} credits)", callback_data=f"task_done_{idx}")
            ])

    await update.message.reply_text(
        "📋 Here are your available tasks:",
        reply_markup=InlineKeyboardMarkup(buttons)
    )

# ========================
# BUTTON HANDLERS
# ========================
async def handle_open_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user clicks 'open link'."""
    query = update.callback_query
    await query.answer()

    idx = int(query.data.split("_")[1])
    tasks = await get_all_tasks()

    if idx <= 0 or idx > len(tasks):
        await query.edit_message_text("⚠️ Invalid task.")
        return

    task = tasks[idx - 1]
    await query.message.reply_text(
        f"🔗 Task: {task['title']}\n\n"
        f"👉 {task['link']}"
    )

async def handle_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user clicks 'Done' button."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    idx = int(query.data.split("_")[2])
    tasks = await get_all_tasks()

    if idx <= 0 or idx > len(tasks):
        await query.edit_message_text("⚠️ Invalid task.")
        return

    task = tasks[idx - 1]
    user = await get_user(user_id)

    # Already completed?
    if task["id"] in user.get("tasks_completed", []):
        await query.answer("✅ You already completed this task!", show_alert=True)
        return

    # Mark task as completed
    await mark_task_completed(user_id, task["id"])

    # Add credits
    user["credits"] += task["reward"]
    await context.application.bot.send_message(
        chat_id=user_id,
        text=f"🎉 Task *{task['title']}* completed! +{task['reward']} credits"
    )

    # Refresh tasks list
    await show_tasks(update, context)

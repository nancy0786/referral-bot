# handlers/tasks.py
import logging
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.db import get_tasks, complete_task, add_user_task_progress

logger = logging.getLogger(__name__)

# ========================
# USER COMMAND: /tasks
# ========================
async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show available tasks to the user."""
    user_id = str(update.effective_user.id)
    tasks = get_tasks()

    if not tasks:
        await update.message.reply_text("✅ No active tasks available right now.")
        return

    buttons = []
    for idx, task in enumerate(tasks, start=1):
        buttons.append([
            InlineKeyboardButton(f"🔗 {task['title']}", callback_data=f"open_{idx}"),
            InlineKeyboardButton("✅ Done", callback_data=f"task_done_{idx}")
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
    tasks = get_tasks()

    if idx <= 0 or idx > len(tasks):
        await query.edit_message_text("⚠️ Invalid task.")
        return

    task = tasks[idx - 1]
    await query.edit_message_text(
        f"🔗 Task: {task['title']}\n\n"
        f"👉 [Click here to open link]({task['link']})",
        parse_mode="Markdown",
        disable_web_page_preview=True
    )

async def handle_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle when user clicks 'Done' button."""
    query = update.callback_query
    await query.answer()

    user_id = str(query.from_user.id)
    idx = int(query.data.split("_")[2])
    tasks = get_tasks()

    if idx <= 0 or idx > len(tasks):
        await query.edit_message_text("⚠️ Invalid task.")
        return

    task = tasks[idx - 1]

    # Mark task as complete for this user
    complete_task(user_id, task["title"])
    add_user_task_progress(user_id, task["title"])

    await query.edit_message_text(
        f"✅ Task *{task['title']}* marked as completed!",
        parse_mode="Markdown"
    )

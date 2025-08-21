# handlers/tasks.py
import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
from utils.db import (
    get_all_tasks,
    get_user,
    save_user,
    mark_task_opened,
    mark_task_completed
)

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
        if update.message:
            await update.message.reply_text("✅ No active tasks available right now.")
        elif update.callback_query:
            await update.callback_query.edit_message_text("✅ No active tasks available right now.")
        return

    buttons = []
    for idx, task in enumerate(tasks, start=1):
        # Already completed
        if str(task["id"]) in user.get("tasks_completed", []):
            buttons.append([
                InlineKeyboardButton(f"✅ {task['title']} (Completed)", callback_data="done")
            ])
        else:
            buttons.append([
                InlineKeyboardButton(f"🔗 {task['title']}", callback_data=f"open_{idx}"),
                InlineKeyboardButton(f"✅ Done (+{task['reward']} credits)", callback_data=f"task_done_{idx}")
            ])

    if update.message:
        await update.message.reply_text(
            "📋 Here are your available tasks:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
    elif update.callback_query:
        await update.callback_query.edit_message_text(
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
    user_id = str(query.from_user.id)

    # Mark as opened
    await mark_task_opened(user_id, str(task["id"]))

    # Send task link
    await query.message.reply_text(
        f"🔗 Task: {task['title']}\n\n👉 {task['link']}\n\n"
        "⏳ Please wait 5 seconds before you can click Done..."
    )

    # Wait 5 seconds before enabling Done
    await asyncio.sleep(5)
    await query.message.reply_text(
        f"✅ Now you can mark *{task['title']}* as Done.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(f"✅ Done (+{task['reward']} credits)", callback_data=f"task_done_{idx}")]
        ])
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

    # Try marking completed
    success, msg = await mark_task_completed(user_id, str(task["id"]), task["reward"])

    if not success:
        # Show alert if failed (not opened, too fast, already completed)
        await query.answer(msg, show_alert=True)
        return

    # ✅ Success → Send a beautiful confirmation
    await context.application.bot.send_message(
        chat_id=user_id,
        text=msg,  # 🎉 Task completed! +X credits
        parse_mode="Markdown"
    )

    # Refresh tasks list
    await show_tasks(update, context)

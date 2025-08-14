TASKS = [
    {"id": "join_channel", "title": "Join Our Partner Channel", "reward": 2, "type": "telegram_channel", "link": "https://t.me/partner_channel"},
    {"id": "follow_instagram", "title": "Follow Our Instagram", "reward": 1, "type": "external", "link": "https://instagram.com/example"},
    {"id": "visit_site", "title": "Visit Our Website", "reward": 1, "type": "external", "link": "https://example.com"}
]

async def show_tasks(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for task in TASKS:
        keyboard.append([InlineKeyboardButton(task["title"], url=task["link"])])
        keyboard.append([InlineKeyboardButton(f"✅ Done ({task['reward']} credits)", callback_data=f"task_done_{task['id']}")])
    await update.callback_query.edit_message_text(
        "📋 Complete tasks to earn rewards:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_task_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    task_id = update.callback_query.data.replace("task_done_", "")
    user_data = get_user_data(user_id)

    if task_id in user_data.get("tasks_completed", []):
        await update.callback_query.answer("You already completed this task!", show_alert=True)
        return

    task = next((t for t in TASKS if t["id"] == task_id), None)
    if not task:
        await update.callback_query.answer("Task not found!", show_alert=True)
        return

    user_data["credits"] += task["reward"]
    user_data["tasks_completed"].append(task_id)
    save_user_data(user_id, user_data)

    await update.callback_query.answer(f"🎉 Task completed! +{task['reward']} credits", show_alert=True)
    await show_tasks(update, context)

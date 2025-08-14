from utils.db import get_user_data
from telegram import Update
from telegram.ext import ContextTypes

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    name = user_data.get("name", update.effective_user.first_name)
    plan = user_data.get("plan", "free").capitalize()
    credits = user_data.get("credits", 0)
    expiry = user_data.get("plan_expiry", "N/A")
    verified = "✅ Verified" if user_data.get("sponsor_verified", False) else "❌ Not Verified"
    tasks_done = len(user_data.get("tasks_completed", []))
    badges = ", ".join(user_data.get("badges", [])) or "None"

    msg = (
        f"👤 **Profile**\n"
        f"• Name: {name}\n"
        f"• Telegram ID: `{user_id}`\n"
        f"• Plan: {plan}\n"
        f"• Credits: {credits}\n"
        f"• Plan Expiry: {expiry}\n"
        f"• Sponsor Status: {verified}\n"
        f"• Tasks Completed: {tasks_done}\n"
        f"• Badges: {badges}"
    )

    await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

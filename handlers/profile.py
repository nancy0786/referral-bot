# handlers/profile.py
from utils.db import get_user_data
from telegram import Update
from telegram.ext import ContextTypes

async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await get_user_data(user_id) or {}  # ✅ Prevent None errors

    # Basic details
    name = user_data.get("name") or update.effective_user.first_name
    username = f"@{update.effective_user.username}" if update.effective_user.username else "N/A"
    plan = user_data.get("plan", "free").capitalize()
    credits = user_data.get("credits", 0)   # ✅ includes tasks, rewards, giveaways, redeem
    expiry = user_data.get("plan_expiry", "N/A")
    verified = "✅ Verified" if user_data.get("sponsor_verified", False) else "❌ Not Verified"

    # Progress
    tasks_done = len(user_data.get("tasks_completed", []))  # ✅ only direct task completions
    badges = ", ".join(user_data.get("badges", [])) or "None"

    # Referral
    ref_count = user_data.get("referrals", 0)
    ref_link = user_data.get("ref_link", "Not generated yet")

    msg = (
        f"👤 **Your Profile**\n\n"
        f"• Name: {name}\n"
        f"• Username: {username}\n"
        f"• Telegram ID: `{user_id}`\n"
        f"• Plan: {plan}\n"
        f"• Credits (All Sources): {credits}\n"   # ✅ shows total credits
        f"• Plan Expiry: {expiry}\n"
        f"• Sponsor Status: {verified}\n\n"
        f"📋 **Progress**\n"
        f"• Tasks Completed: {tasks_done}\n"
        f"• Badges: {badges}\n\n"
        f"👥 **Referrals**\n"
        f"• Total Referrals: {ref_count}\n"
        f"• Referral Link: {ref_link}"
    )

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

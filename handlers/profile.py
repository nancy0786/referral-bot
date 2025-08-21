# handlers/profile.py
from utils.db import get_user_data
from telegram import Update
from telegram.ext import ContextTypes
from utils.checks import ensure_access

async def some_command(update, context):
    if not await ensure_access(update, context):
        return  # stop execution until user completes requirements
    
    # normal command code here
async def show_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = await get_user_data(user_id) or {}  # ✅ Prevent None errors

    # Basic details
    name = user_data.get("name") or update.effective_user.first_name
    username = f"@{update.effective_user.username}" if update.effective_user.username else "N/A"
    plan = user_data.get("plan", "free")
    # plan might be dict name or a string - normalize for display
    if isinstance(plan, dict):
        plan_name = plan.get("name", "Free")
    else:
        plan_name = str(plan).capitalize()

    credits = user_data.get("credits", 0)   # ✅ includes tasks, rewards, giveaways, redeem
    expiry = user_data.get("plan_expiry", "N/A")
    verified = "✅ Verified" if user_data.get("sponsor_verified", False) else "❌ Not Verified"

    # Progress
    tasks_done = len(user_data.get("tasks_completed", []))  # ✅ real completed tasks
    badges = ", ".join(user_data.get("badges", [])) or "None"

    # Referrals (✅ handle total, successful, pending properly)
    referrals = user_data.get("referrals", {})
    if isinstance(referrals, dict):
        ref_total = referrals.get("total", 0)
        ref_success = referrals.get("successful", 0)

        pending_val = referrals.get("pending", 0)
        if isinstance(pending_val, int):
            ref_pending = pending_val
        elif isinstance(pending_val, list):
            ref_pending = len(pending_val)
        else:
            ref_pending = 0
    else:
        # fallback for old format
        ref_total, ref_success, ref_pending = 0, 0, 0

    ref_link = user_data.get("ref_link", "Not generated yet")

    msg = (
        f"👤 **Your Profile**\n\n"
        f"• Name: {name}\n"
        f"• Username: {username}\n"
        f"• Telegram ID: `{user_id}`\n"
        f"• Plan: {plan_name}\n"
        f"• Credits (All Sources): {credits}\n"
        f"• Plan Expiry: {expiry}\n"
        f"• Sponsor Status: {verified}\n\n"
        f"📋 **Progress**\n"
        f"• Tasks Completed: {tasks_done}\n"
        f"• Badges: {badges}\n\n"
        f"👥 **Referrals**\n"
        f"• Total Referrals: {ref_total}\n"
        f"• Successful Referrals: {ref_success}\n"
        f"• Pending Referrals: {ref_pending}\n"
        f"• Referral Link: {ref_link}"
    )

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

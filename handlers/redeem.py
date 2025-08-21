# handlers/redeem.py
import time
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import get_user, save_user
from utils.codes import get_code_info, mark_code_used
from utils.checks import ensure_access

async def some_command(update, context):
    if not await ensure_access(update, context):
        return  # stop execution until user completes requirements
    
    # normal command code here
AWAIT_FLAG = "awaiting_redeem_code"

REDEEM_INSTRUCTIONS = (
    "🎁 **Redeem Code**\n\n"
    "Please send your 16-character code (A–Z and 0–9 only).\n"
    "Example: `AB12CD34EF56GH78`\n\n"
    "_Send the code now, or type /cancel._"
)

async def start_redeem_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    context.user_data[AWAIT_FLAG] = True
    await query.answer()
    await query.edit_message_text(REDEEM_INSTRUCTIONS, parse_mode="Markdown")

async def start_redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data[AWAIT_FLAG] = True
    await update.message.reply_text(REDEEM_INSTRUCTIONS, parse_mode="Markdown")

async def handle_redeem_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles user text ONLY when awaiting redeem code."""
    if not context.user_data.get(AWAIT_FLAG):
        return  # ignore normal text

    code = (update.message.text or "").strip().upper()

    info = await get_code_info(code)
    if not info:
        await update.message.reply_text("❌ Invalid code format or code not found.\nPlease check and try again.")
        return

    if info.get("used_by"):
        await update.message.reply_text("⚠️ This code has already been used.")
        return

    # Apply reward
    user_id = update.effective_user.id
    profile = await get_user(user_id, username=update.effective_user.username)
    reward = info.get("reward", {})

    applied_msg = None

    # Credits reward
    if "credits" in reward and isinstance(reward["credits"], int):
        profile["credits"] = int(profile.get("credits", 0)) + int(reward["credits"])
        applied_msg = f"✅ Redeemed! +{reward['credits']} credits added to your balance."

    # Plan reward
    plan_obj = reward.get("plan")
    if isinstance(plan_obj, dict):
        name = str(plan_obj.get("name", "Premium"))
        days = int(plan_obj.get("days", 30))
        now = int(time.time())

        # If existing plan not expired, extend; else set new expiry from now
        current = profile.get("plan", {"name": "Free", "expires_at": None})
        expires_at = current.get("expires_at")
        base_time = now if not expires_at or expires_at < now else int(expires_at)
        new_expiry = base_time + days * 24 * 60 * 60

        profile["plan"] = {"name": name, "expires_at": new_expiry}

        human_days = "day" if days == 1 else "days"
        plan_line = f"✅ Plan activated: {name} for {days} {human_days}."
        applied_msg = f"{applied_msg+'\n' if applied_msg else ''}{plan_line}"

    if not applied_msg:
        await update.message.reply_text("❌ This code has no valid reward attached. Contact support.")
        return

    # Save user and mark code used
    await save_user(user_id, profile)
    await mark_code_used(code, user_id)

    # Done
    context.user_data[AWAIT_FLAG] = False
    await update.message.reply_text(applied_msg)

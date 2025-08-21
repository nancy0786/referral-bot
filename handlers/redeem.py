# handlers/redeem.py
import re
import time
import json
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import get_user, save_user, get_redeem_code, mark_code_used
from utils.checks import ensure_access

# -----------------------------
# Constants
# -----------------------------
AWAIT_FLAG = "awaiting_redeem_code"

REDEEM_INSTRUCTIONS = (
    "🎁 **Redeem Code**\n\n"
    "Please send your 16-character code (A–Z and 0–9 only).\n"
    "Example: `AB12CD34EF56GH78`\n\n"
    "_Send the code now, or type /cancel._"
)

# -----------------------------
# Start Redeem Commands
# -----------------------------
async def start_redeem_from_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger redeem via inline menu."""
    query = update.callback_query
    context.user_data[AWAIT_FLAG] = True
    await query.answer()
    await query.edit_message_text(REDEEM_INSTRUCTIONS, parse_mode="Markdown")

async def start_redeem_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Trigger redeem via /redeem command."""
    context.user_data[AWAIT_FLAG] = True
    await update.message.reply_text(REDEEM_INSTRUCTIONS, parse_mode="Markdown")

# -----------------------------
# Handle Redeem Text
# -----------------------------
async def handle_redeem_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle user input for redeem code."""
    if not context.user_data.get(AWAIT_FLAG):
        return  # normal text, not redeem code

    code = (update.message.text or "").strip().upper()

    # Validate code format
    if not re.match(r"^[A-Z0-9]{16}$", code):
        return await update.message.reply_text(
            "❌ Invalid code format. Must be 16 characters A–Z or 0–9."
        )

    # Fetch code info from DB
    info = get_redeem_code(code)
    if not info:
        return await update.message.reply_text("❌ Code not found or invalid.")

    user_id = update.effective_user.id
    used_by = info[3].split(",") if info[3] else []
    if str(user_id) in used_by:
        return await update.message.reply_text("⚠️ You have already used this code.")

    # Fetch user profile
    profile = await get_user(user_id, username=update.effective_user.username)

    # Apply credits
    profile["credits"] = profile.get("credits", 0) + info[1]

    # Apply premium duration
    if info[2] > 0:
        now = int(time.time())
        expiry = max(profile.get("plan_expiry", now), now)
        expiry += info[2] * 3600  # hours -> seconds
        profile["plan"] = "premium"
        profile["plan_expiry"] = expiry

    # Save user and mark code as used
    await save_user(user_id, profile)
    mark_code_used(code, user_id)

    # Clear await flag
    context.user_data[AWAIT_FLAG] = False

    # Success message
    await update.message.reply_text(
        f"🎉 Redeemed successfully!\n"
        f"✅ Credits: +{info[1]}\n"
        f"✅ Premium: +{info[2]} hour(s)"
    )

# -----------------------------
# Optional: /cancel command for users
# -----------------------------
async def cancel_redeem(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Cancel redeem process."""
    if context.user_data.get(AWAIT_FLAG):
        context.user_data[AWAIT_FLAG] = False
        await update.message.reply_text("❌ Redeem process cancelled.")

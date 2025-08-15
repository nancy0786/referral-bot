# handlers/start.py

import os
import datetime
import config
from telegram import Update
from telegram.ext import ContextTypes
from handlers.force_join import is_member, prompt_join
from handlers.sponsor_verify import ask_sponsor_verification, auto_verify_sponsor
from handlers.menu import send_main_menu
from utils.db import (
    get_user,
    save_user,
    set_invited_by,
    add_pending_referral,
    get_user_data,
    save_user_data
)

# Constants
REFERRAL_CREDIT = 2
BADGE_LEVELS = {
    1: "Referrer Lv1",
    5: "Referrer Lv2",
    10: "Referrer Lv3"
}

# ------------------------------------------------------------
# Helper Functions
# ------------------------------------------------------------

def load_welcome_text() -> str:
    """Load welcome message from file if available, otherwise default."""
    if os.path.exists(config.WELCOME_FILE):
        with open(config.WELCOME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "👋 Welcome!"

async def log_new_user(
    context: ContextTypes.DEFAULT_TYPE,
    user: Update.effective_user,
    ref: str
):
    """Send new user log to log channel."""
    if config.LOG_CHANNEL_ID != 0:
        text = (
            "📥 **New User Started Bot**\n"
            f"👤 Name: {user.full_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🔗 Username: @{user.username if user.username else 'None'}\n"
            f"👥 Referral: `{ref if ref else 'None'}`\n"
            f"⏰ Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await context.bot.send_message(
            config.LOG_CHANNEL_ID,
            text,
            parse_mode="Markdown"
        )

# ------------------------------------------------------------
# Main Start Command
# ------------------------------------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username
    ref_code = None

    # Load or create user profile
    profile = await get_user(user_id, username=username)

    # --------------------------------------------------------
    # Handle referral from /start <ref_id>
    # --------------------------------------------------------
    if context.args:
        ref = context.args[0]
        if ref.isdigit():
            ref_id = int(ref)
            ref_code = ref
            # New referral linking
            if ref_id != user_id and profile["referrals"].get("invited_by") is None:
                await set_invited_by(user_id, ref_id)
                await add_pending_referral(ref_id, user_id)

            # Referral credit and badge logic
            if ref_id != user_id:
                ref_data = get_user_data(ref_id)
                if user_id not in ref_data.get("referrals", []):
                    ref_data.setdefault("referrals", []).append(user_id)
                    ref_data["credits"] = ref_data.get("credits", 0) + REFERRAL_CREDIT

                    total_refs = len(ref_data["referrals"])
                    if total_refs in BADGE_LEVELS:
                        badge = BADGE_LEVELS[total_refs]
                        if badge not in ref_data.get("badges", []):
                            ref_data.setdefault("badges", []).append(badge)

                    save_user_data(ref_id, ref_data)

    # --------------------------------------------------------
    # Force Join Check
    # --------------------------------------------------------
    if not await is_member(context, user_id):
        await prompt_join(update, context)
        await log_new_user(context, user, ref_code)
        return

    # --------------------------------------------------------
    # Sponsor Verification Check
    # --------------------------------------------------------
    if not profile.get("sponsor_verified", False):
        verified = await check_sponsor_message(user_id, context)
        if verified:
            profile["sponsor_verified"] = True
            await save_user(user_id, profile)
        else:
            await ask_sponsor_verification(update, context)
            await log_new_user(context, user, ref_code)
            return
    # --------------------------------------------------------
    # Save profile to DB and backup channel
    # --------------------------------------------------------
    await save_user(user_id, profile, backup_sync=True)

    # --------------------------------------------------------
    # Send Welcome Message
    # --------------------------------------------------------
    welcome_msg = load_welcome_text()
    await update.message.reply_text(welcome_msg)

    # --------------------------------------------------------
    # Send Main Menu
    # --------------------------------------------------------
    await send_main_menu(update, context)

    # --------------------------------------------------------
    # Log New User
    # --------------------------------------------------------
    await log_new_user(context, user, ref_code)

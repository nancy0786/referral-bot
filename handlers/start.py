# handlers/start.py

import os
import datetime
import config
from telegram import Update
from telegram.ext import ContextTypes
from handlers.force_join import is_member, prompt_join
from handlers.sponsor_verify import ask_sponsor_verification, auto_verify_sponsor
from handlers.menu import send_main_menu
from utils.db import json_get_user as get_user, json_save_user as save_user, set_invited_by, add_pending_referral

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
    if os.path.exists(config.WELCOME_FILE):
        with open(config.WELCOME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return (
        "✨ ʜᴇʏ, {user_name} ✨\n\n"
        "🤖 ɪ'ᴍ ʏᴏᴜʀ ᴘᴇʀꜱᴏɴᴀʟ ʙᴏᴛ\n"
        "━━━━━━━━━━━━━━━⧫\n"
        "◆ 📌 Complete tasks ➝ Earn rewards\n"
        "◆ 🎁 Redeem codes ➝ Get bonus\n"
        "◆ 👥 Refer friends ➝ Claim extra credits\n"
        "◆ 📊 Profile & stats\n"
        "━━━━━━━━━━━━━━━⧫\n"
        "⚡ Use the buttons below to explore!"
    )

async def log_new_user(context: ContextTypes.DEFAULT_TYPE, user, ref: str):
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
    profile = await get_user(user_id)
    if profile is None:
        profile = {
            "id": user_id,
            "username": username,
            "sponsor_verified": False,
            "credits": 0,
            "badges": [],
            "referrals": {
                "invited_by": None,
                "pending": [],
                "completed": []
            }
        }
        await save_user(user_id, profile)

    # --------------------------------------------------------
    # Handle referral from /start <ref_id>
    # --------------------------------------------------------
    if context.args:
        ref = context.args[0]
        if ref.isdigit():
            ref_id = int(ref)
            ref_code = ref
            if ref_id != user_id and profile["referrals"].get("invited_by") is None:
                await set_invited_by(user_id, ref_id)
                await add_pending_referral(ref_id, user_id)

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
        verified = await auto_verify_sponsor(user_id, context)
        if verified:
            profile["sponsor_verified"] = True
            await save_user(user_id, profile)

            # ✅ Referral completion & credits
            if profile["referrals"].get("invited_by"):
                ref_id = profile["referrals"]["invited_by"]
                ref_profile = await get_user(ref_id)

                if ref_profile and user_id in ref_profile.get("referrals", {}).get("pending", []):
                    ref_profile["referrals"]["pending"].remove(user_id)
                    ref_profile.setdefault("referrals", {}).setdefault("completed", []).append(user_id)

                    # Add credits
                    ref_profile["credits"] = ref_profile.get("credits", 0) + REFERRAL_CREDIT

                    # Badge system
                    total_refs = len(ref_profile["referrals"].get("completed", []))
                    if total_refs in BADGE_LEVELS:
                        badge = BADGE_LEVELS[total_refs]
                        if badge not in ref_profile.get("badges", []):
                            ref_profile.setdefault("badges", []).append(badge)

                    await save_user(ref_id, ref_profile)

    # --------------------------------------------------------
    # Send Main Menu
    # --------------------------------------------------------
    await send_main_menu(update, context)
    await log_new_user(context, user, ref_code)

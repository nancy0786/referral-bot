# handlers/sponsor_verify.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import config
from utils.db import json_get_user as get_user, json_save_user as save_user

VERIFY_AWAIT_KEY = "awaiting_sponsor_verify"

async def ask_sponsor_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ask user to verify automatically via Sponsor Bot.
    Shows a button linking to the Sponsor Bot.
    """
    context.user_data[VERIFY_AWAIT_KEY] = True

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Verify with Sponsor Bot", url=f"https://t.me/{config.SPONSOR_BOT_USERNAME.lstrip('@')}")]
    ])

    msg = (
        f"📢 **Sponsor Verification Required**\n\n"
        f"Click the button below to verify with our sponsor bot {config.SPONSOR_BOT_USERNAME}.\n\n"
        "Once verified, you will get full access to all commands!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


async def auto_verify_sponsor(user_id: int, context: ContextTypes.DEFAULT_TYPE = None) -> bool:
    """
    Automatically verify user via Sponsor Bot.
    Returns True if verified, False otherwise.
    Accepts user_id directly (no Update required).
    """
    sponsor_verified = False

    # -------------------------
    # Placeholder: actual Sponsor Bot verification logic goes here
    # e.g., check Sponsor Bot API, DB flag, shared channel message
    # sponsor_verified = check_sponsor_api(user_id)
    # -------------------------

    if sponsor_verified:
        profile = await get_user(user_id)
        if profile:
            profile["sponsor_verified"] = True
            await save_user(user_id, profile)

        # Optional: send message if context is provided
        if context:
            try:
                await context.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "🎉 **Congratulations!**\n\n"
                        "You have been successfully **verified by our Sponsor Bot**.\n"
                        "✨ You now have full access to all commands and rewards!\n\n"
                        "💡 Tip: Explore /menu to see your tasks and plans."
                    ),
                    parse_mode="Markdown"
                )
            except Exception:
                pass

        return True

    return False


# -----------------------------
# Handle forwarded messages
# -----------------------------
async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handles forwarded messages for sponsor verification.
    Marks the user as verified if forward detected.
    """
    user = update.effective_user
    user_id = user.id
    profile = await get_user(user_id)

    if not profile.get("sponsor_verified", False):
        profile["sponsor_verified"] = True
        await save_user(user_id, profile)
        await update.message.reply_text(
            "✅ Sponsor verification successful via forwarded message!"
        )

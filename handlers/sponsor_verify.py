# handlers/sponsor_verify.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import config
from utils.db import get_user, save_user

VERIFY_AWAIT_KEY = "awaiting_sponsor_verify"

async def ask_sponsor_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ask user to verify automatically via Sponsor Bot.
    Shows a button linking to the Sponsor Bot.
    """
    # Set flag for user_data (optional for tracking)
    context.user_data[VERIFY_AWAIT_KEY] = True

    # Inline button to open Sponsor Bot
    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Verify with Sponsor Bot", url=f"https://t.me/{config.SPONSOR_BOT_USERNAME.lstrip('@')}")]
    ])

    msg = (
        f"📢 **Sponsor Verification Required**\n\n"
        f"Click the button below to verify with our sponsor bot {config.SPONSOR_BOT_USERNAME}.\n\n"
        "Once verified, you will get full access to all commands!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)

async def auto_verify_sponsor(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Automatically verify user via Sponsor Bot.
    Returns True if verified, False otherwise.
    (Replace the placeholder logic with your Sponsor Bot API or shared mechanism.)
    """
    user_id = update.effective_user.id
    sponsor_verified = False

    # -------------------------
    # Placeholder for actual Sponsor Bot verification
    # -------------------------
    try:
        # Example: call Sponsor Bot API, check DB, or shared channel messages
        # sponsor_verified = check_sponsor_api(user_id)
        pass
    except Exception:
        sponsor_verified = False

    if sponsor_verified:
        # Update user profile
        profile = await get_user(user_id)
        profile["sponsor_verified"] = True
        await save_user(user_id, profile)

        # Send amazing verification message
        msg = (
            "🎉 **Congratulations!**\n\n"
            "You have been successfully **verified by our Sponsor Bot**.\n"
            "✨ You now have full access to all commands and rewards!\n\n"
            "💡 Tip: Explore /menu to see your tasks and plans."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return True

    return False

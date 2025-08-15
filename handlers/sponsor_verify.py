from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import config
from utils.db import get_user, save_user

VERIFY_AWAIT_KEY = "awaiting_sponsor_verify"

async def ask_sponsor_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to verify automatically via sponsor bot."""
    # Set flag for user_data (optional for tracking)
    context.user_data[VERIFY_AWAIT_KEY] = True

    # Message with inline button to sponsor bot
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
    Automatically verify user from Sponsor Bot.
    Requires Sponsor Bot API or shared channel mechanism.
    Returns True if verified.
    """
    user_id = update.effective_user.id

    # ---- Replace this block with actual Sponsor Bot verification logic ----
    sponsor_verified = False
    try:
        # Example: check sponsor DB, channel membership, or API
        # sponsor_verified = check_sponsor_api(user_id)
        pass
    except Exception:
        sponsor_verified = False

    if sponsor_verified:
        profile = await get_user(user_id)
        profile["sponsor_verified"] = True
        await save_user(user_id, profile)

        # Amazing verification message
        msg = (
            "🎉 **Congratulations!**\n\n"
            "You have been successfully **verified by our Sponsor Bot**.\n"
            "✨ You now have full access to all commands and rewards!\n\n"
            "💡 Tip: Explore /menu to see your tasks and plans."
        )
        await update.message.reply_text(msg, parse_mode="Markdown")
        return True

    return False

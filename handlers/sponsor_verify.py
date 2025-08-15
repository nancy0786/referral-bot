from telegram import Update
from telegram.ext import ContextTypes
import config
from utils.db import get_user, save_user

VERIFY_AWAIT_KEY = "awaiting_sponsor_verify"

async def ask_sponsor_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Ask user to forward a message from sponsor bot."""
    context.user_data[VERIFY_AWAIT_KEY] = True
    msg = (
        f"📢 **Sponsor Verification Required**\n\n"
        f"Please forward *any* message from our sponsor bot {config.SPONSOR_BOT_USERNAME} "
        "to this chat so we can verify you.\n\n"
        "Once verified, you can continue."
    )
    await update.message.reply_text(msg, parse_mode="Markdown")

async def handle_forward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check forwarded message to verify sponsor bot usage."""
    if not context.user_data.get(VERIFY_AWAIT_KEY):
        return  # not in verification mode

    fwd = update.message.forward_from
    if not fwd:
        await update.message.reply_text("❌ This is not a forwarded message. Please forward from sponsor bot.")
        return

    if fwd.id == config.SPONSOR_BOT_ID:
        profile = await get_user(update.effective_user.id)
        profile["sponsor_verified"] = True
        await save_user(update.effective_user.id, profile)
        context.user_data[VERIFY_AWAIT_KEY] = False
        await update.message.reply_text("✅ Sponsor verification successful! You may now continue.")
        # Here we can send them to main menu in Step 3 later
    else:
        await update.message.reply_text("❌ This message is not from our sponsor bot. Please try again.")

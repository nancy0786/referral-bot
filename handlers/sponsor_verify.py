# handlers/sponsor_verify.py

from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ContextTypes
import config
from utils.db import json_get_user as get_user, json_save_user as save_user

VERIFY_AWAIT_KEY = "awaiting_sponsor_verify"

# ---------------------------
# Step 1: Ask user to verify
# ---------------------------
async def ask_sponsor_verification(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Ask user to verify with Sponsor Bot.
    Shows a button linking to the Sponsor Bot where they can request their code.
    """
    context.user_data[VERIFY_AWAIT_KEY] = True

    kb = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Verify with Sponsor Bot", url=f"https://t.me/{config.SPONSOR_BOT_USERNAME.lstrip('@')}?start=getcode")]
    ])

    msg = (
        "📢 **Sponsor Verification Required**\n\n"
        f"Click the button below to talk to our sponsor bot {config.SPONSOR_BOT_USERNAME}.\n\n"
        "➡️ Type `/getcode` in the sponsor bot.\n"
        "➡️ It will give you a unique verification code.\n"
        "➡️ Come back here and send `/verify CODE` to complete verification.\n\n"
        "Once verified, you will get full access!"
    )

    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb)


# ---------------------------
# Step 2: Verify with code
# ---------------------------
async def verify_with_code(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    User runs /verify CODE in the main bot.
    Checks against sponsor bot DB and marks user verified.
    """
    user = update.effective_user
    user_id = user.id

    if not context.args:
        await update.message.reply_text("⚠️ Usage: /verify CODE")
        return

    code = context.args[0].strip()

    # Load sponsor profile (same DB)
    sponsor_profile = await get_user(user_id)

    if sponsor_profile and sponsor_profile.get("verify_code") == code:
        sponsor_profile["sponsor_verified"] = True
        await save_user(user_id, sponsor_profile)

        await update.message.reply_text(
            "✅ Congratulations! You are now sponsor verified.\n"
            "🎉 You now have full access to tasks, rewards and commands!"
        )
    else:
        await update.message.reply_text("❌ Invalid or expired code. Please try again.")

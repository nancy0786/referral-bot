# handlers/referral.py
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import save_user, get_user_data   # ✅ import db helpers
from utils.checks import ensure_access

async def some_command(update, context):
    if not await ensure_access(update, context):
        return  # stop execution until user completes requirements
    
    # normal command code here
async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send the personal referral link to the user.
    The link is unique to the user and can be used by new users to start the bot.
    """
    user_id = str(update.effective_user.id)
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    # ✅ Save referral link to DB
    user_data = await get_user_data(user_id) or {}
    user_data["ref_link"] = link
    await save_user(user_id, user_data)

    msg = (
        f"📢 *Your Referral Link:*\n{link}\n\n"
        f"Share this link with friends to earn credits & badges!"
    )

    if update.message:
        await update.message.reply_text(msg, parse_mode="Markdown")
    elif update.callback_query:
        await update.callback_query.edit_message_text(msg, parse_mode="Markdown")

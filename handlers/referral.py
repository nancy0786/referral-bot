# handlers/referral.py
from telegram import Update
from telegram.ext import ContextTypes

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Send the personal referral link to the user.
    The link is unique to the user and can be used by new users to start the bot.
    """
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"

    # Handle message command usage (/referral)
    if update.message:
        await update.message.reply_text(
            f"📢 *Your Referral Link:*\n{link}\n\n"
            f"Share this link with friends to earn credits & badges!",
            parse_mode="Markdown"
        )

    # Optional: if you want to handle button callbacks
    elif update.callback_query:
        await update.callback_query.edit_message_text(
            f"📢 *Your Referral Link:*\n{link}\n\n"
            f"Share this link with friends to earn credits & badges!",
            parse_mode="Markdown"
        )

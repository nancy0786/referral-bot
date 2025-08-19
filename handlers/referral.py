# handlers/referral.py
from telegram import Update
from telegram.ext import ContextTypes

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    
    await update.message.reply_text(
        f"📢 *Your Referral Link:*\n{link}\n\n"
        f"Share this link with friends to earn credits & badges!",
        parse_mode="Markdown"
    )

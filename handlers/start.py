import datetime
from telegram import Update
from telegram.ext import ContextTypes
from handlers.force_join import is_member, prompt_join
from utils.db import get_user, save_user, set_invited_by, add_pending_referral
import config
import os

def load_welcome_text() -> str:
    if os.path.exists(config.WELCOME_FILE):
        with open(config.WELCOME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "👋 Welcome!"

async def log_new_user(context: ContextTypes.DEFAULT_TYPE, user: Update.effective_user, ref: str):
    if config.LOG_CHANNEL_ID != 0:
        text = (
            "📥 **New User Started Bot**\n"
            f"👤 Name: {user.full_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🔗 Username: @{user.username if user.username else 'None'}\n"
            f"👥 Referral: `{ref if ref else 'None'}`\n"
            f"⏰ Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await context.bot.send_message(config.LOG_CHANNEL_ID, text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username

    profile = await get_user(user_id, username=username)

    ref_code = None
    if context.args:
        ref = context.args[0]
        if ref.isdigit():
            ref_id = int(ref)
            ref_code = ref
            if ref_id != user_id and profile["referrals"].get("invited_by") is None:
                await set_invited_by(user_id, ref_id)
                await add_pending_referral(ref_id, user_id)

    if not await is_member(context, user_id):
        await prompt_join(update, context)
        await log_new_user(context, user, ref_code)
        return

    welcome_msg = load_welcome_text()
    await update.message.reply_text(welcome_msg)

    await save_user(user_id, profile)
    await log_new_user(context, user, ref_code)

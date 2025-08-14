from telegram import InlineKeyboardMarkup, InlineKeyboardButton, Update
from telegram.ext import ContextTypes
from telegram.constants import ChatMemberStatus
import logging
import config

JOIN_BTN_TEXT = "📢 Join our channel"
RECHECK_BTN_DATA = "recheck_join"
RECHECK_BTN_TEXT = "✅ I've Joined"

async def is_member(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(config.FORCE_JOIN_CHANNEL, user_id)
        return member.status not in (ChatMemberStatus.LEFT, ChatMemberStatus.KICKED)
    except Exception as e:
        logging.warning("Force join check failed: %s", e)
        return True

def join_keyboard() -> InlineKeyboardMarkup:
    url = f"https://t.me/{config.FORCE_JOIN_CHANNEL.lstrip('@')}"
    kb = [
        [InlineKeyboardButton(JOIN_BTN_TEXT, url=url)],
        [InlineKeyboardButton(RECHECK_BTN_TEXT, callback_data=RECHECK_BTN_DATA)]
    ]
    return InlineKeyboardMarkup(kb)

async def prompt_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    text = (
        f"To continue, please join our channel:\n{config.FORCE_JOIN_CHANNEL}\n\n"
        "After joining, tap “✅ I've Joined” below."
    )
    await update.effective_message.reply_text(
        text,
        reply_markup=join_keyboard(),
        disable_web_page_preview=True
    )

async def handle_recheck_join(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    user_id = query.from_user.id
    if await is_member(context, user_id):
        await query.edit_message_text("✅ Great! You're in. Send /start again to continue.")
    else:
        await query.answer("❌ You haven't joined yet.", show_alert=True)

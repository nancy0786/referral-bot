from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from handlers.profile import show_profile
from utils.checks import ensure_access

async def some_command(update, context):
    if not await ensure_access(update, context):
        return  # stop execution until user completes requirements
    
    # normal command code here
async def send_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, edit=False) -> None:
    keyboard = [
        [InlineKeyboardButton("🎥 Watch Videos", callback_data="menu_videos")],
        [InlineKeyboardButton("🏆 My Profile", callback_data="menu_profile")],
        [InlineKeyboardButton("🎯 Tasks", callback_data="menu_tasks")],
        [InlineKeyboardButton("🎁 Redeem Code", callback_data="menu_redeem")],
        [InlineKeyboardButton("💎 Upgrade Plan", callback_data="menu_upgrade")],
        [InlineKeyboardButton("❓ Help", callback_data="menu_help")],
    ]
    markup = InlineKeyboardMarkup(keyboard)

    if edit and update.callback_query:
        await update.callback_query.edit_message_text(
            "📋 **Main Menu**", reply_markup=markup, parse_mode="Markdown"
        )
    else:
        # If called from /menu command
        msg = update.message or update.callback_query.message
        await msg.reply_text(
            "📋 **Main Menu**", reply_markup=markup, parse_mode="Markdown"
        )

async def handle_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    data = query.data
    await query.answer()  # Answer callback query once

    if data == "menu_videos":
        await query.edit_message_text("🎥 Video section coming soon...")
    elif data == "menu_profile":
        await show_profile(update, context)  # ✅ Call real profile handler
    elif data == "menu_tasks":
        from handlers.giveaways import show_giveaways
        await show_giveaways(update, context)
    elif data == "menu_redeem":
        await query.edit_message_text("🎁 Redeem code system coming soon...")
    elif data == "menu_upgrade":
        await query.edit_message_text("💎 Upgrade plans coming soon...")
    elif data == "menu_help":
        await query.edit_message_text("❓ Help section coming soon...")

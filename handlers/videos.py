# handlers/video_handler.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.db import get_user, save_user
import time

VIDEO_CHANNEL = "@YourVideoChannel"  # replace with your channel username

async def get_video_by_number(bot, number: str):
    """Fetch video from the channel by numeric tag in caption."""
    try:
        async for msg in bot.get_chat(VIDEO_CHANNEL).iter_history(limit=200):
            if msg.caption and number in msg.caption:
                if msg.video:
                    return msg.video.file_id
                elif msg.document:
                    return msg.document.file_id
    except Exception as e:
        print(f"[Video Fetch Error] {e}")
    return None

async def send_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to enter video number."""
    if update.callback_query:
        await update.callback_query.edit_message_text(
            "🎥 Please send the video number you want to watch (e.g., 1, 2, 3):"
        )
    else:
        await update.message.reply_text(
            "🎥 Please send the video number you want to watch (e.g., 1, 2, 3):"
        )
    context.user_data["awaiting_video_number"] = True

async def handle_video_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user input for video number."""
    if not context.user_data.get("awaiting_video_number"):
        return

    vid_num = update.message.text.strip()
    user_id = update.effective_user.id
    data = await get_user(user_id)

    plan = data.get("plan", {}).get("name", "free").lower()
    credits = data.get("credits", 0)
    expiry = data.get("plan", {}).get("expires_at")
    now = time.time()

    # Plan & credits logic
    if plan == "premium":
        if expiry and now > expiry:
            data["plan"]["name"] = "free"
            await save_user(user_id, data)
            await update.message.reply_text("⚠️ Your Premium plan expired. Upgrade needed.")
            context.user_data["awaiting_video_number"] = False
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            await save_user(user_id, data)
        else:
            await update.message.reply_text("💳 No credits left. Complete tasks or upgrade plan.")
            context.user_data["awaiting_video_number"] = False
            return
    elif plan == "free":
        await update.message.reply_text("🔓 Free plan: Limited videos only. Upgrade for full access.")
        context.user_data["awaiting_video_number"] = False
        return

    # Fetch video dynamically
    video_file_id = await get_video_by_number(context.bot, vid_num)
    if not video_file_id:
        await update.message.reply_text("❌ Video not found. Make sure the number is correct.")
        context.user_data["awaiting_video_number"] = False
        return

    # Send video with inline download button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Download", callback_data=f"download_{vid_num}")]
    ])
    await update.message.reply_video(video_file_id, caption=f"🎥 Video {vid_num}", reply_markup=keyboard)
    context.user_data["awaiting_video_number"] = False

async def handle_download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle download request with plan/credits check."""
    query = update.callback_query
    vid_num = query.data.replace("download_", "")
    user_id = query.from_user.id
    data = await get_user(user_id)

    plan = data.get("plan", {}).get("name", "free").lower()
    credits = data.get("credits", 0)
    expiry = data.get("plan", {}).get("expires_at")
    now = time.time()

    # Check permissions
    if plan == "premium":
        if expiry and now > expiry:
            data["plan"]["name"] = "free"
            await save_user(user_id, data)
            await query.edit_message_text("⚠️ Premium expired. Cannot download.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            await save_user(user_id, data)
        else:
            await query.answer("💳 No credits left.", show_alert=True)
            return
    elif plan == "free":
        await query.answer("⛔ Free plan cannot download videos.", show_alert=True)
        return

    # Fetch video dynamically
    video_file_id = await get_video_by_number(context.bot, vid_num)
    if not video_file_id:
        await query.answer("❌ Video not found.", show_alert=True)
        return

    # Send video file
    await query.message.reply_video(video_file_id, caption=f"⬇️ Download Video {vid_num}")
    await query.answer("🎉 Video sent for download!")

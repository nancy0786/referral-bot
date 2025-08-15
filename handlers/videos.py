# handlers/videos.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.db import get_user_data, save_user_data
import time

# Your channel where videos are uploaded
VIDEO_CHANNEL = "@YourVideoChannel"

# -----------------------------
# Helper to fetch video dynamically
# -----------------------------
async def get_video_by_number(bot, number: str):
    """Fetch the video from the channel by its numeric tag in caption."""
    try:
        async for msg in bot.get_chat(VIDEO_CHANNEL).iter_history(limit=200):
            if msg.caption and number in msg.caption:
                if msg.video:
                    return msg.video.file_id
                elif msg.document:
                    return msg.document.file_id
    except Exception as e:
        print(f"Error fetching video: {e}")
    return None

# -----------------------------
# Show video menu to user
# -----------------------------
async def send_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt user to enter video number."""
    await update.callback_query.edit_message_text(
        "🎥 Please send the video number you want to watch (e.g., 1, 2, 3):"
    )
    context.user_data["awaiting_video_number"] = True

# -----------------------------
# Handle user input for video
# -----------------------------
async def handle_video_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles user input for video number."""
    if not context.user_data.get("awaiting_video_number"):
        return

    vid_num = update.message.text.strip()
    user_id = update.effective_user.id
    data = get_user_data(user_id)

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", 0)
    now = time.time()

    # Check plan and deduct credits if necessary
    if plan == "premium":
        if expiry and now > expiry:
            data["plan"] = "free"
            save_user_data(user_id, data)
            await update.message.reply_text("⚠️ Your Premium plan expired. Upgrade needed.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            save_user_data(user_id, data)
        else:
            await update.message.reply_text("💳 No credits left. Complete tasks or upgrade plan.")
            return
    elif plan == "free":
        await update.message.reply_text("🔓 Free plan: Only limited videos available. Upgrade for full access.")
        return

    # Fetch video dynamically
    video_file_id = await get_video_by_number(context.bot, vid_num)
    if not video_file_id:
        await update.message.reply_text("❌ Video not found. Make sure the number is correct.")
        return

    # Send video with inline download button
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Download", callback_data=f"download_{vid_num}")]
    ])
    await update.message.reply_video(video_file_id, caption=f"🎥 Video {vid_num}", reply_markup=keyboard)
    context.user_data["awaiting_video_number"] = False

# -----------------------------
# Handle download request
# -----------------------------
async def handle_download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle download request with plan/credits check."""
    query = update.callback_query
    vid_num = query.data.replace("download_", "")
    user_id = query.from_user.id
    data = get_user_data(user_id)

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", 0)
    now = time.time()

    # Check permissions
    if plan == "premium":
        if expiry and now > expiry:
            data["plan"] = "free"
            save_user_data(user_id, data)
            await query.edit_message_text("⚠️ Premium expired. Cannot download.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            save_user_data(user_id, data)
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

# -----------------------------
# Aliases to match main.py imports
# -----------------------------
video_menu = send_video_menu
handle_watch_video = handle_video_number

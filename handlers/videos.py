from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
import json, os, time

USER_DATA_DIR = "user_data"

def get_user_data(user_id):
    path = f"{USER_DATA_DIR}/{user_id}.json"
    if not os.path.exists(path):
        return None
    with open(path, "r") as f:
        return json.load(f)

def save_user_data(user_id, data):
    os.makedirs(USER_DATA_DIR, exist_ok=True)
    with open(f"{USER_DATA_DIR}/{user_id}.json", "w") as f:
        json.dump(data, f, indent=2)

async def video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)

    if not data:
        await update.callback_query.edit_message_text("❌ User data not found.")
        return

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", None)

    # Premium plan check
    if plan == "premium":
        if expiry and time.time() > expiry:
            data["plan"] = "free"
            save_user_data(user_id, data)
            await update.callback_query.edit_message_text(
                "⚠️ Your premium plan has expired. Please upgrade again."
            )
            return
        else:
            await send_video_list(update)
            return

    # Credit-based check
    if plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            save_user_data(user_id, data)
            await send_video_list(update)
            return
        else:
            await update.callback_query.edit_message_text(
                "💳 You have no credits left.\n\nEarn more via tasks or upgrade your plan."
            )
            return

    # Free plan restriction
    if plan == "free":
        await update.callback_query.edit_message_text(
            "🔓 You are on the Free Plan.\n\nUpgrade to Premium or use credits to watch videos."
        )

async def send_video_list(update: Update):
    keyboard = [
        [InlineKeyboardButton("📹 Video 1", callback_data="watch_vid1")],
        [InlineKeyboardButton("📹 Video 2", callback_data="watch_vid2")],
    ]
    await update.callback_query.edit_message_text(
        "🎥 Available Videos:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_watch_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    vid_id = query.data.replace("watch_", "")
    await query.answer()
    await query.edit_message_text(f"▶️ Playing {vid_id} ... (video sending here)")

async def send_video_list(update: Update):
    keyboard = [
        [
            InlineKeyboardButton("▶️ Watch Video 1", callback_data="watch_vid1"),
            InlineKeyboardButton("⬇️ Download Video 1", callback_data="download_vid1")
        ],
        [
            InlineKeyboardButton("▶️ Watch Video 2", callback_data="watch_vid2"),
            InlineKeyboardButton("⬇️ Download Video 2", callback_data="download_vid2")
        ],
    ]
    await update.callback_query.edit_message_text(
        "🎥 Available Videos:", reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    data = get_user_data(user_id)
    plan = data.get("plan", "free")
    credits = data.get("credits", 0)

    # Premium → free download
    if plan == "premium":
        await send_download(update)
        return

    # Credit plan → deduct credit if available
    if plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            save_user_data(user_id, data)
            await send_download(update)
            return
        else:
            await update.callback_query.edit_message_text(
                "💳 You have no credits left.\nEarn more via tasks or upgrade."
            )
            return

    # Free plan → block download
    if plan == "free":
        await update.callback_query.edit_message_text(
            "⛔ Downloads are not available on Free Plan.\nUpgrade or earn credits."
        )

async def send_download(update: Update):
    vid_id = update.callback_query.data.replace("download_", "")
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(f"⬇️ Sending {vid_id} file...")
    # Here send the actual file:
    # await update.effective_chat.send_document(open(f"videos/{vid_id}.mp4", "rb"))

# handlers/videos.py
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, MessageHandler, filters
from utils.db import get_user_data, save_user_data
import sqlite3
import time
from config import ADMIN_IDS
import re
from utils.db import add_fetched_video
from utils.checks import ensure_access   # ✅ import access check
from utils.db import add_or_update_category, get_all_categories


# -----------------------------
# Config
# -----------------------------
VIDEO_CHANNEL = -1002524650614
DB_PATH = "videos.db"

# -----------------------------
# DB Setup
# -----------------------------
def init_video_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS videos (
            vid_num TEXT PRIMARY KEY,
            file_id TEXT NOT NULL,
            msg_id INTEGER NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meta (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.commit()
    conn.close()

def save_video(vid_num, file_id, msg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO videos (vid_num, file_id, msg_id) VALUES (?, ?, ?)", (vid_num, file_id, msg_id))
    conn.commit()
    conn.close()

def get_video(vid_num):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT file_id FROM videos WHERE vid_num = ?", (vid_num,))
    row = cur.fetchone()
    conn.close()
    return row[0] if row else None

def get_all_videos(limit=20):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT vid_num FROM videos ORDER BY CAST(vid_num AS INTEGER) ASC LIMIT ?", (limit,))
    rows = cur.fetchall()
    conn.close()
    return [r[0] for r in rows]

def get_last_msg_id():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT value FROM meta WHERE key='last_msg_id'")
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0

def set_last_msg_id(msg_id):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("INSERT OR REPLACE INTO meta (key, value) VALUES ('last_msg_id', ?)", (str(msg_id),))
    conn.commit()
    conn.close()

# -----------------------------
# Admin: Fetch Videos (/fetchvid)
# -----------------------------
async def fetch_videos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Only admins can fetch videos.")
        return

    await update.message.reply_text(
        "📡 The bot will now automatically save new videos sent in the channel.\n"
        "⚠️ Old videos cannot be fetched due to Telegram Bot API limitations."
    )


# -----------------------------
# Auto-fetch new channel videos
# -----------------------------
async def new_channel_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    msg = update.channel_post
    if not msg.caption:
        print("⚠️ Channel post has no caption. Skipping.")
        return

    match = re.search(r"\d+", msg.caption)
    if not match:
        print(f"⚠️ No video number found in caption: {msg.caption}")
        return

    vid_num = match.group(0)

    file_id = None
    if msg.video:
        file_id = msg.video.file_id
    elif msg.document:
        file_id = msg.document.file_id

    if not file_id:
        print(f"⚠️ No video/document file found in message {msg.message_id}")
        return

    try:
        save_video(vid_num, file_id, msg.message_id)
        set_last_msg_id(msg.message_id)
        print(f"✅ Saved video {vid_num} (msg_id {msg.message_id}) to DB")
    except Exception as e:
        print(f"❌ Failed to save video {vid_num} to DB: {e}")
        return

    try:
        await add_fetched_video(user_id=0, video_id=vid_num, tags=["channel"])
        print(f"✅ Added video {vid_num} to user JSON (user_id=0)")
    except Exception as e:
        print(f"❌ Failed to add video {vid_num} to JSON: {e}")

# -----------------------------
# User: Get specific video (/video #num)
# -----------------------------
async def get_video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_access(update, context):
        return

    if not context.args:
        await update.message.reply_text("⚙️ Usage: /video <number>")
        return

    vid_num = context.args[0].lstrip("#")
    user_id = update.effective_user.id
    data = await get_user_data(user_id)

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", 0)
    now = time.time()

    if plan == "premium":
        if expiry and now > expiry:
            data["plan"] = "free"
            await save_user_data(user_id, data)
            await update.message.reply_text("⚠️ Premium expired. Upgrade required.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            await save_user_data(user_id, data)
        else:
            await update.message.reply_text("💳 Not enough credits.")
            return
    elif plan == "free":
        await update.message.reply_text("⛔ Free plan cannot access this video.")
        return

    video_file_id = get_video(vid_num)
    if not video_file_id:
        await update.message.reply_text("❌ Video not found in DB. Ask admin to run /fetchvid.")
        return

    await update.message.reply_video(video_file_id, caption=f"🎥 Video {vid_num}")

# -----------------------------
# Admin: Manage categories (/addcategory, /categories)
# -----------------------------
async def addcategory_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Only admins can add categories.")
        return

    if len(context.args) < 2:
        await update.message.reply_text("⚙️ Usage: /addcategory <name> <range> (e.g. /addcategory Python 1-50)")
        return

    category_name = context.args[0]
    video_range = context.args[1]

    add_or_update_category(category_name, video_range)
    await update.message.reply_text(f"✅ Category '{category_name}' set for videos {video_range}.")

async def categories_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ Only admins can view categories.")
        return

    cats = get_all_categories()
    if not cats:
        await update.message.reply_text("📂 No categories found. Use /addcategory to create.")
        return

    msg = "\n".join([f"📂 {c[0]} → {c[1]}" for c in cats])
    await update.message.reply_text(f"📂 Categories:\n{msg}")

# -----------------------------
# User: Video details (/videodetails)
# -----------------------------
async def videodetails_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await ensure_access(update, context):
        return

    videos = get_all_videos(limit=50)
    if not videos:
        await update.message.reply_text("📂 No videos available. Please wait until admin uploads/fetches videos.")
        return

    video_list = "\n".join([f"📹 #{v}" for v in videos])
    await update.message.reply_text(f"🎥 Available Videos:\n{video_list}\n\nUse /video <number> to watch.")

# -----------------------------
# Existing logic (unchanged)
# -----------------------------
async def send_video_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.edit_message_text(
        "🎥 Please send the video number you want to watch (e.g., 1, 2, 3):"
    )
    context.user_data["awaiting_video_number"] = True

async def handle_video_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("awaiting_video_number"):
        return

    vid_num = update.message.text.strip()
    user_id = update.effective_user.id
    data = await get_user_data(user_id)

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", 0)
    now = time.time()

    if plan == "premium":
        if expiry and now > expiry:
            data["plan"] = "free"
            await save_user_data(user_id, data)
            await update.message.reply_text("⚠️ Your Premium plan expired. Upgrade needed.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            await save_user_data(user_id, data)
        else:
            await update.message.reply_text("💳 No credits left. Complete tasks or upgrade plan.")
            return
    elif plan == "free":
        await update.message.reply_text("🔓 Free plan: Only limited videos available. Upgrade for full access.")
        return

    video_file_id = get_video(vid_num)
    if not video_file_id:
        await update.message.reply_text("❌ Video not found in DB. Ask admin to run /fetchvid.")
        return

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬇️ Download", callback_data=f"download_{vid_num}")]
    ])
    await update.message.reply_video(video_file_id, caption=f"🎥 Video {vid_num}", reply_markup=keyboard)
    context.user_data["awaiting_video_number"] = False

async def handle_download_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    vid_num = query.data.replace("download_", "")
    user_id = query.from_user.id
    data = await get_user_data(user_id)

    plan = data.get("plan", "free")
    credits = data.get("credits", 0)
    expiry = data.get("plan_expiry", 0)
    now = time.time()

    if plan == "premium":
        if expiry and now > expiry:
            data["plan"] = "free"
            await save_user_data(user_id, data)
            await query.edit_message_text("⚠️ Premium expired. Cannot download.")
            return
    elif plan == "credit":
        if credits > 0:
            data["credits"] -= 1
            await save_user_data(user_id, data)
        else:
            await query.answer("💳 No credits left.", show_alert=True)
            return
    elif plan == "free":
        await query.answer("⛔ Free plan cannot download videos.", show_alert=True)
        return

    video_file_id = get_video(vid_num)
    if not video_file_id:
        await query.answer("❌ Video not found in DB.", show_alert=True)
        return

    await query.message.reply_video(video_file_id, caption=f"⬇️ Download Video {vid_num}")
    await query.answer("🎉 Video sent for download!")

# -----------------------------
# Aliases
# -----------------------------
video_menu = send_video_menu
handle_watch_video = handle_video_number

# -----------------------------
# Init DB on import
# -----------------------------
init_video_db()

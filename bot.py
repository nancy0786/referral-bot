import os
import time
import json
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)
from telegram.error import TelegramError
from dotenv import load_dotenv
import uuid
import re

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS").split(",")]
STORAGE_CHAT_ID = os.getenv("STORAGE_CHAT_ID")
SPONSOR_BOT_USERNAME = os.getenv("SPONSOR_BOT_USERNAME")

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory cache for message IDs
USER_MESSAGE_IDS = {}  # {user_id: message_id}

# Resolve channel ID from link or ID
async def resolve_chat_id(context: ContextTypes.DEFAULT_TYPE, chat_identifier: str):
    """Convert a channel link or ID to a chat ID."""
    try:
        if chat_identifier.isdigit() or chat_identifier.startswith("-"):
            return int(chat_identifier)
        chat_identifier = chat_identifier.lstrip("@").split("/")[-1]
        chat = await context.bot.get_chat(f"@{chat_identifier}")
        return chat.id
    except TelegramError as e:
        logger.error(f"Error resolving chat ID for {chat_identifier}: {e}")
        raise ValueError(f"Invalid chat identifier: {chat_identifier}")

# Initialize chat IDs
async def initialize_chat_ids(context: ContextTypes.DEFAULT_TYPE):
    """Resolve CHANNEL_ID and STORAGE_CHAT_ID from .env."""
    global CHANNEL_ID, STORAGE_CHAT_ID
    CHANNEL_ID = await resolve_chat_id(context, CHANNEL_ID)
    STORAGE_CHAT_ID = await resolve_chat_id(context, STORAGE_CHAT_ID)
    logger.info(f"Resolved CHANNEL_ID: {CHANNEL_ID}, STORAGE_CHAT_ID: {STORAGE_CHAT_ID}")

# File-based DB functions
async def save_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict):
    """Save user data to Telegram storage chat as a JSON message."""
    try:
        data_str = json.dumps(data, indent=2)
        message = await context.bot.send_message(
            chat_id=STORAGE_CHAT_ID, text=f"USER_{user_id}\n{data_str}"
        )
        USER_MESSAGE_IDS[user_id] = message.message_id
        return message.message_id
    except TelegramError as e:
        logger.error(f"Error saving user data for {user_id}: {e}")
        return None

async def load_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Load user data from Telegram storage chat using cached message ID."""
    try:
        if user_id in USER_MESSAGE_IDS:
            message_id = USER_MESSAGE_IDS[user_id]
            # Fetch the specific message by copying it
            message = await context.bot.copy_message(
                chat_id=STORAGE_CHAT_ID,
                from_chat_id=STORAGE_CHAT_ID,
                message_id=message_id,
                disable_notification=True
            )
            if message.text and message.text.startswith(f"USER_{user_id}\n"):
                data = json.loads(message.text.split("\n", 1)[1])
                data["message_id"] = message_id
                return data
        # Fallback: Search recent updates
        async for update in context.bot.get_updates(limit=100):
            if (
                update.message
                and update.message.chat_id == STORAGE_CHAT_ID
                and update.message.text
                and update.message.text.startswith(f"USER_{user_id}\n")
            ):
                data = json.loads(update.message.text.split("\n", 1)[1])
                USER_MESSAGE_IDS[user_id] = update.message.message_id
                data["message_id"] = update.message.message_id
                return data
        return None
    except TelegramError as e:
        logger.error(f"Error loading user data for {user_id}: {e}")
        return None

async def update_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int, data: dict):
    """Update user data by editing the existing message."""
    existing_data = await load_user_data(context, user_id)
    if existing_data and "message_id" in existing_data:
        try:
            await context.bot.edit_message_text(
                chat_id=STORAGE_CHAT_ID,
                message_id=existing_data["message_id"],
                text=f"USER_{user_id}\n{json.dumps(data, indent=2)}",
            )
        except TelegramError as e:
            logger.error(f"Error updating user data for {user_id}: {e}")
    else:
        await save_user_data(context, user_id, data)

async def get_total_users(context: ContextTypes.DEFAULT_TYPE):
    """Count total users in storage chat."""
    count = 0
    try:
        async for update in context.bot.get_updates(limit=1000):
            if (
                update.message
                and update.message.chat_id == STORAGE_CHAT_ID
                and update.message.text
                and update.message.text.startswith("USER_")
            ):
                count += 1
    except TelegramError as e:
        logger.error(f"Error counting users: {e}")
    return count

# Initialize user data
async def init_user_data(context: ContextTypes.DEFAULT_TYPE, user_id: int, username: str, inviter_id: int = None):
    """Initialize new user data."""
    data = {
        "username": username,
        "credits": 0,
        "plan": "Free",
        "plan_expiry": None,
        "referrals": [],
        "successful_referrals": 0,
        "daily_videos_watched": 0,
        "last_video_time": 0,
        "redeemed_codes": [],
        "badges": [],
        "last_activity": int(time.time()),
        "sponsor_verified": False,
        "inviter_id": inviter_id,
    }
    await save_user_data(context, user_id, data)
    return data

# Check channel membership
async def check_channel_membership(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Check if user is a member of the required channel."""
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except TelegramError:
        return False

# Plan details
PLANS = {
    "Free": {"credits_per_hour": 3, "daily_video_limit": 10},
    "Daily": {"credits": 35, "days": 1, "unlimited_videos": True},
    "Monthly": {"credits": 860, "days": 28, "unlimited_videos": True},
    "Premium": {"credits": 0, "days": 40, "unlimited_videos": True, "downloads_per_day": 0},
    "Elite": {"credits": 0, "days": 45, "unlimited_videos": True, "downloads_per_day": 10},
    "Superior": {"credits": 0, "days": 60, "unlimited_videos": True, "downloads_per_day": 25},
}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    # Initialize chat IDs on first command
    if isinstance(CHANNEL_ID, str) or isinstance(STORAGE_CHAT_ID, str):
        await initialize_chat_ids(context)

    user = update.effective_user
    user_id = user.id
    username = user.username or user.first_name
    args = context.args

    # Check for referral
    inviter_id = int(args[0]) if args and args[0].isdigit() else None

    # Load or initialize user data
    user_data = await load_user_data(context, user_id)
    if not user_data:
        user_data = await init_user_data(context, user_id, username, inviter_id)

    # Check session expiry
    current_time = int(time.time())
    if current_time - user_data.get("last_activity", 0) > 1800:  # 30 mins
        await update.message.delete()
        await update.message.reply_text("Session Expired. Use /start to begin again.")
        return

    # Update last activity
    user_data["last_activity"] = current_time
    await update_user_data(context, user_id, user_data)

    # Check channel membership
    if not await check_channel_membership(context, user_id):
        keyboard = [
            [InlineKeyboardButton("Join Channel", url=f"https://t.me/{str(CHANNEL_ID).lstrip('@')}")],
            [InlineKeyboardButton("✅ I've Joined", callback_data="check_join")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"Please join our channel to proceed.", reply_markup=reply_markup
        )
        return

    # Check sponsor bot verification
    if not user_data.get("sponsor_verified", False):
        await update.message.reply_text(
            f"Please forward a message from {SPONSOR_BOT_USERNAME} to verify usage."
        )
        return

    # Show main menu
    await show_main_menu(update, context)

# Main menu
async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display the main menu."""
    keyboard = [
        [InlineKeyboardButton("🎬 Watch Videos", callback_data="watch_videos")],
        [InlineKeyboardButton("💎 Profile", callback_data="profile")],
        [InlineKeyboardButton("🧑‍🤝‍🧑 Invite Friends", callback_data="invite_friends")],
        [InlineKeyboardButton("🎁 Daily Tasks & Giveaways", callback_data="tasks_giveaways")],
        [InlineKeyboardButton("🎟 Redeem Code", callback_data="redeem_code")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.message.edit_text("🏠 Main Menu", reply_markup=reply_markup)
    else:
        await update.message.reply_text("🏠 Main Menu", reply_markup=reply_markup)

# Callback handler
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    user_data = await load_user_data(context, user_id)

    if not user_data:
        await query.message.reply_text("Please start the bot with /start.")
        return

    # Update last activity
    user_data["last_activity"] = int(time.time())
    await update_user_data(context, user_id, user_data)

    if query.data == "check_join":
        if await check_channel_membership(context, user_id):
            await query.message.edit_text("Channel joined! Please forward a message from the sponsor bot.")
        else:
            await query.message.edit_text("You haven't joined the channel yet. Please join and try again.")
        return

    if not user_data.get("sponsor_verified", False):
        await query.message.edit_text("Please forward a message from the sponsor bot first.")
        return

    if query.data == "watch_videos":
        await handle_watch_videos(query, context, user_data)
    elif query.data == "profile":
        await show_profile(query, context, user_data)
    elif query.data == "invite_friends":
        await show_referral(query, context, user_data)
    elif query.data == "tasks_giveaways":
        await show_tasks_giveaways(query, context)
    elif query.data == "redeem_code":
        await query.message.reply_text("Please send the 16-digit redeem code using /redeem <code>.")
    elif query.data.startswith("watch_video_"):
        await play_video(query, context, user_data)
    elif query.data.startswith("download_video_"):
        await download_video(query, context, user_data)
    elif query.data == "back_to_menu":
        await show_main_menu(query, context)

# Sponsor bot verification
async def handle_forwarded_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify forwarded message from sponsor bot."""
    user_id = update.effective_user.id
    user_data = await load_user_data(context, user_id)
    if not user_data:
        await update.message.reply_text("Please start the bot with /start.")
        return

    if update.message.forward_from_chat and update.message.forward_from_chat.username == SPONSOR_BOT_USERNAME:
        user_data["sponsor_verified"] = True
        user_data["last_activity"] = int(time.time())
        await update_user_data(context, user_id, user_data)
        await update.message.reply_text("Sponsor bot verified! Welcome to the main menu.")
        await show_main_menu(update, context)
    else:
        await update.message.reply_text(f"Please forward a message from {SPONSOR_BOT_USERNAME}.")

# Watch videos
async def handle_watch_videos(query: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Handle watch videos section."""
    user_id = query.from_user.id
    current_time = int(time.time())
    plan = user_data.get("plan", "Free")
    plan_info = PLANS.get(plan, PLANS["Free"])

    # Check plan expiry
    if user_data.get("plan_expiry"):
        expiry = datetime.fromisoformat(user_data["plan_expiry"])
        if datetime.now() < expiry:
            if plan not in ["Premium", "Elite", "Superior"]:
                user_data["credits"] += plan_info.get("credits_per_hour", 0)
                user_data["last_activity"] = current_time
                await update_user_data(context, user_id, user_data)
        else:
            user_data["plan"] = "Free"
            user_data["plan_expiry"] = None
            user_data["credits"] = 0
            await update_user_data(context, user_id, user_data)

    # Check daily video limit
    today = datetime.now().date().isoformat()
    if user_data.get("last_video_date", "") != today:
        user_data["daily_videos_watched"] = 0
        user_data["last_video_date"] = today

    if not plan_info.get("unlimited_videos", False) and user_data["daily_videos_watched"] >= plan_info["daily_video_limit"]:
        await query.message.edit_text("Daily video limit reached. Upgrade your plan or try tomorrow!")
        return

    # Check cooldown
    if current_time - user_data.get("last_video_time", 0) < 180:  # 3 mins
        await query.message.edit_text("Please wait 3 minutes before watching another video.")
        return

    # Dummy video list (replace with actual video URLs)
    videos = [
        {"id": 1, "title": "Video 1", "url": "https://example.com/video1.mp4"},
        {"id": 2, "title": "Video 2", "url": "https://example.com/video2.mp4"},
    ]

    keyboard = [
        [InlineKeyboardButton(video["title"], callback_data=f"watch_video_{video['id']}")]
        for video in videos
    ]
    keyboard.append([InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")])
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text("🎬 Choose a video to watch:", reply_markup=reply_markup)

# Play video
async def play_video(query: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Handle video playback."""
    user_id = query.from_user.id
    video_id = int(query.data.split("_")[-1])
    plan = user_data.get("plan", "Free")
    plan_info = PLANS.get(plan, PLANS["Free"])

    # Check credits
    if not plan_info.get("unlimited_videos", False) and user_data["credits"] < 1:
        await query.message.edit_text("Not enough credits to watch a video.")
        return

    # Dummy video (replace with actual video)
    video = {"id": video_id, "title": f"Video {video_id}", "url": f"https://example.com/video{video_id}.mp4"}
    user_data["daily_videos_watched"] += 1
    user_data["last_video_time"] = int(time.time())
    if not plan_info.get("unlimited_videos", False):
        user_data["credits"] -= 1

    # Check referral reward
    if user_data.get("inviter_id") and user_data["daily_videos_watched"] == 1:
        inviter_data = await load_user_data(context, user_data["inviter_id"])
        if inviter_data:
            inviter_data["successful_referrals"] += 1
            inviter_data["credits"] += 7
            if inviter_data["successful_referrals"] >= 6 and inviter_data["plan"] != "Premium":
                inviter_data["plan"] = "Premium"
                inviter_data["plan_expiry"] = (datetime.now() + timedelta(days=40)).isoformat()
            if inviter_data["successful_referrals"] >= 11 and "Top Referrer" not in inviter_data["badges"]:
                inviter_data["badges"].append("Top Referrer")
            await update_user_data(context, user_data["inviter_id"], inviter_data)

    await update_user_data(context, user_id, user_data)

    keyboard = [
        [InlineKeyboardButton("📥 Download (2 credits)", callback_data=f"download_video_{video_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="watch_videos")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message = await query.message.reply_text(f"Playing {video['title']}...\n{video['url']}", reply_markup=reply_markup)
    
    # Auto-delete after 10 mins
    context.job_queue.run_once(delete_message, 600, data={"chat_id": message.chat_id, "message_id": message.message_id})

# Download video
async def download_video(query: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Handle video download."""
    user_id = query.from_user.id
    video_id = int(query.data.split("_")[-1])
    plan = user_data.get("plan", "Free")
    plan_info = PLANS.get(plan, PLANS["Free"])

    # Check download limits
    today = datetime.now().date().isoformat()
    if user_data.get("last_download_date", "") != today:
        user_data["daily_downloads"] = 0
        user_data["last_download_date"] = today

    if plan in ["Elite", "Superior"] and user_data["daily_downloads"] >= plan_info["downloads_per_day"]:
        await query.message.edit_text(f"Daily download limit ({plan_info['downloads_per_day']}) reached.")
        return

    if user_data["credits"] < 2 and plan not in ["Premium", "Elite", "Superior"]:
        await query.message.edit_text("Not enough credits to download (2 credits required).")
        return

    user_data["daily_downloads"] = user_data.get("daily_downloads", 0) + 1
    if plan not in ["Premium", "Elite", "Superior"]:
        user_data["credits"] -= 2
    await update_user_data(context, user_id, user_data)

    # Dummy video URL
    video_url = f"https://example.com/video{video_id}.mp4"
    message = await query.message.reply_text(f"Downloading video...\n{video_url}")
    
    # Auto-delete after 5 mins
    context.job_queue.run_once(delete_message, 300, data={"chat_id": message.chat_id, "message_id": message.message_id})

# Profile
async def show_profile(query: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Show user profile."""
    badges = ", ".join(user_data.get("badges", [])) or "None"
    text = (
        f"💎 Profile\n\n"
        f"Username: {user_data['username']}\n"
        f"User ID: {query.from_user.id}\n"
        f"Credits: {user_data['credits']}\n"
        f"Plan: {user_data['plan']}\n"
        f"Badges: {badges}\n"
        f"Total Referrals: {user_data['successful_referrals']}\n"
        f"Redeemed Codes: {len(user_data['redeemed_codes'])}"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup)

# Referral
async def show_referral(query: Update, context: ContextTypes.DEFAULT_TYPE, user_data: dict):
    """Show referral link."""
    referral_link = f"https://t.me/{(await context.bot.get_me()).username}?start={query.from_user.id}"
    text = (
        f"🧑‍🤝‍🧑 Invite Friends\n\n"
        f"Your referral link: {referral_link}\n"
        f"Earn 7 credits per successful referral.\n"
        f"6 referrals ➝ Premium Plan\n"
        f"11 referrals ➝ Top Referrer Badge + Giveaway Access"
    )
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup)

# Tasks & Giveaways
async def show_tasks_giveaways(query: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show tasks and giveaways."""
    text = (
        "🎁 Daily Tasks & Giveaways\n\n"
        "Tasks:\n- Join @example_channel (10 credits)\n"
        "Giveaways:\n- No active giveaways."
    )
    keyboard = [[InlineKeyboardButton("🔙 Back", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.edit_text(text, reply_markup=reply_markup)

# Redeem code
async def redeem(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /redeem command."""
    user_id = update.effective_user.id
    user_data = await load_user_data(context, user_id)
    if not user_data:
        await update.message.reply_text("Please start the bot with /start.")
        return

    if len(context.args) != 1 or len(context.args[0]) != 16:
        await update.message.reply_text("Please provide a valid 16-digit redeem code.")
        return

    code = context.args[0].upper()
    code_data = await load_user_data(context, f"CODE_{code}")
    if not code_data or code in user_data["redeemed_codes"]:
        await update.message.reply_text("Invalid or already used code.")
        return

    user_data["credits"] += code_data.get("credits", 0)
    if code_data.get("plan"):
        user_data["plan"] = code_data["plan"]
        user_data["plan_expiry"] = (datetime.now() + timedelta(days=code_data["days"])).isoformat()
    user_data["redeemed_codes"].append(code)
    await update_user_data(context, user_id, user_data)
    await update.message.reply_text(f"Code redeemed! You received {code_data.get('credits', 0)} credits.")

# Admin panel
async def admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Admin panel command."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized.")
        return

    keyboard = [
        [InlineKeyboardButton("Users", callback_data="admin_users")],
        [InlineKeyboardButton("Broadcast", callback_data="admin_broadcast")],
        [InlineKeyboardButton("Add Credits", callback_data="admin_add_credit")],
        [InlineKeyboardButton("Set Plan", callback_data="admin_set_plan")],
        [InlineKeyboardButton("Create Code", callback_data="admin_create_code")],
        [InlineKeyboardButton("User Stats", callback_data="admin_user_stats")],
        [InlineKeyboardButton("Tasks", callback_data="admin_tasks")],
        [InlineKeyboardButton("Giveaway", callback_data="admin_giveaway")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("🛠 Admin Panel", reply_markup=reply_markup)

# Admin callback
async def admin_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin button callbacks."""
    query = update.callback_query
    await query.answer()
    if query.from_user.id not in ADMIN_IDS:
        await query.message.edit_text("Unauthorized.")
        return

    if query.data == "admin_users":
        total_users = await get_total_users(context)
        await query.message.edit_text(f"Total Users: {total_users}")
    elif query.data == "admin_broadcast":
        await query.message.edit_text("Reply with the message to broadcast.")
        context.user_data["admin_action"] = "broadcast"
    elif query.data == "admin_add_credit":
        await query.message.edit_text("Send /add_credit <user_id> <amount>")
    elif query.data == "admin_set_plan":
        await query.message.edit_text("Send /set_plan <user_id> <Daily|Monthly|Premium|Elite|Superior> <days>")
    elif query.data == "admin_create_code":
        code = "".join(str(uuid.uuid4()).replace("-", "").upper()[:16])
        code_data = {"credits": 50, "plan": None, "days": 0}
        await save_user_data(context, f"CODE_{code}", code_data)
        await query.message.edit_text(f"New redeem code created: {code}")
    elif query.data == "admin_user_stats":
        await query.message.edit_text("Referral leaderboard not implemented yet.")
    elif query.data == "admin_tasks":
        await query.message.edit_text("Send /tasks to create new tasks.")
    elif query.data == "admin_giveaway":
        await query.message.edit_text("Send /giveaway to start a giveaway.")

# Admin commands
async def add_credit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add credits to a user."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) != 2 or not context.args[1].isdigit():
        await update.message.reply_text("Usage: /add_credit <user_id> <amount>")
        return
    user_id = int(context.args[0])
    amount = int(context.args[1])
    user_data = await load_user_data(context, user_id)
    if user_data:
        user_data["credits"] += amount
        await update_user_data(context, user_id, user_data)
        await update.message.reply_text(f"Added {amount} credits to user {user_id}.")
    else:
        await update.message.reply_text("User not found.")

async def set_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set user plan."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized.")
        return
    if len(context.args) != 3 or context.args[1] not in PLANS or not context.args[2].isdigit():
        await update.message.reply_text("Usage: /set_plan <user_id> <Daily|Monthly|Premium|Elite|Superior> <days>")
        return
    user_id = int(context.args[0])
    plan = context.args[1]
    days = int(context.args[2])
    user_data = await load_user_data(context, user_id)
    if user_data:
        user_data["plan"] = plan
        user_data["plan_expiry"] = (datetime.now() + timedelta(days=days)).isoformat()
        user_data["credits"] += PLANS[plan].get("credits", 0)
        await update_user_data(context, user_id, user_data)
        await update.message.reply_text(f"Set plan {plan} for user {user_id} for {days} days.")
    else:
        await update.message.reply_text("User not found.")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Broadcast a message."""
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("Unauthorized.")
        return
    if context.user_data.get("admin_action") != "broadcast":
        await update.message.reply_text("Please select broadcast from admin panel first.")
        return
    try:
        async for update in context.bot.get_updates(limit=1000):
            if (
                update.message
                and update.message.chat_id == STORAGE_CHAT_ID
                and update.message.text
                and update.message.text.startswith("USER_")
            ):
                user_id = int(update.message.text.split("\n")[0].split("_")[1])
                try:
                    await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=update.message.chat_id,
                        message_id=update.message.message_id,
                    )
                except TelegramError:
                    continue
    except TelegramError as e:
        logger.error(f"Error broadcasting: {e}")
    await update.message.reply_text("Broadcast sent.")
    context.user_data.pop("admin_action", None)

# Job to delete messages
async def delete_message(context: ContextTypes.DEFAULT_TYPE):
    """Delete a message after a delay."""
    data = context.job.data
    try:
        await context.bot.delete_message(chat_id=data["chat_id"], message_id=data["message_id"])
    except TelegramError:
        pass

# Main function
def main():
    """Run the bot."""
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("redeem", redeem))
    application.add_handler(CommandHandler("admin", admin))
    application.add_handler(CommandHandler("add_credit", add_credit))
    application.add_handler(CommandHandler("set_plan", set_plan))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CallbackQueryHandler(button_callback))
    application.add_handler(MessageHandler(filters.FORWARDED, handle_forwarded_message))

    application.run_polling()

if __name__ == "__main__":
    main()

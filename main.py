# main.py
import os
import logging
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# ========================
# LOAD ENV
# ========================
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@playhubby").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0").strip())
WELCOME_FILE = os.path.join("data", "welcome.txt")
SPONSOR_BOT_USERNAME = os.getenv("SPONSOR_BOT_USERNAME", "").strip()
SPONSOR_BOT_ID = int(os.getenv("SPONSOR_BOT_ID", "0").strip())
REDEEM_CODE_LENGTH = 16
PRIVATE_DB_CHANNEL_ID = int(os.getenv("PRIVATE_DB_CHANNEL_ID", "0").strip() or 0)
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "db")
INDEX_FILENAME = "backup_index"

# ========================
# IMPORT HANDLERS
# ========================
from handlers.start import start
from handlers.force_join import handle_recheck_join, RECHECK_BTN_DATA
from handlers.sponsor_verify import handle_forward
from handlers.menu import send_main_menu, handle_menu_callback
from handlers.videos import (
    video_menu,
    handle_watch_video,
    handle_download_video,
    videolist_command,
    videodetails_command,
    get_video_command,
    fetch_videos   # ✅ NEW
)
from handlers.tasks import show_tasks, handle_task_done
from handlers.profile import show_profile
from handlers.referral import send_referral_link
from handlers.redeem import start_redeem_command, start_redeem_from_menu, handle_redeem_text
from handlers import admin, session
from handlers.admin_restore import restore_db_command
from plan_system import check_and_update_expiry, refill_free_plan_credits
from admin_commands import admin_set_plan
from user_system import ensure_user_registered
from utils.db import update_last_active

# ========================
# LOGGING
# ========================
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ========================
# MIDDLEWARES
# ========================
async def activity_middleware(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        await update_last_active(update.effective_user.id)

async def global_user_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user:
        user_id = str(update.effective_user.id)
        result = ensure_user_registered(user_id, update.effective_user)
        if result:
            await result
        check_and_update_expiry(user_id)
        refill_free_plan_credits(user_id)

# ========================
# BASIC COMMANDS
# ========================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await global_user_check(update, context)
    await update.message.reply_text("👋 Welcome back! Your plan details are up-to-date.")

async def echo_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await global_user_check(update, context)
    await update.message.reply_text("✅ Message received and plan checked.")

# ========================
# MAIN FUNCTION
# ========================
def main():
    if not BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")

    app = Application.builder().token(BOT_TOKEN).build()

    # Save admin IDs in bot_data for use in videolist
    app.bot_data["ADMIN_IDS"] = ADMIN_IDS

    # Middleware
    app.add_handler(MessageHandler(filters.ALL, activity_middleware), group=-1)

    # Commands
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", send_main_menu))
    app.add_handler(CommandHandler("redeem", start_redeem_command))
    app.add_handler(CommandHandler("restore_db", restore_db_command))
    app.add_handler(CommandHandler("set_plan", admin_set_plan))
    app.add_handler(CommandHandler("broadcast", admin.broadcast))
    app.add_handler(CommandHandler("setwelcome", admin.setwelcome))
    app.add_handler(CommandHandler("addcredits", admin.addcredits))
    app.add_handler(CommandHandler("setplan", admin.setplan))
    app.add_handler(CommandHandler("stats", admin.stats))
    app.add_handler(CommandHandler("listusers", admin.listusers))

    # NEW video commands
    app.add_handler(CommandHandler("videolist", videolist_command))
    app.add_handler(CommandHandler("videodetails", videodetails_command))
    app.add_handler(CommandHandler("video", video_command))
    app.add_handler(CommandHandler("fetchvid", fetch_videos_command))  # ✅ NEW admin fetch command

    # CallbackQueryHandlers
    app.add_handler(CallbackQueryHandler(handle_recheck_join, pattern=f"^{RECHECK_BTN_DATA}$"))
    app.add_handler(CallbackQueryHandler(start_redeem_from_menu, pattern="^menu_redeem$"))
    app.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))
    app.add_handler(CallbackQueryHandler(video_menu, pattern="^menu_videos$"))
    app.add_handler(CallbackQueryHandler(handle_watch_video, pattern="^watch_"))
    app.add_handler(CallbackQueryHandler(handle_download_video, pattern="^download_"))
    app.add_handler(CallbackQueryHandler(show_tasks, pattern="^tasks$"))
    app.add_handler(CallbackQueryHandler(handle_task_done, pattern="^task_done_"))
    app.add_handler(CallbackQueryHandler(show_profile, pattern="^profile$"))
    app.add_handler(CallbackQueryHandler(send_referral_link, pattern="^ref_link$"))

    # Forwarded messages (Sponsor Verification)
    app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))

    # Redeem text
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_redeem_text))

    # General messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo_command))

    # Background jobs
    job_queue = app.job_queue
    job_queue.run_repeating(session.check_sessions, interval=60, first=60)

    logger.info("Bot started...")
    app.run_polling(allowed_updates=["message", "callback_query"])

# ========================
# ENTRY POINT
# ========================
if __name__ == "__main__":
    main()

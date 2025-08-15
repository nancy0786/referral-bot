import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler
import config
from handlers.start import start
from handlers.force_join import handle_recheck_join, RECHECK_BTN_DATA

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")

    app = Application.builder().token(config.BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(handle_recheck_join, pattern=f"^{RECHECK_BTN_DATA}$"))

    logger.info("Bot started...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()


    from handlers.sponsor_verify import handle_forward

# ...
app.add_handler(MessageHandler(filters.FORWARDED, handle_forward))    


from handlers.menu import send_main_menu, handle_menu_callback

# Commands
app.add_handler(CommandHandler("menu", send_main_menu))

# Callbacks
app.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))

from handlers.videos import video_menu, handle_watch_video

app.add_handler(CallbackQueryHandler(video_menu, pattern="^menu_videos$"))
app.add_handler(CallbackQueryHandler(handle_watch_video, pattern="^watch_"))

from handlers.videos import handle_download_video

app.add_handler(CallbackQueryHandler(handle_download_video, pattern="^download_"))


from handlers.tasks import show_tasks, handle_task_done

app.add_handler(CallbackQueryHandler(show_tasks, pattern="^tasks$"))
app.add_handler(CallbackQueryHandler(handle_task_done, pattern="^task_done_"))

[InlineKeyboardButton("👤 Profile", callback_data="profile")]


from handlers.profile import show_profile

app.add_handler(CallbackQueryHandler(show_profile, pattern="^profile$"))

[InlineKeyboardButton("🔗 My Referral Link", callback_data="ref_link")]


from handlers.referral import send_referral_link

app.add_handler(CallbackQueryHandler(send_referral_link, pattern="^ref_link$"))


# main.py (additions)
import logging
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
import config
from handlers.start import start
from handlers.force_join import handle_recheck_join, RECHECK_BTN_DATA
from handlers.menu import send_main_menu, handle_menu_callback  # if you have it
from handlers.redeem import start_redeem_command, start_redeem_from_menu, handle_redeem_text

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main() -> None:
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing in .env")

    app = Application.builder().token(config.BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", send_main_menu))
    app.add_handler(CommandHandler("redeem", start_redeem_command))

    # Callback buttons
    app.add_handler(CallbackQueryHandler(handle_recheck_join, pattern=f"^{RECHECK_BTN_DATA}$"))
    app.add_handler(CallbackQueryHandler(start_redeem_from_menu, pattern="^menu_redeem$"))
    # Keep your other menu callbacks like:
    # app.add_handler(CallbackQueryHandler(handle_menu_callback, pattern="^menu_"))

    # Text handler for redeem code input (only works when awaiting flag is set)
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_redeem_text))

    logger.info("Bot started...")
    app.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == "__main__":
    main()





from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackQueryHandler
from handlers import start, sponsor_verify, menu, videos, download, tasks, profile, referral, redeem, session
from utils.db import update_last_active

TOKEN = "YOUR_BOT_TOKEN"

app = ApplicationBuilder().token(TOKEN).build()

# Update last active on every user interaction
def activity_middleware(update, context):
    if update.effective_user:
        update_last_active(update.effective_user.id)
app.add_handler(MessageHandler(filters.ALL, activity_middleware), group=-1)

# Register your other handlers here...
# Example:
# app.add_handler(CommandHandler("start", start.start_handler))

# Background job to check session expiry
app.job_queue.run_repeating(session.check_sessions, interval=60, first=60)

app.run_polling()



from handlers import admin

app.add_handler(CommandHandler("broadcast", admin.broadcast))
app.add_handler(CommandHandler("setwelcome", admin.setwelcome))
app.add_handler(CommandHandler("addcredits", admin.addcredits))
app.add_handler(CommandHandler("setplan", admin.setplan))
app.add_handler(CommandHandler("stats", admin.stats))
app.add_handler(CommandHandler("listusers", admin.listusers))



# main.py
import logging
from telegram.ext import Application, CommandHandler
import config
from handlers.start import start
from handlers.force_join import handle_recheck_join, RECHECK_BTN_DATA
from handlers.admin_restore import restore_db_command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    if not config.BOT_TOKEN:
        raise SystemExit("BOT_TOKEN missing")
    app = Application.builder().token(config.BOT_TOKEN).build()

    # Basic handlers (register other handlers as you have them)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("restore_db", restore_db_command))  # admin-only

    # your other handlers...
    # app.add_handler(CallbackQueryHandler(...))

    logger.info("Bot starting...")
    app.run_polling(allowed_updates=["message","callback_query"])

if __name__ == "__main__":
    main()



from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext
from plan_system import check_and_update_expiry, refill_free_plan_credits
from admin_commands import admin_set_plan
from user_system import ensure_user_registered

# Called for every message or command
async def global_user_check(update: Update, context: CallbackContext):
    user_id = str(update.effective_user.id)

    # Ensure user exists in DB
    ensure_user_registered(user_id, update.effective_user)

    # Step 13: Check expiry + refill free plan
    check_and_update_expiry(user_id)
    refill_free_plan_credits(user_id)


async def start(update: Update, context: CallbackContext):
    await global_user_check(update, context)
    await update.message.reply_text("👋 Welcome back! Your plan details are up-to-date.")


async def echo(update: Update, context: CallbackContext):
    await global_user_check(update, context)
    await update.message.reply_text("✅ Message received and plan checked.")


def main():
    app = ApplicationBuilder().token("YOUR_BOT_TOKEN").build()

    # Admin command to set plan
    app.add_handler(CommandHandler("set_plan", admin_set_plan))

    # User start
    app.add_handler(CommandHandler("start", start))

    # General messages
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))

    app.run_polling()


if __name__ == "__main__":
    main()



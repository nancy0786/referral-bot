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

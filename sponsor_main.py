# sponsor_main.py
import logging
from telegram.ext import Application, CommandHandler
from utils.db import init_db

SPONSOR_BOT_TOKEN = "7770837317:AAF1sv0Urz-cg7jINyBBDaW_0tO3R5k70dc"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

async def getcode(update, context):
    user_id = update.effective_user.id
    code = f"SPONSOR-{user_id}"
    await update.message.reply_text(f"Your sponsor code: {code}")

def main():
    # Initialize DB
    init_db()

    # Create bot app
    app = Application.builder().token(SPONSOR_BOT_TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("getcode", getcode))

    # Start bot
    print("Sponsor bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

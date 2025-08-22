# sponsor_main.py
import logging
from telegram.ext import Application, CommandHandler
from utils.db import init_db
from handlers.sponsor_verify import getcode   # ✅ Import the correct handler

SPONSOR_BOT_TOKEN = "7770837317:AAF1sv0Urz-cg7jINyBBDaW_0tO3R5k70dc"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

def main():
    # Initialize DB
    init_db()

    # Create bot app
    app = Application.builder().token(SPONSOR_BOT_TOKEN).build()

    # ✅ Register the imported handler (not a local one)
    app.add_handler(CommandHandler("getcode", getcode))

    # Start bot
    print("Sponsor bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()

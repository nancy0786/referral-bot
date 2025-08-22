# sponsor_main.py

import asyncio
from telegram.ext import Application, CommandHandler
import config
from handlers.sponsor_verify import getcode
from utils.db import init_db

async def main():
    await init_db()  # init database if needed
    app = Application.builder().token(config.SPONSOR_BOT_TOKEN).build()

    app.add_handler(CommandHandler("getcode", getcode))

    print("✅ Sponsor Bot is running...")
    await app.run_polling()

if __name__ == "__main__":
    asyncio.run(main())

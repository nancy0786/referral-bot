# handlers/session.py
from telegram import Bot
from utils.db import get_user_data, clear_active_messages
import time, os

CHECK_INTERVAL = 60  # seconds
EXPIRY_TIME = 30 * 60  # 30 minutes

async def check_sessions(context):
    bot: Bot = context.bot
    db_folder = "db"
    now = time.time()

    if not os.path.exists(db_folder):
        return

    for filename in os.listdir(db_folder):
        # Only process .json files
        if not filename.endswith(".json"):
            continue

        user_str = filename.replace(".json", "")

        # Skip files that are not numeric (like 'tasks.json')
        if not user_str.isdigit():
            continue

        user_id = int(user_str)

        # Await the coroutine to get actual user_data
        user_data = await get_user_data(user_id)
        last_active = user_data.get("last_active", now)

        if now - last_active >= EXPIRY_TIME and user_data.get("active_messages"):
            try:
                for msg_id in user_data["active_messages"]:
                    try:
                        await bot.delete_message(chat_id=user_id, message_id=msg_id)
                    except:
                        pass
                await bot.send_message(chat_id=user_id, text="⏳ Session expired. Use /start to begin again.")
                await clear_active_messages(user_id)
            except:
                pass

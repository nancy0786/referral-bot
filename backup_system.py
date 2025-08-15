import os
import shutil
import asyncio
from config import DATA_FOLDER, BACKUP_CHANNEL_ID, BOT_TOKEN
from telegram import Bot

# Local backup folder inside bot directory
BACKUP_FOLDER = os.path.join(DATA_FOLDER, "backups")
os.makedirs(BACKUP_FOLDER, exist_ok=True)

async def backup_user_data(user_id, user_file_path):
    """
    Creates a local backup of the user's data file and sends it to the backup channel (if set).
    """
    # 1. Local backup copy
    backup_path = os.path.join(BACKUP_FOLDER, f"{user_id}.json")
    shutil.copy(user_file_path, backup_path)
    print(f"[Backup] Local backup created for user {user_id} at {backup_path}")

    # 2. Upload to Telegram backup channel
    if BACKUP_CHANNEL_ID and BOT_TOKEN:
        try:
            bot = Bot(token=BOT_TOKEN)
            await bot.send_document(
                chat_id=BACKUP_CHANNEL_ID,
                document=open(backup_path, "rb"),
                caption=f"Backup for user {user_id}"
            )
            print(f"[Backup] User {user_id} backup sent to Telegram channel {BACKUP_CHANNEL_ID}")
        except Exception as e:
            print(f"[Backup] Failed to send backup to Telegram: {e}")

# If some places call backup_user_data synchronously, wrap it
def backup_user_data_sync(user_id, user_file_path):
    asyncio.run(backup_user_data(user_id, user_file_path))

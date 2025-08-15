# utils/backup_user.py
import os
import shutil
import asyncio
from config import DATA_FOLDER, BACKUP_CHANNEL_ID, BOT_TOKEN
from telegram import Bot

# Local backup folder inside bot directory
BACKUP_FOLDER = os.path.join(DATA_FOLDER, "backups")
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# Keep track of last Telegram message per user
USER_MESSAGE_ID_FILE = os.path.join(BACKUP_FOLDER, "user_messages.json")

import json

def load_user_messages():
    if not os.path.exists(USER_MESSAGE_ID_FILE):
        return {}
    with open(USER_MESSAGE_ID_FILE, "r") as f:
        try:
            return json.load(f)
        except:
            return {}

def save_user_messages(data):
    with open(USER_MESSAGE_ID_FILE, "w") as f:
        json.dump(data, f, indent=2)

async def backup_user_data(user_id, user_file_path):
    """
    Creates a local backup of the user's data file and sends it to the backup channel (if set),
    deleting the previous backup message if exists.
    """
    # 1️⃣ Local backup copy
    backup_path = os.path.join(BACKUP_FOLDER, f"{user_id}.json")
    shutil.copy(user_file_path, backup_path)
    print(f"[Backup] Local backup created for user {user_id} at {backup_path}")

    # 2️⃣ Upload to Telegram backup channel
    if BACKUP_CHANNEL_ID and BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN)
        user_messages = load_user_messages()
        prev_msg_id = user_messages.get(str(user_id))

        # Delete previous backup message if exists
        if prev_msg_id:
            try:
                await bot.delete_message(chat_id=BACKUP_CHANNEL_ID, message_id=prev_msg_id)
                print(f"[Backup] Deleted previous backup message {prev_msg_id} for user {user_id}")
            except Exception as e:
                print(f"[Backup] Could not delete previous message {prev_msg_id}: {e}")

        # Send new backup
        try:
            sent = await bot.send_document(
                chat_id=BACKUP_CHANNEL_ID,
                document=open(backup_path, "rb"),
                caption=f"Backup for user {user_id}"
            )
            # Save new message_id
            user_messages[str(user_id)] = sent.message_id
            save_user_messages(user_messages)
            print(f"[Backup] User {user_id} backup sent to Telegram channel {BACKUP_CHANNEL_ID}")
        except Exception as e:
            print(f"[Backup] Failed to send backup to Telegram: {e}")

# Synchronous wrapper
def backup_user_data_sync(user_id, user_file_path):
    asyncio.run(backup_user_data(user_id, user_file_path))

# utils/backup_system.py
import os
import shutil
import json
import aiofiles
import asyncio
from config import DATA_FOLDER, BACKUP_CHANNEL_ID, BOT_TOKEN
from telegram import Bot
from telegram.constants import ChatAction

# Local backup folder inside bot directory
BACKUP_FOLDER = os.path.join(DATA_FOLDER, "backups")
os.makedirs(BACKUP_FOLDER, exist_ok=True)

# Track last Telegram message per user
USER_MESSAGE_ID_FILE = os.path.join(BACKUP_FOLDER, "user_messages.json")


async def load_user_messages() -> dict:
    """Load the mapping of user_id -> last backup message id"""
    if not os.path.exists(USER_MESSAGE_ID_FILE):
        return {}
    async with aiofiles.open(USER_MESSAGE_ID_FILE, "r", encoding="utf-8") as f:
        try:
            text = await f.read()
            return json.loads(text)
        except:
            return {}


async def save_user_messages(data: dict):
    """Save the mapping of user_id -> last backup message id"""
    tmp_file = USER_MESSAGE_ID_FILE + ".tmp"
    async with aiofiles.open(tmp_file, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))
    os.replace(tmp_file, USER_MESSAGE_ID_FILE)


async def backup_user_data(user_id: int, user_file_path: str):
    """
    Backup a user's data:
      1️⃣ Local backup in /backups
      2️⃣ Upload to Telegram backup channel (single file per user)
         -> Deletes old backup message first
         -> Only sends if content changed
    """
    # 1️⃣ Local backup copy
    backup_path = os.path.join(BACKUP_FOLDER, f"{user_id}.json")

    # Check if file changed
    send_backup = True
    if os.path.exists(backup_path):
        async with aiofiles.open(backup_path, "r", encoding="utf-8") as f:
            old_data = await f.read()
        async with aiofiles.open(user_file_path, "r", encoding="utf-8") as f:
            new_data = await f.read()
        if old_data == new_data:
            send_backup = False  # No changes, skip sending

    shutil.copy(user_file_path, backup_path)
    print(f"[Backup] Local backup created for user {user_id} at {backup_path}")

    if not send_backup:
        print(f"[Backup] No changes detected for user {user_id}, skipping Telegram upload")
        return

    # 2️⃣ Telegram backup
    if BACKUP_CHANNEL_ID and BOT_TOKEN:
        bot = Bot(token=BOT_TOKEN)
        user_messages = await load_user_messages()
        prev_msg_id = user_messages.get(str(user_id))

        # Delete old backup message
        if prev_msg_id:
            try:
                await bot.delete_message(chat_id=BACKUP_CHANNEL_ID, message_id=prev_msg_id)
                print(f"[Backup] Deleted previous backup message {prev_msg_id} for user {user_id}")
            except Exception as e:
                print(f"[Backup] Could not delete previous message {prev_msg_id}: {e}")

        # Send new backup
        try:
            async with aiofiles.open(backup_path, "rb") as f:
                data_bytes = await f.read()

            sent = await bot.send_document(
                chat_id=BACKUP_CHANNEL_ID,
                document=data_bytes,
                filename=f"{user_id}.json",
                caption=f"Backup for user {user_id}"
            )

            # Save new message id
            user_messages[str(user_id)] = sent.message_id
            await save_user_messages(user_messages)
            print(f"[Backup] User {user_id} backup sent to Telegram channel {BACKUP_CHANNEL_ID}")

        except Exception as e:
            print(f"[Backup] Failed to send backup to Telegram: {e}")
def backup_user_data_sync(user_id: int, user_file_path: str):
    """Synchronous wrapper"""
    asyncio.run(backup_user_data(user_id, user_file_path))

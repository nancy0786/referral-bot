# utils/backup.py
import json
import time
import asyncio
from typing import Dict, Any, Optional
from telegram import Bot
import config

# The pinned message in the backup channel contains JSON: { user_id: {file_id, message_id, uploaded_at, filename} }
# We will edit that pinned message text whenever index changes.

async def _get_bot() -> Bot:
    return Bot(token=config.BOT_TOKEN)

async def read_index_from_pinned(bot: Bot) -> Dict[str, Any]:
    """Read the JSON index from the pinned message in the channel."""
    if config.PRIVATE_DB_CHANNEL_ID == 0:
        return {}
    try:
        chat = await bot.get_chat(config.PRIVATE_DB_CHANNEL_ID)
        pinned = chat.pinned_message
        if not pinned or not pinned.text:
            return {}
        text = pinned.text
        try:
            data = json.loads(text)
            if isinstance(data, dict):
                return data
            return {}
        except Exception:
            return {}
    except Exception:
        return {}

async def write_index_to_pinned(bot: Bot, index: Dict[str, Any]) -> None:
    """Send or edit the pinned message with the index JSON. If not exists, create and pin it."""
    if config.PRIVATE_DB_CHANNEL_ID == 0:
        return
    text = json.dumps(index, ensure_ascii=False, indent=2)
    try:
        chat = await bot.get_chat(config.PRIVATE_DB_CHANNEL_ID)
        pinned = chat.pinned_message
        # If pinned exists and bot is the author (message.from_user is bot), edit it
        if pinned and pinned.from_user and pinned.from_user.id == (await bot.get_me()).id:
            try:
                await bot.edit_message_text(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=pinned.message_id, text=text)
                return
            except Exception:
                # fallthrough to send a new message
                pass

        # Else send a new index message and pin it
        msg = await bot.send_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, text=text)
        try:
            await bot.pin_chat_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=msg.message_id, disable_notification=True)
        except Exception:
            # ignore pin failures
            pass
    except Exception as e:
        # ignore failures to avoid breaking user saves
        print("write_index_to_pinned error:", e)

async def update_user_backup(user_id: int, local_filepath: str) -> None:
    """
    Uploads local_filepath to the backup channel, removes previous backup for user if exists,
    and updates the pinned index accordingly.
    """
    if config.PRIVATE_DB_CHANNEL_ID == 0:
        return

    bot = await _get_bot()

    # read current index
    index = await read_index_from_pinned(bot)

    str_uid = str(user_id)
    prev = index.get(str_uid)

    # Delete previous message if exists
    if prev and "message_id" in prev:
        try:
            await bot.delete_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=int(prev["message_id"]))
        except Exception:
            # ignore deletion errors
            pass

    # upload new file
    try:
        with open(local_filepath, "rb") as f:
            sent = await bot.send_document(chat_id=config.PRIVATE_DB_CHANNEL_ID, document=f, filename=f"{user_id}.json", caption=f"Backup for user {user_id} at {int(time.time())}")
        # update index entry
        index[str_uid] = {
            "file_id": sent.document.file_id,
            "message_id": sent.message_id,
            "uploaded_at": int(time.time()),
            "filename": f"{user_id}.json"
        }
        # write/replace pinned index
        await write_index_to_pinned(bot, index)
    except Exception as e:
        print("update_user_backup error:", e)


async def restore_all_from_index() -> Dict[str, str]:
    """
    Downloads all files referenced in pinned index into local DB folder.
    Returns dict {user_id: 'ok'/'error:...'}.
    """
    results = {}
    if config.PRIVATE_DB_CHANNEL_ID == 0:
        return results

    bot = await _get_bot()
    index = await read_index_from_pinned(bot)
    import os
    os.makedirs(config.DATA_FOLDER, exist_ok=True)

    for str_uid, info in index.items():
        try:
            file_id = info.get("file_id")
            if not file_id:
                results[str_uid] = "no_file_id"
                continue
            tfile = await bot.get_file(file_id)
            local_path = f"{config.DATA_FOLDER}/{str_uid}.json"
            await tfile.download_to_drive(custom_path=local_path)
            results[str_uid] = "ok"
        except Exception as e:
            results[str_uid] = f"error: {e}"
    return results

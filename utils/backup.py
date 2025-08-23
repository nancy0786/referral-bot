# utils/backup.py
import json
import time
import asyncio
from typing import Dict, Any
from telegram import Bot
import config
import os

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
        try:
            data = json.loads(pinned.text)
            return data if isinstance(data, dict) else {}
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
        if pinned:  # allow edit even if not authored by this bot
            try:
                await bot.edit_message_text(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=pinned.message_id, text=text)
                return
            except Exception:
                pass
        # else send a new index
        msg = await bot.send_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, text=text)
        try:
            await bot.pin_chat_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=msg.message_id, disable_notification=True)
        except Exception:
            pass
    except Exception as e:
        print("write_index_to_pinned error:", e)

async def update_user_backup(user_id: int, local_filepath: str, new_data: Dict[str, Any]) -> None:
    """
    Uploads user backup: both JSON file and JSON text.
    Deletes previous ones if exists. Only uploads if changed.
    """
    if config.PRIVATE_DB_CHANNEL_ID == 0:
        return

    bot = await _get_bot()
    index = await read_index_from_pinned(bot)
    str_uid = str(user_id)
    prev = index.get(str_uid)

    # Exclude trivial fields from change detection
    ignore_keys = ["last_active", "active_messages"]
    filtered_new_data = {k: v for k, v in new_data.items() if k not in ignore_keys}

    # Check if data has changed
    old_json = None
    if prev and "last_data" in prev:
        try:
            old_data = json.loads(prev["last_data"])
            filtered_old_data = {k: v for k, v in old_data.items() if k not in ignore_keys}
            old_json = filtered_old_data
        except Exception:
            pass
    if old_json == filtered_new_data:
        # No significant change, skip upload
        return

    # Delete previous messages if exist
    if prev:
        for key in ("file_message_id", "text_message_id"):
            if key in prev:
                try:
                    await bot.delete_message(chat_id=config.PRIVATE_DB_CHANNEL_ID, message_id=int(prev[key]))
                except Exception:
                    pass

    # Upload new JSON file
    try:
        with open(local_filepath, "rb") as f:
            file_msg = await bot.send_document(
                chat_id=config.PRIVATE_DB_CHANNEL_ID,
                document=f,
                filename=f"{user_id}.json",
                caption=f"Backup file for user {user_id} at {int(time.time())}"
            )
    except Exception as e:
        print("update_user_backup file upload error:", e)
        return

    # Upload new JSON text (pretty-printed)
    try:
        text_str = json.dumps(new_data, ensure_ascii=False, indent=2)
        text_msg = await bot.send_message(
            chat_id=config.PRIVATE_DB_CHANNEL_ID,
            text=(
                f"User {user_id} details:\n"
                f"Name: {new_data.get('username')}\n"
                f"Plan: {new_data.get('plan', {}).get('name') if isinstance(new_data.get('plan'), dict) else new_data.get('plan')}\n"
                f"Credits: {new_data.get('credits', 0)}\n"
                f"ID: {user_id}\n"
                f"<pre>{text_str}</pre>"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        print("update_user_backup text upload error:", e)
        text_msg = None

    # Update index
    index[str_uid] = {
        "file_message_id": file_msg.message_id,
        "text_message_id": text_msg.message_id if text_msg else None,
        "uploaded_at": int(time.time()),
        "filename": f"{user_id}.json",
        "last_data": json.dumps(new_data, ensure_ascii=False)  # keep raw data for change detection
    }
    await write_index_to_pinned(bot, index)
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
    os.makedirs(config.DATA_FOLDER, exist_ok=True)

    for str_uid, info in index.items():
        try:
            file_msg_id = info.get("file_message_id")
            if not file_msg_id:
                results[str_uid] = "no_file_message"
                continue
            # simplified manual restore
            results[str_uid] = "manual restore needed"
        except Exception as e:
            results[str_uid] = f"error: {e}"

    # Second block for actual file download if file_id exists
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

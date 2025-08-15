import json
from pathlib import Path
from typing import Any, Dict, Optional
import aiofiles

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

DEFAULT_USER = {
    "user_id": None,
    "username": None,
    "credits": 0,
    "plan": {"name": "Free", "expires_at": None},
    "usage": {"videos_watched_today": 0, "last_watch_reset": None},
    "referrals": {
        "invited_by": None,
        "total": 0,
        "successful": 0,
        "pending": []
    },
    "badges": []
}

def _user_path(user_id: int) -> Path:
    return DATA_DIR / f"{user_id}.json"

async def get_user(user_id: int, username: Optional[str] = None) -> Dict[str, Any]:
    p = _user_path(user_id)
    if not p.exists():
        data = {**DEFAULT_USER, "user_id": user_id, "username": username}
        await save_user(user_id, data)
        return data

    async with aiofiles.open(p, "r", encoding="utf-8") as f:
        raw = await f.read()
    try:
        data = json.loads(raw)
    except Exception:
        data = {**DEFAULT_USER, "user_id": user_id, "username": username}
    if username:
        data["username"] = username
    return data

async def save_user(user_id: int, data: Dict[str, Any]) -> None:
    p = _user_path(user_id)
    async with aiofiles.open(p, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

async def set_invited_by(user_id: int, inviter_id: int) -> None:
    data = await get_user(user_id)
    if data["referrals"].get("invited_by") is None and inviter_id != user_id:
        data["referrals"]["invited_by"] = inviter_id
        await save_user(user_id, data)

async def add_pending_referral(inviter_id: int, referred_user_id: int) -> None:
    inviter = await get_user(inviter_id)
    pend = set(inviter["referrals"].get("pending", []))
    if referred_user_id != inviter_id and referred_user_id not in pend:
        pend.add(referred_user_id)
        inviter["referrals"]["pending"] = list(pend)
        await save_user(inviter_id, inviter)


        DEFAULT_USER = {
    "user_id": None,
    "username": None,
    "credits": 0,
    "plan": {"name": "Free", "expires_at": None},
    "usage": {"videos_watched_today": 0, "last_watch_reset": None},
    "referrals": {
        "invited_by": None,
        "total": 0,
        "successful": 0,
        "pending": []
    },
    "badges": [],
    "sponsor_verified": False  # <-- NEW
}        


import json, os, time

DB_PATH = "db"

def get_user_data(user_id):
    file_path = f"{DB_PATH}/{user_id}.json"
    if not os.path.exists(file_path):
        return {
            "credits": 0,
            "plan": "Free",
            "plan_expiry": None,
            "referrals": [],
            "badges": [],
            "redeemed_codes": [],
            "usage_today": 0,
            "last_reset": time.time(),
            "sponsor_verified": False,
            "last_active": time.time(),
            "active_messages": []
        }
    with open(file_path, "r") as f:
        return json.load(f)

def save_user_data(user_id, data):
    os.makedirs(DB_PATH, exist_ok=True)
    with open(f"{DB_PATH}/{user_id}.json", "w") as f:
        json.dump(data, f)

def update_last_active(user_id):
    data = get_user_data(user_id)
    data["last_active"] = time.time()
    save_user_data(user_id, data)

def add_active_message(user_id, message_id):
    data = get_user_data(user_id)
    if message_id not in data["active_messages"]:
        data["active_messages"].append(message_id)
    save_user_data(user_id, data)

def clear_active_messages(user_id):
    data = get_user_data(user_id)
    data["active_messages"] = []
    save_user_data(user_id, data)


# utils/db.py
import json
import aiofiles
import os
import time
from typing import Dict, Any, Optional
import config
from . import backup

os.makedirs(config.DATA_FOLDER, exist_ok=True)

DEFAULT_USER = {
    "user_id": None,
    "username": None,
    "credits": 0,
    "plan": {"name": "Free", "expires_at": None},
    "usage": {"videos_watched_today": 0, "last_watch_reset": None},
    "referrals": {"invited_by": None, "total": 0, "successful": 0, "pending": []},
    "badges": [],
    "sponsor_verified": False,
    "tasks_completed": [],
    "giveaways_joined": [],
    "last_active": int(time.time()),
    "active_messages": []
}

def _path_for(user_id: int) -> str:
    return os.path.join(config.DATA_FOLDER, f"{user_id}.json")

async def get_user(user_id: int, username: Optional[str] = None) -> Dict[str, Any]:
    path = _path_for(user_id)
    if not os.path.exists(path):
        # Try to get from backup channel if exists
        # We'll attempt restore of only this user by reading pinned index first
        # If present, backup.restore_all_from_index will download; but here we keep it simple:
        data = dict(DEFAULT_USER)
        data["user_id"] = user_id
        data["username"] = username
        await save_user(user_id, data)  # create local and backup
        return data

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        txt = await f.read()
    try:
        data = json.loads(txt)
    except Exception:
        data = dict(DEFAULT_USER)
        data["user_id"] = user_id
        data["username"] = username
    if username:
        data["username"] = username
    return data

async def save_user(user_id: int, data: Dict[str, Any], backup_sync: bool = True) -> None:
    """
    Save local user JSON and optionally sync to backup channel (backup_sync=True).
    backup_sync=True for full mirroring.
    """
    path = _path_for(user_id)
    # Ensure user_id field
    data["user_id"] = user_id
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, ensure_ascii=False, indent=2))

    # If required, update backup in channel (async, fire-and-forget)
    if backup_sync and config.PRIVATE_DB_CHANNEL_ID != 0:
        # run backup but don't block caller
        try:
            # schedule update_user_backup asynchronously
            async def _u():
                await backup.update_user_backup(user_id, path)
            # create background task
            import asyncio
            asyncio.create_task(_u())
        except Exception as e:
            print("backup schedule failed:", e)
            

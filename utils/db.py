# db.py
import os
import time
import json
import aiofiles
import asyncio
import tempfile
from typing import Dict, Any, Optional, List
import config
from . import backup  # backup.update_user_backup

# Ensure main data folder exists
os.makedirs(config.DATA_FOLDER, exist_ok=True)

# Centralized default user template
DEFAULT_USER: Dict[str, Any] = {
    "user_id": None,
    "username": None,
    "credits": 0,
    "plan": {"name": "Free", "expires_at": None},
    "videos_per_day": 0,
    "downloads_per_day": 0,
    "usage": {"videos_watched_today": 0, "last_watch_reset": None},
    "referrals": {"invited_by": None, "total": 0, "successful": 0, "pending": []},
    "ref_link": None,
    "badges": [],
    "sponsor_verified": False,
    "tasks_completed": [],
    "giveaways_joined": [],
    "last_active": 0,
    "active_messages": [],

    # 🆕 Section for video details
    "videos": {
        "fetched": [],   # video IDs fetched from database channel
        "watched": [],   # video IDs user already watched
        "tags": {}       # mapping: {video_id: ["tag1", "tag2"]}
    }
}

def _path_for(user_id: int) -> str:
    """Return local JSON path for a user"""
    return os.path.join(config.DATA_FOLDER, f"{user_id}.json")


async def get_user(user_id: int, username: Optional[str] = None) -> Dict[str, Any]:
    """Load user data asynchronously. Create new user if not exists."""
    path = _path_for(user_id)

    if not os.path.exists(path):
        data = dict(DEFAULT_USER)
        data["user_id"] = user_id
        data["username"] = username
        await save_user(user_id, data)
        return data

    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        try:
            raw = await f.read()
            data = json.loads(raw)
        except Exception:
            data = dict(DEFAULT_USER)
            data["user_id"] = user_id
            data["username"] = username

    # Ensure new fields exist for old users
    if "videos" not in data:
        data["videos"] = {"fetched": [], "watched": [], "tags": {}}

    if username:
        data["username"] = username

    return data


async def save_user(user_id: int, data: Dict[str, Any], backup_sync: bool = True) -> None:
    """
    Save user locally and optionally sync to backup channel.
    Atomic write to prevent file corruption.
    """
    path = _path_for(user_id)
    data["user_id"] = user_id

    # Atomic write to temp file first
    tmp_fd, tmp_path = tempfile.mkstemp()
    try:
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(data, ensure_ascii=False, indent=2))
        os.replace(tmp_path, path)  # replace original file atomically
    finally:
        try:
            os.close(tmp_fd)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass

    # Backup to Telegram channel (async fire-and-forget)
    if backup_sync and config.PRIVATE_DB_CHANNEL_ID != 0:
        try:
            async def _backup():
                await backup.update_user_backup(user_id, path)
            asyncio.create_task(_backup())
        except Exception as e:
            print(f"[DB Backup] Failed to schedule backup for user {user_id}: {e}")


async def set_invited_by(user_id: int, inviter_id: int) -> None:
    """Set who invited a user"""
    user = await get_user(user_id)
    if user["referrals"].get("invited_by") is None and inviter_id != user_id:
        user["referrals"]["invited_by"] = inviter_id
        await save_user(user_id, user)


async def add_pending_referral(inviter_id: int, referred_user_id: int) -> None:
    """Add a pending referral to inviter"""
    inviter = await get_user(inviter_id)
    pending_set = set(inviter["referrals"].get("pending", []))
    if referred_user_id != inviter_id and referred_user_id not in pending_set:
        pending_set.add(referred_user_id)
        inviter["referrals"]["pending"] = list(pending_set)
        await save_user(inviter_id, inviter)


async def update_last_active(user_id: int) -> None:
    """Update last active timestamp"""
    user = await get_user(user_id)
    user["last_active"] = int(time.time())
    await save_user(user_id, user)


async def add_active_message(user_id: int, message_id: int) -> None:
    """Track currently active messages"""
    user = await get_user(user_id)
    if message_id not in user["active_messages"]:
        user["active_messages"].append(message_id)
    await save_user(user_id, user)


async def clear_active_messages(user_id: int) -> None:
    """Clear all active messages"""
    user = await get_user(user_id)
    user["active_messages"] = []
    await save_user(user_id, user)



# 🆕 ---------------- VIDEO MANAGEMENT ----------------

async def add_fetched_video(user_id: int, video_id: int, tags: Optional[List[str]] = None):
    """Add a fetched video with optional tags"""
    user = await get_user(user_id)
    if video_id not in user["videos"]["fetched"]:
        user["videos"]["fetched"].append(video_id)
    if tags:
        user["videos"]["tags"][str(video_id)] = tags
    await save_user(user_id, user)


async def mark_video_watched(user_id: int, video_id: int):
    """Mark video as watched"""
    user = await get_user(user_id)
    if video_id not in user["videos"]["watched"]:
        user["videos"]["watched"].append(video_id)
    await save_user(user_id, user)


async def get_user_videos(user_id: int):
    """Return all video info for user"""
    user = await get_user(user_id)
    return user.get("videos", {"fetched": [], "watched": [], "tags": {}})



# Backward compatibility for older handlers
async def get_user_data(user_id: int):
    """Return user data in old-style dict format for legacy handlers."""
    user = await get_user(user_id)

    # ✅ Fix for old DB files where referrals could be a list
    referrals = user.get("referrals", {})
    if isinstance(referrals, list):  # old format
        referrals = {"pending": referrals, "completed": [], "invited_by": None, "total": 0, "successful": 0}

    return {
        "credits": user.get("credits", 0),
        "plan": user.get("plan", {}).get("name", "Free"),
        "plan_expiry": user.get("plan", {}).get("expires_at"),
        "referrals": referrals.get("pending", []),
        "badges": user.get("badges", []),
        "redeemed_codes": user.get("redeemed_codes", []),
        "usage_today": user.get("usage", {}).get("videos_watched_today", 0),
        "last_reset": user.get("usage", {}).get("last_watch_reset"),
        "sponsor_verified": user.get("sponsor_verified", False),
        "last_active": user.get("last_active", 0),
        "active_messages": user.get("active_messages", []),
        "ref_link": user.get("ref_link")   # ✅ add this
    }


async def save_user_data(user_id: int, data: dict):
    """Save user data in old-style format for legacy handlers."""
    user = await get_user(user_id)

    # ✅ Fix for old DB files where referrals could be a list
    if isinstance(user.get("referrals"), list):
        user["referrals"] = {"pending": user["referrals"], "completed": [], "invited_by": None, "total": 0, "successful": 0}

    user["credits"] = data.get("credits", user.get("credits", 0))
    user["plan"]["name"] = data.get("plan", user.get("plan", {}).get("name", "Free"))
    user["plan"]["expires_at"] = data.get("plan_expiry", user.get("plan", {}).get("expires_at"))
    user["referrals"]["pending"] = data.get("referrals", user.get("referrals", {}).get("pending", []))
    user["badges"] = data.get("badges", user.get("badges", []))
    user["redeemed_codes"] = data.get("redeemed_codes", user.get("redeemed_codes", []))
    user["usage"]["videos_watched_today"] = data.get("usage_today", user.get("usage", {}).get("videos_watched_today", 0))
    user["usage"]["last_watch_reset"] = data.get("last_reset", user.get("usage", {}).get("last_watch_reset"))
    user["sponsor_verified"] = data.get("sponsor_verified", user.get("sponsor_verified", False))
    user["last_active"] = data.get("last_active", user.get("last_active", 0))
    user["active_messages"] = data.get("active_messages", user.get("active_messages", []))

    await save_user(user_id, user)

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
import sqlite3

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
    # normalize to int to avoid fragmented files like "123" vs 123
    try:
        user_id = int(user_id)
    except Exception:
        raise ValueError("user_id must be an integer-compatible value")

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
            data = json.loads(raw) if raw else dict(DEFAULT_USER)
        except Exception:
            data = dict(DEFAULT_USER)
            data["user_id"] = user_id
            data["username"] = username

    # Ensure new fields exist for old users
    if "videos" not in data:
        data["videos"] = {"fetched": [], "watched": [], "tags": {}}

    # Backfill commonly-missing fields to avoid KeyError
    if "tasks_completed" not in data:
        data["tasks_completed"] = []
    if "tasks_opened" not in data:
        data["tasks_opened"] = {}
    if "credits" not in data:
        data["credits"] = 0
    if "usage" not in data:
        data["usage"] = {"videos_watched_today": 0, "last_watch_reset": None}
    referrals_val = data.get("referrals", {})
    if isinstance(referrals_val, list):
        # older format used a list for pending referrals — normalize to dict
        data["referrals"] = {
            "pending": referrals_val,
            "completed": [],
            "invited_by": None,
            "total": 0,
            "successful": 0
        }
    elif not referrals_val:
        data["referrals"] = {"invited_by": None, "total": 0, "successful": 0, "pending": []}

    if username:
        data["username"] = username

    # Persist backfilled structure but avoid redundant backup on read
    await save_user(user_id, data, backup_sync=False)
    return data


async def save_user(user_id: int, data: Dict[str, Any], backup_sync: bool = True) -> None:
    """
    Save user locally and optionally sync to backup channel.
    Atomic write to prevent file corruption.
    """
    # normalize id
    try:
        user_id = int(user_id)
    except Exception:
        raise ValueError("user_id must be an integer-compatible value")

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
    if backup_sync and getattr(config, "PRIVATE_DB_CHANNEL_ID", 0) != 0:
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


async def mark_video_watched(user_id: int, video_id: str):
    """Mark video as watched"""
    user = await get_user(user_id)
    if video_id not in user["videos"]["watched"]:
        user["videos"]["watched"].append(video_id)
    await save_user(user_id, user)


async def get_user_videos(user_id: int):
    """Return all video info for user"""
    user = await get_user(user_id)
    return user.get("videos", {"fetched": [], "watched": [], "tags": {}})


# ---------------- TASKS MANAGEMENT ----------------

TASKS_FILE = os.path.join(config.DATA_FOLDER, "tasks.json")

# Ensure tasks file exists
if not os.path.exists(TASKS_FILE):
    with open(TASKS_FILE, "w", encoding="utf-8") as f:
        json.dump([], f)


def _normalize_task(task: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Ensure task dict has all required fields"""
    return {
        "id": str(task.get("id", f"task_{index}")),
        "title": task.get("title", f"Task {index+1}"),
        "reward": int(task.get("reward", 0)),
        "link": task.get("link", None)
    }


async def get_all_tasks() -> List[Dict[str, Any]]:
    """Return all global tasks (safe, always valid)."""
    try:
        async with aiofiles.open(TASKS_FILE, "r", encoding="utf-8") as f:
            raw = await f.read()
            tasks = json.loads(raw) if raw else []
    except Exception:
        tasks = []

    # Normalize tasks
    tasks = [_normalize_task(t, i) for i, t in enumerate(tasks)]
    return tasks


async def save_all_tasks(tasks: List[Dict[str, Any]]):
    """Save global tasks list safely."""
    # Normalize before saving
    tasks = [_normalize_task(t, i) for i, t in enumerate(tasks)]

    tmp_fd, tmp_path = tempfile.mkstemp()
    try:
        async with aiofiles.open(tmp_path, "w", encoding="utf-8") as f:
            await f.write(json.dumps(tasks, ensure_ascii=False, indent=2))
        os.replace(tmp_path, TASKS_FILE)
    finally:
        try:
            os.close(tmp_fd)
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


async def add_task(task: Dict[str, Any]):
    """Add a new global task"""
    tasks = await get_all_tasks()
    tasks.append(task)
    await save_all_tasks(tasks)


async def delete_task(index: int):
    """Delete a task by index"""
    tasks = await get_all_tasks()
    if 0 <= index < len(tasks):
        tasks.pop(index)
        await save_all_tasks(tasks)


# 🆕 Track which tasks user opened (to enforce "open before done")
async def mark_task_opened(user_id: int, task_id: str):
    """Mark that a user has opened a task link."""
    user = await get_user(user_id)
    if "tasks_opened" not in user or not isinstance(user["tasks_opened"], dict):
        user["tasks_opened"] = {}
    user["tasks_opened"][task_id] = int(time.time())  # store open timestamp
    await save_user(user_id, user)


async def mark_task_completed(user_id: int, task_id: str, reward: int = 0):
    """Mark task as completed and credit user if valid."""
    user = await get_user(user_id)

    # Ensure opened before completion
    opened_at = user.get("tasks_opened", {}).get(task_id)
    if not opened_at:
        return False, "⚠️ You must open the task link first!"

    # Ensure at least 5s passed
    if time.time() - opened_at < 5:
        return False, "⏳ Please stay at least 5 seconds before completing."

    # Prevent double credit - ensure list exists
    if "tasks_completed" not in user or not isinstance(user["tasks_completed"], list):
        user["tasks_completed"] = []

    if task_id in user.get("tasks_completed", []):
        return False, "✅ You already completed this task!"

    # Mark completed & add credits (single-source here)
    user["tasks_completed"].append(task_id)
    user["credits"] = int(user.get("credits", 0)) + int(reward or 0)
    await save_user(user_id, user)
    return True, f"🎉 Task completed! +{int(reward or 0)} credits"


# db.py


DB_NAME = "bot_database.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Existing tables ...

    # Video Categories table
    cursor.execute('''CREATE TABLE IF NOT EXISTS video_categories (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        category_name TEXT UNIQUE,
                        video_range TEXT
                    )''')

    conn.commit()
    conn.close()


# =====================
# VIDEO CATEGORY FUNCTIONS
# =====================

def add_or_update_category(category_name: str, video_range: str):
    """Add a new category or update if already exists."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO video_categories (category_name, video_range)
                      VALUES (?, ?)
                      ON CONFLICT(category_name) DO UPDATE SET video_range=excluded.video_range''',
                   (category_name, video_range))
    conn.commit()
    conn.close()


def delete_category(category_name: str):
    """Delete a category by name."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM video_categories WHERE category_name = ?", (category_name,))
    conn.commit()
    conn.close()


def get_all_categories():
    """Return all categories as list of tuples (category_name, video_range)."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT category_name, video_range FROM video_categories ORDER BY id")
    rows = cursor.fetchall()
    conn.close()
    return rows





# Backward compatibility for older handlers
async def get_user_data(user_id: int):
    """Return user data in old-style dict format for legacy handlers."""
    user = await get_user(user_id)

    # ✅ Fix for old DB files where referrals could be a list
    referrals = user.get("referrals", {})
    if isinstance(referrals, list):  # old format safeguard
        referrals = {
            "pending": referrals,
            "completed": [],
            "invited_by": None,
            "total": 0,
            "successful": 0
        }

    # ✅ Build a proper referral summary
    ref_total = referrals.get("total", len(referrals.get("pending", [])) + len(referrals.get("completed", [])))
    ref_success = referrals.get("successful", len(referrals.get("completed", [])))

    return {
        "user_id": user.get("user_id"),
        "name": user.get("username"),
        "credits": user.get("credits", 0),
        "plan": user.get("plan", {}).get("name", "Free") if isinstance(user.get("plan"), dict) else user.get("plan", "Free"),
        "plan_expiry": user.get("plan", {}).get("expires_at") if isinstance(user.get("plan"), dict) else None,
        "referrals": referrals,
        "badges": user.get("badges", []),
        "redeemed_codes": user.get("redeemed_codes", []),
        "usage_today": user.get("usage", {}).get("videos_watched_today", 0),
        "last_reset": user.get("usage", {}).get("last_watch_reset"),
        "sponsor_verified": user.get("sponsor_verified", False),
        "last_active": user.get("last_active", 0),
        "active_messages": user.get("active_messages", []),
        "ref_link": user.get("ref_link"),
        # 🆕 Add tasks info for profile
        "tasks_completed": user.get("tasks_completed", []),
    }


async def save_user_data(user_id: int, data: dict):
    """Save user data in old-style format for legacy handlers."""
    user = await get_user(user_id)

    # ✅ Fix for old DB files where referrals could be a list
    if isinstance(user.get("referrals"), list):
        user["referrals"] = {"pending": user["referrals"], "completed": [], "invited_by": None, "total": 0, "successful": 0}

    user["credits"] = data.get("credits", user.get("credits", 0))
    # plan may be a string or dict - keep compatibility
    if isinstance(user.get("plan"), dict):
        user["plan"]["name"] = data.get("plan", user.get("plan", {}).get("name", "Free"))
        user["plan"]["expires_at"] = data.get("plan_expiry", user.get("plan", {}).get("expires_at"))
    else:
        user["plan"] = {"name": data.get("plan", user.get("plan", "Free")), "expires_at": data.get("plan_expiry")}
    user["referrals"] = data.get("referrals", user.get("referrals", {}))
    user["badges"] = data.get("badges", user.get("badges", []))
    user["redeemed_codes"] = data.get("redeemed_codes", user.get("redeemed_codes", []))
    user["usage"]["videos_watched_today"] = data.get("usage_today", user.get("usage", {}).get("videos_watched_today", 0))
    user["usage"]["last_watch_reset"] = data.get("last_reset", user.get("usage", {}).get("last_watch_reset"))
    user["sponsor_verified"] = data.get("sponsor_verified", user.get("sponsor_verified", False))
    user["last_active"] = data.get("last_active", user.get("last_active", 0))
    user["active_messages"] = data.get("active_messages", user.get("active_messages", []))
    user["tasks_completed"] = data.get("tasks_completed", user.get("tasks_completed", []))

    await save_user(user_id, user)

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

import json
import os
from datetime import datetime, timedelta
from config import DB_FOLDER, BACKUP_CHANNEL_ID
from backup_system import backup_user_data  # From Step 12
from db import get_user_data, save_user_data  # ✅ Use async DB

# Define all plans here
PLANS = {
    "free": {
        "credits": 3,
        "videos_per_day": 10,
        "downloads_per_day": 0,
        "expiry_days": None
    },
    "daily": {
        "credits": 35,
        "videos_per_day": -1,  # Unlimited
        "downloads_per_day": -1,
        "expiry_days": 1
    },
    "monthly": {
        "credits": 860,
        "videos_per_day": -1,
        "downloads_per_day": -1,
        "expiry_days": 28
    },
    "premium": {
        "credits": -1,  # Unlimited
        "videos_per_day": -1,
        "downloads_per_day": -1,
        "expiry_days": 40
    },
    "elite": {
        "credits": -1,
        "videos_per_day": -1,
        "downloads_per_day": 10,
        "expiry_days": 45
    },
    "superior": {
        "credits": -1,
        "videos_per_day": -1,
        "downloads_per_day": 25,
        "expiry_days": 60
    }
}


async def load_user(user_id):
    """Load user from async DB"""
    return await get_user_data(user_id)


async def save_user(user_id, data):
    """Save user to async DB + backup"""
    await save_user_data(user_id, data)
    path = os.path.join(DB_FOLDER, f"{user_id}.json")
    backup_user_data(user_id, path)  # Step 12 integration


async def set_plan(user_id, plan_name):
    """Assign a plan to a user"""
    user = await load_user(user_id)
    if not user:
        return False, "User not found."

    plan_name = plan_name.lower()
    if plan_name not in PLANS:
        return False, "Invalid plan name."

    plan = PLANS[plan_name]
    user["plan"] = plan_name
    user["credits"] = plan["credits"]
    user["videos_per_day"] = plan["videos_per_day"]
    user["downloads_per_day"] = plan["downloads_per_day"]

    if plan["expiry_days"]:
        user["plan_expiry"] = (datetime.now() + timedelta(days=plan["expiry_days"])).strftime("%Y-%m-%d %H:%M:%S")
    else:
        user["plan_expiry"] = None

    await save_user(user_id, user)
    return True, f"Plan '{plan_name}' set successfully."


async def check_and_update_expiry(user_id):
    """Check if user's plan expired, revert to free if needed"""
    user = await load_user(user_id)
    if not user or not user.get("plan_expiry"):
        return

    expiry_str = user.get("plan_expiry")
    if expiry_str:
        try:
            expiry_date = datetime.strptime(expiry_str, "%Y-%m-%d %H:%M:%S")
        except Exception:
            expiry_date = None
    else:
        expiry_date = None

    if expiry_date and datetime.now() > expiry_date:
        # Expired → revert to free plan
        plan = PLANS["free"]
        user["plan"] = "free"
        user["credits"] = plan["credits"]
        user["videos_per_day"] = plan["videos_per_day"]
        user["downloads_per_day"] = plan["downloads_per_day"]
        user["plan_expiry"] = None
        await save_user(user_id, user)


async def refill_free_plan_credits(user_id):
    """Refill credits for free plan users hourly"""
    user = await load_user(user_id)
    if not user or user.get("plan") != "free":
        return

    last_refill_str = user.get("last_refill", "1970-01-01 00:00:00")
    try:
        last_refill = datetime.strptime(last_refill_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        last_refill = datetime(1970, 1, 1)

    if datetime.now() - last_refill >= timedelta(hours=1):
        user["credits"] = min(user["credits"] + 3, PLANS["free"]["credits"])
        user["last_refill"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await save_user(user_id, user)

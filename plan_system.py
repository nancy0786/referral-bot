import json
import os
from datetime import datetime, timedelta
from config import DB_FOLDER, BACKUP_CHANNEL_ID
from backup_system import backup_user_data  # From Step 12
 

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


def load_user_sync(user_id):
    """Load user's JSON file synchronously (for internal use)"""
    path = os.path.join(DB_FOLDER, f"{user_id}.json")
    if os.path.exists(path):
        with open(path, "r") as f:
            return json.load(f)
    return None


def save_user_sync(user_id, data):
    """Save user data synchronously (internal use)"""
    path = os.path.join(DB_FOLDER, f"{user_id}.json")
    with open(path, "w") as f:
        json.dump(data, f, indent=4)
    backup_user_data(user_id, path)


def set_plan(user_id, plan_name):
    """Assign a plan to a user"""
    user = load_user_sync(user_id)
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

    save_user_sync(user_id, user)
    return True, f"Plan '{plan_name}' set successfully."


# ------------------ Async functions ------------------

async def check_and_update_expiry(user_id):
    """Check if user's plan expired, revert to free if needed"""
    user = await get_user_data(user_id)
    if not user or not user.get("plan_expiry"):
        return

    expiry_timestamp = user.get("plan_expiry")
    if expiry_timestamp:
        if isinstance(expiry_timestamp, int):
            expiry_date = datetime.fromtimestamp(expiry_timestamp)
        else:
            expiry_date = datetime.strptime(expiry_timestamp, "%Y-%m-%d %H:%M:%S")
    else:
        expiry_date = None

    if expiry_date and datetime.now() > expiry_date:
        # Revert to free plan
        plan = PLANS["free"]
        user["plan"] = "free"
        user["credits"] = plan["credits"]
        user["videos_per_day"] = plan["videos_per_day"]
        user["downloads_per_day"] = plan["downloads_per_day"]
        user["plan_expiry"] = None
        await save_user_data(user_id, user)


async def refill_free_plan_credits(user_id):
    """Refill credits for free plan users hourly"""
    user = await get_user_data(user_id)
    if not user or user.get("plan") != "free":
        return

    last_refill_str = user.get("last_refill", "1970-01-01 00:00:00")
    last_refill = datetime.strptime(last_refill_str, "%Y-%m-%d %H:%M:%S")

    if datetime.now() - last_refill >= timedelta(hours=1):
        user["credits"] = min(user.get("credits", 0) + 3, PLANS["free"]["credits"])
        user["last_refill"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        await save_user_data(user_id, user)

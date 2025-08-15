import os
import json
from config import DB_FOLDER
from plan_system import PLANS
from datetime import datetime
from backup_system import backup_user_data

def ensure_user_registered(user_id, user_obj):
    path = os.path.join(DB_FOLDER, f"{user_id}.json")
    if not os.path.exists(path):
        data = {
            "user_id": user_id,
            "name": user_obj.full_name,
            "username": user_obj.username,
            "plan": "free",
            "credits": PLANS["free"]["credits"],
            "videos_per_day": PLANS["free"]["videos_per_day"],
            "downloads_per_day": PLANS["free"]["downloads_per_day"],
            "last_refill": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "plan_expiry": None
        }
        with open(path, "w") as f:
            json.dump(data, f, indent=4)
        backup_user_data(user_id, path)  # Step 12 backup

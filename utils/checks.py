# utils/checks.py

import datetime
from handlers.force_join import is_member, prompt_join
from utils.db import get_user, save_user
from plan_system import PLANS


async def check_plan(user: dict):
    """Check user plan limits and expiry."""
    plan_data = user.get("plan", {})

    # 🔧 Fix: If plan is stored as string, wrap it in dict
    if isinstance(plan_data, str):
        plan_data = {"name": plan_data}
        user["plan"] = plan_data   # keep DB consistent

    plan_name = plan_data.get("name", "free")
    plan = PLANS.get(plan_name.lower(), PLANS["free"])
    
    # Ensure start_date exists
    plan_start = user.get("plan", {}).get("start_date")
    if not plan_start:
        user.setdefault("plan", {})["start_date"] = datetime.datetime.utcnow().isoformat()
        await save_user(user.get("user_id"), user)
        plan_start = user["plan"]["start_date"]

    # Check expiry
    expiry_days = plan.get("expiry_days")
    if expiry_days:
        plan_start_date = datetime.datetime.fromisoformat(plan_start)
        if datetime.datetime.utcnow() > plan_start_date + datetime.timedelta(days=expiry_days):
            return False, f"⚠️ Your {plan_name} plan has expired. Upgrade to continue using the bot."

    # Reset daily counters if needed
    today = datetime.date.today()
    last_reset = user.get("usage", {}).get("last_watch_reset")
    if last_reset != str(today):
        user.setdefault("usage", {})["videos_watched_today"] = 0
        user["usage"]["downloads_per_day"] = 0
        user["usage"]["last_watch_reset"] = str(today)
        await save_user(user.get("user_id"), user)

    # Check videos per day
    videos_per_day = plan.get("videos_per_day", -1)
    videos_watched = user.get("usage", {}).get("videos_watched_today", 0)
    if videos_per_day != -1 and videos_watched >= videos_per_day:
        return False, f"⚠️ Your {plan_name} plan allows only {videos_per_day} videos per day. Wait until tomorrow or upgrade your plan."

    # Check downloads per day
    downloads_limit = plan.get("downloads_per_day", -1)
    downloads_done = user.get("usage", {}).get("downloads_per_day", 0)
    if downloads_limit != -1 and downloads_done >= downloads_limit:
        return False, f"⚠️ Your {plan_name} plan allows only {downloads_limit} downloads per day. Wait until tomorrow or upgrade your plan."

    # Check credits
    credits_limit = plan.get("credits", -1)
    if credits_limit != -1 and user.get("credits", 0) >= credits_limit:
        return False, f"⚠️ Your {plan_name} plan allows max {credits_limit} credits. Upgrade your plan to earn more."

    return True, None


async def ensure_access(update, context):
    """Ensure user has completed force join, sponsor verification, and plan limits."""
    user = update.effective_user
    user_id = user.id

    # 1️⃣ Force Join
    if not await is_member(context, user_id):
        await prompt_join(update, context)
        return False

    # 2️⃣ Sponsor Verification
    profile = await get_user(user_id)
    if not profile.get("sponsor_verified", False):
        await ask_sponsor_verification(update, context)
        return False

    # 3️⃣ Plan validation
    ok, msg = await check_plan(profile)
    if not ok:
        await update.message.reply_text(msg)
        return False

    return True

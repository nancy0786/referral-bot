import datetime
from telegram import Update
from telegram.ext import ContextTypes
from handlers.force_join import is_member, prompt_join
from utils.db import get_user, save_user, set_invited_by, add_pending_referral
import config
import os

def load_welcome_text() -> str:
    if os.path.exists(config.WELCOME_FILE):
        with open(config.WELCOME_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "👋 Welcome!"

async def log_new_user(context: ContextTypes.DEFAULT_TYPE, user: Update.effective_user, ref: str):
    if config.LOG_CHANNEL_ID != 0:
        text = (
            "📥 **New User Started Bot**\n"
            f"👤 Name: {user.full_name}\n"
            f"🆔 ID: `{user.id}`\n"
            f"🔗 Username: @{user.username if user.username else 'None'}\n"
            f"👥 Referral: `{ref if ref else 'None'}`\n"
            f"⏰ Time: {datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC"
        )
        await context.bot.send_message(config.LOG_CHANNEL_ID, text, parse_mode="Markdown")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    user_id = user.id
    username = user.username

    profile = await get_user(user_id, username=username)

    ref_code = None
    if context.args:
        ref = context.args[0]
        if ref.isdigit():
            ref_id = int(ref)
            ref_code = ref
            if ref_id != user_id and profile["referrals"].get("invited_by") is None:
                await set_invited_by(user_id, ref_id)
                await add_pending_referral(ref_id, user_id)

    if not await is_member(context, user_id):
        await prompt_join(update, context)
        await log_new_user(context, user, ref_code)
        return

    welcome_msg = load_welcome_text()
    await update.message.reply_text(welcome_msg)

    await save_user(user_id, profile)
    await log_new_user(context, user, ref_code)



from handlers.sponsor_verify import ask_sponsor_verification

# ...
if not await is_member(context, user_id):
    await prompt_join(update, context)
    await log_new_user(context, user, ref_code)
    return

# Sponsor verification check
if not profile.get("sponsor_verified", False):
    await ask_sponsor_verification(update, context)
    await log_new_user(context, user, ref_code)
    return


from handlers.menu import send_main_menu

# ...
# After force join + sponsor verification passed:
await send_main_menu(update, context)
await log_new_user(context, user, ref_code)


from utils.db import get_user_data, save_user_data

REFERRAL_CREDIT = 2
BADGE_LEVELS = {1: "Referrer Lv1", 5: "Referrer Lv2", 10: "Referrer Lv3"}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    # Handle referral
    if args:
        try:
            ref_id = int(args[0])
            if ref_id != user_id:  # prevent self-referral
                ref_data = get_user_data(ref_id)
                if user_id not in ref_data.get("referrals", []):
                    ref_data.setdefault("referrals", []).append(user_id)
                    ref_data["credits"] = ref_data.get("credits", 0) + REFERRAL_CREDIT

                    # Badge logic
                    total_refs = len(ref_data["referrals"])
                    if total_refs in BADGE_LEVELS:
                        if BADGE_LEVELS[total_refs] not in ref_data.get("badges", []):
                            ref_data.setdefault("badges", []).append(BADGE_LEVELS[total_refs])

                    save_user_data(ref_id, ref_data)
        except ValueError:
            pass

    # Continue existing /start flow
    # ... rest of Step 1 code ...

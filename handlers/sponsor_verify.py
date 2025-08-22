# handlers/sponsor_verify.py

import random
import string
from telegram import Update
from telegram.ext import ContextTypes
from utils.db import get_user, save_user

def generate_code(length=6):
    """Generate random sponsor verification code."""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

async def getcode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /getcode in Sponsor Bot."""
    user = update.effective_user
    user_id = user.id

    profile = await get_user(user_id)
    if profile is None:
        profile = {
            "id": user_id,
            "username": user.username,
            "sponsor_verified": False,
            "sponsor_code": None
        }

    # generate a fresh code
    code = generate_code()
    profile["sponsor_code"] = code
    await save_user(user_id, profile)

    await update.message.reply_text(
        f"✅ Here is your sponsor verification code:\n\n"
        f"`{code}`\n\n"
        "👉 Now send this code to the main bot using `/verify <code>`",
        parse_mode="Markdown"
    )

async def verify_code(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /verify in Main Bot (checks code saved by Sponsor Bot)."""
    user = update.effective_user
    user_id = user.id
    profile = await get_user(user_id)

    if not context.args:
        await update.message.reply_text("⚠️ Usage: `/verify CODE`", parse_mode="Markdown")
        return

    # normalize user input
    code_entered = context.args[0].strip().upper()

    if profile and profile.get("sponsor_code") == code_entered:
        profile["sponsor_verified"] = True
        profile["sponsor_code"] = None   # 🔑 clear the code after use
        await save_user(user_id, profile)
        await update.message.reply_text("🎉 Verification successful! You are now sponsor verified.")
    else:
        await update.message.reply_text("❌ Invalid code. Please try again.")

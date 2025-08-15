# handlers/admin_restore.py
from telegram import Update
from telegram.ext import ContextTypes
import config
from utils.backup import restore_all_from_index

async def restore_db_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id not in config.ADMIN_IDS:
        await update.message.reply_text("❌ You are not authorized.")
        return

    await update.message.reply_text("🔄 Starting restore from backup channel. This might take a while...")
    results = await restore_all_from_index()
    ok_count = sum(1 for v in results.values() if v == "ok")
    await update.message.reply_text(f"✅ Restore complete. Files restored: {ok_count}. See details in logs.")

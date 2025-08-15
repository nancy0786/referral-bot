from plan_system import set_plan
from telegram import Update
from telegram.ext import CallbackContext

def admin_set_plan(update: Update, context: CallbackContext):
    if str(update.effective_user.id) not in context.bot_data.get("ADMINS", []):
        return update.message.reply_text("❌ You are not an admin.")

    if len(context.args) < 2:
        return update.message.reply_text("Usage: /set_plan <user_id> <plan_name>")

    user_id = context.args[0]
    plan_name = context.args[1]
    success, msg = set_plan(user_id, plan_name)
    update.message.reply_text(msg)

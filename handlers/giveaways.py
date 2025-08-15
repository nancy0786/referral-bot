from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from utils.db import get_user_data, save_user_data
from datetime import datetime

# Example giveaways
giveaways = [
    {
        "id": "giveaway1",
        "title": "🎁 Win 10 Credits!",
        "reward": {"credits": 10},
        "end_time": "2025-08-20 18:00:00",
        "participants": []
    },
]

def parse_time(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")

async def show_giveaways(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_data = get_user_data(user_id)

    text = "🎯 **Active Giveaways**\n\n"
    buttons = []

    for g in giveaways:
        end_time = parse_time(g["end_time"])
        joined = g["id"] in user_data.get("giveaways_joined", [])
        status = "✅ Joined" if joined else "🎉 Join"
        if datetime.utcnow() > end_time:
            status = "❌ Ended"

        text += f"{g['title']} - Ends: {g['end_time']}\nStatus: {status}\n\n"
        if status != "❌ Ended":
            buttons.append([InlineKeyboardButton(status, callback_data=f"join_{g['id']}")])

    markup = InlineKeyboardMarkup(buttons) if buttons else None

    msg = update.message or update.callback_query.message
    await msg.reply_text(text, reply_markup=markup, parse_mode="Markdown")

async def handle_giveaway_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data
    user_id = query.from_user.id
    user_data = get_user_data(user_id)

    if data.startswith("join_"):
        gid = data.split("_")[1]
        g = next((x for x in giveaways if x["id"] == gid), None)
        if not g:
            await query.answer("❌ Giveaway not found", show_alert=True)
            return

        if gid in user_data.get("giveaways_joined", []):
            await query.answer("✅ Already joined", show_alert=True)
            return

        if datetime.utcnow() > parse_time(g["end_time"]):
            await query.answer("❌ Giveaway ended", show_alert=True)
            return

        # Add user to giveaway
        g["participants"].append(user_id)
        user_data.setdefault("giveaways_joined", []).append(gid)

        # Give reward
        for k, v in g["reward"].items():
            user_data[k] = user_data.get(k, 0) + v

        save_user_data(user_id, user_data)
        await query.answer("🎉 You joined and got your reward!", show_alert=True)

        # Update button
        await query.edit_message_reply_markup(
            InlineKeyboardMarkup([[InlineKeyboardButton("✅ Joined", callback_data=f"join_{gid}")]])
        )

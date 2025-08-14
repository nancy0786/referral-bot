async def send_referral_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    bot_username = (await context.bot.get_me()).username
    link = f"https://t.me/{bot_username}?start={user_id}"
    await update.callback_query.edit_message_text(
        f"📢 *Your Referral Link:*\n{link}\n\n"
        f"Share this link with friends to earn credits & badges!",
        parse_mode="Markdown"
    )

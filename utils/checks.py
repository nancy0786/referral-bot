# utils/checks.py

from handlers.force_join import is_member, prompt_join
#from handlers.sponsor_verify import auto_verify_sponsor
from utils.db import get_user, save_user
from handlers.force_join import is_member, prompt_join
from utils.db import get_user, save_user

async def ensure_access(update, context):
    """Ensure user has completed force join + sponsor verification before using bot."""
    user = update.effective_user
    user_id = user.id

    # 1. Force Join
    if not await is_member(context, user_id):
        await prompt_join(update, context)
        return False

    # 2. Sponsor Verification (code system only)
    profile = await get_user(user_id)
    if not profile.get("sponsor_verified", False):
        # User hasn’t verified yet → show instructions
        await ask_sponsor_verification(update, context)
        return False

    return True

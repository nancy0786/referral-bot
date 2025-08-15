import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@playhubby").strip()
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0").strip())
WELCOME_FILE = os.path.join("data", "welcome.txt")

SPONSOR_BOT_USERNAME = os.getenv("SPONSOR_BOT_USERNAME", "").strip()
SPONSOR_BOT_ID = int(os.getenv("SPONSOR_BOT_ID", "0").strip())

# config.py (optional additions)
REDEEM_CODE_LENGTH = 16


# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
PRIVATE_DB_CHANNEL_ID = int(os.getenv("PRIVATE_DB_CHANNEL_ID", "0").strip() or 0)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip()]
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "db")
INDEX_FILENAME = "backup_index"  # used for pinned message content

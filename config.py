# config.py

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# --- BOT SETTINGS ---
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()

# Force join channel
FORCE_JOIN_CHANNEL = os.getenv("FORCE_JOIN_CHANNEL", "@playhubby").strip()

# Admin IDs list (comma-separated in .env)
ADMIN_IDS = [int(x) for x in os.getenv("ADMIN_IDS", "").replace(" ", "").split(",") if x]

# Log channel for bot activities
LOG_CHANNEL_ID = int(os.getenv("LOG_CHANNEL_ID", "0").strip())

# Welcome message file
WELCOME_FILE = os.path.join("data", "welcome.txt")

# Sponsor bot details
SPONSOR_BOT_USERNAME = os.getenv("SPONSOR_BOT_USERNAME", "").strip()
SPONSOR_BOT_ID = int(os.getenv("SPONSOR_BOT_ID", "0").strip())

# Redeem code configuration
REDEEM_CODE_LENGTH = 16

# --- BACKUP / STORAGE SETTINGS ---
PRIVATE_DB_CHANNEL_ID = int(os.getenv("PRIVATE_DB_CHANNEL_ID", "0").strip() or 0)

# Data folder for local DB
DATA_FOLDER = os.path.join(os.path.dirname(__file__), "db")

# Backup index filename (used for pinned message content)
INDEX_FILENAME = "backup_index"

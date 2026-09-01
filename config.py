"""
config.py
Central place for environment variables, constants, and file paths.
Nothing else in this project should read os.environ directly — import from here.
"""

import os
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
OUTPUT_DIR = BASE_DIR / "output"
FONT_DIR = BASE_DIR / "assets" / "fonts"
HISTORY_DB_PATH = BASE_DIR / "history.sqlite3"

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ── Groq (quote + hashtag generation) ────────────────────────────────
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.3-70b-versatile"
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# ── TikTok Content Posting API ───────────────────────────────────────
TIKTOK_ACCESS_TOKEN = os.environ.get("TIKTOK_ACCESS_TOKEN", "")
TIKTOK_POST_INIT_URL = "https://open.tiktokapis.com/v2/post/publish/content/init/"

# ── Supabase Storage (image hosting — gives TikTok a public URL) ────
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")  # e.g. https://xxxx.supabase.co
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")  # service_role or anon key
SUPABASE_BUCKET = os.environ.get("SUPABASE_BUCKET", "media")

# ── Generation rules ──────────────────────────────────────────────────
MAX_QUOTE_WORDS = 10
MIN_HASHTAGS = 3
MAX_HASHTAGS = 6

# How similar (0-100) a new quote can be to any past quote before it's
# rejected as a near-duplicate. Lower = stricter. 82 is a reasonable start.
DUPLICATE_SIMILARITY_THRESHOLD = 82

# How many times to ask Groq for a fresh quote before giving up on a run.
MAX_GENERATION_RETRIES = 5

# Card image size — TikTok photo-post friendly (9:16 portrait)
CARD_WIDTH = 1080
CARD_HEIGHT = 1920

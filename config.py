import os
from typing import List
from dotenv import load_dotenv

load_dotenv()

def safe_int(val: str, default: int = 0) -> int:
    try:
        return int(val.strip()) if val and val.strip() else default
    except (ValueError, TypeError):
        return default

BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
API_ID: int = safe_int(os.getenv("API_ID", "0"))
API_HASH: str = os.getenv("API_HASH", "").strip()
SESSION_STRING: str = os.getenv("SESSION_STRING", "").strip()
PORT: int = safe_int(os.getenv("PORT", "10000"), 10000)

PRIVATE_GROUP_ID: int = safe_int(os.getenv("PRIVATE_GROUP_ID", "0"))

def _normalize_group(g: str) -> str:
    g = g.strip()
    if not g:
        return ""
    for prefix in ("https://t.me/", "http://t.me/", "t.me/"):
        if g.startswith(prefix):
            g = g[len(prefix):]
            break
    if g and not g.startswith("-") and not g.startswith("@"):
        g = f"@{g}"
    return g

# Ochiq guruhlar ro'yxati (vergul bilan ajratilgan)
_source_groups_raw = os.getenv("SOURCE_GROUPS", "")
SOURCE_GROUPS: List[str] = [
    _normalize_group(g) for g in _source_groups_raw.split(",") if _normalize_group(g)
]

ADMIN_ID: int = safe_int(os.getenv("ADMIN_ID", "0"))

PAYMENT_CARD: str = os.getenv("PAYMENT_CARD", "9860340101317303").strip()
PAYMENT_CARD_HOLDER: str = os.getenv("PAYMENT_CARD_HOLDER", "Mavlonov Maqsudali").strip()

PRICE_WEEK: int = safe_int(os.getenv("PRICE_WEEK", "25000"), 25000)
PRICE_MONTH: int = safe_int(os.getenv("PRICE_MONTH", "80000"), 80000)
REFERRAL_BONUS: int = safe_int(os.getenv("REFERRAL_BONUS", "5000"), 5000)

DB_PATH: str = os.getenv("DB_PATH", "logistika.db").strip()

# WhatsApp Gateway sozlamalari (Green-API / UltraMsg)
GREEN_API_INSTANCE_ID: str = os.getenv("GREEN_API_INSTANCE_ID", "").strip()
GREEN_API_TOKEN: str = os.getenv("GREEN_API_TOKEN", "").strip()
GREEN_API_URL: str = os.getenv("GREEN_API_URL", "https://api.green-api.com").strip()

ULTRAMSG_INSTANCE_ID: str = os.getenv("ULTRAMSG_INSTANCE_ID", "").strip()
ULTRAMSG_TOKEN: str = os.getenv("ULTRAMSG_TOKEN", "").strip()


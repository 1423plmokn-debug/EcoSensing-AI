import os
import re
from pathlib import Path
from typing import Any
from dotenv import load_dotenv

# Base Directory of the Project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env file with override=True
load_dotenv(BASE_DIR / ".env", override=True)

# Strict regex matching all Unicode emoji ranges
EMOJI_REGEX = re.compile(
    r"[\U00010000-\U0010ffff\u2600-\u27bf\U0001f1e6-\U0001f1ff\u2300-\u23ff\u2b50\u200d\ufe0f]+"
)


def strip_all_emojis(text: str) -> str:
    """Strictly remove all Unicode emoji characters from a string."""
    if not isinstance(text, str):
        return text
    return EMOJI_REGEX.sub("", text)


def sanitize_emojis(obj: Any) -> Any:
    """Recursively strip all emojis from strings in any nested data structure."""
    if isinstance(obj, str):
        return strip_all_emojis(obj)
    elif isinstance(obj, dict):
        return {strip_all_emojis(k) if isinstance(k, str) else k: sanitize_emojis(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [sanitize_emojis(item) for item in obj]
    elif isinstance(obj, tuple):
        return tuple(sanitize_emojis(item) for item in obj)
    elif isinstance(obj, set):
        return {sanitize_emojis(item) for item in obj}
    return obj


class Settings:
    PROJECT_NAME: str = "EcoSensing AI - Urban Microclimate & Field Sentinel"
    INSTITUTION: str = "الجامعة التقنية الوسطى / كلية البوليتكنك / قسم تقنيات هندسة الإلكترونيك والذكاء الاصطناعي"
    AUTHOR: str = "EcoSensing AI Research Lab"

    GROQ_API_KEY_PRIMARY: str = os.getenv("GROQ_API_KEY_PRIMARY", "")
    GROQ_API_KEY_BACKUP: str = os.getenv("GROQ_API_KEY_BACKUP", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    GROQ_MODEL: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_VISION_MODEL: str = os.getenv("GROQ_VISION_MODEL", "llama-3.2-11b-vision-preview")
    LOCATIONIQ_API_KEY: str = os.getenv("LOCATIONIQ_API_KEY", "")
    APP_ENV: str = os.getenv("APP_ENV", "development")
    PORT: int = int(os.getenv("PORT", "8000"))

    @classmethod
    def is_groq_configured(cls) -> bool:
        """Verify if primary or backup GROQ_API_KEY is present and not a dummy placeholder."""
        placeholders = {"", "your_groq_api_key_here", "none", "null"}
        p_key = (cls.GROQ_API_KEY_PRIMARY or "").strip().lower()
        b_key = (cls.GROQ_API_KEY_BACKUP or "").strip().lower()
        return bool((p_key and p_key not in placeholders) or (b_key and b_key not in placeholders))


settings = Settings()

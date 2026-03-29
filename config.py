"""
Central configuration — reads from environment variables.
Copy .env.example → .env and fill in your values.
"""
import base64
import binascii
import json
import os
from typing import Any

from dotenv import load_dotenv

load_dotenv()


class Config:
    # ── Discord ──────────────────────────────────────────────────────────────
    DISCORD_TOKEN: str = os.environ["DISCORD_TOKEN"]

    # Guild ID for instant slash-command sync during development.
    # Set to None (or remove the env var) for global deployment.
    GUILD_ID: int | None = (
        int(os.environ["GUILD_ID"]) if os.environ.get("GUILD_ID") else None
    )

    # Channel where respawn alerts are sent.
    ALERT_CHANNEL_ID: int = int(os.environ["ALERT_CHANNEL_ID"])

    # ── Firebase ─────────────────────────────────────────────────────────────
    # Path to the service-account JSON file downloaded from Firebase console.
    FIREBASE_CREDENTIALS_PATH: str = os.environ.get(
        "FIREBASE_CREDENTIALS_PATH", "firebase_credentials.json"
    )

    # Optional base64-encoded Firebase service-account JSON.
    # When present, this takes precedence over FIREBASE_CREDENTIALS_PATH.
    FIREBASE_CREDENTIALS_B64: str | None = os.environ.get("FIREBASE_CREDENTIALS_B64")

    # ── Timezone ─────────────────────────────────────────────────────────────
    # All user-facing times are displayed in UTC+7 (Indochina Time).
    UTC_OFFSET_HOURS: int = 7

    # ── Alert thresholds (minutes before spawn) ───────────────────────────
    ALERT_THRESHOLDS: list[int] = [10, 5]

    # How often the background alert loop ticks (seconds).
    ALERT_LOOP_INTERVAL: int = 60

    # ── Boss cache TTL (seconds) ──────────────────────────────────────────
    BOSS_CACHE_TTL: int = 300  # 5 minutes


def load_firebase_credentials_info() -> dict[str, Any] | None:
    """
    Decode FIREBASE_CREDENTIALS_B64 into a credentials dict.
    Returns None when env var is not set.
    """
    raw_b64 = Config.FIREBASE_CREDENTIALS_B64
    if not raw_b64:
        return None

    try:
        decoded = base64.b64decode(raw_b64.strip()).decode("utf-8")
        data = json.loads(decoded)
        if not isinstance(data, dict):
            raise ValueError("Decoded Firebase credentials JSON is not an object")
        return data
    except (binascii.Error, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise RuntimeError(
            "Invalid FIREBASE_CREDENTIALS_B64. Ensure it is a valid base64-encoded Firebase JSON file."
        ) from exc

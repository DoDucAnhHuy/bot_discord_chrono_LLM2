"""
boss_service.py – Business logic for boss lookups.

Features:
  • In-memory cache with configurable TTL (reduces Firestore reads).
  • Fuzzy-matching so users can type partial / approximate boss names.
"""
import logging
import time
from difflib import get_close_matches
from typing import Optional

from google.cloud.firestore_v1.async_client import AsyncClient

import database.firestore as db_layer
from config import Config
from models.boss import Boss

logger = logging.getLogger(__name__)

# ── Cache ─────────────────────────────────────────────────────────────────────

_cache_bosses: list[Boss] = []
_cache_ts: float = 0.0  # unix timestamp of last cache fill


async def get_bosses_cached(db: AsyncClient) -> list[Boss]:
    """
    Return all bosses, refreshing the cache when it has expired.
    Thread-safety is not a concern here because discord.py uses a single-thread
    asyncio event loop.
    """
    global _cache_bosses, _cache_ts

    age = time.monotonic() - _cache_ts
    if age > Config.BOSS_CACHE_TTL or not _cache_bosses:
        logger.debug("Boss cache miss – fetching from Firestore")
        _cache_bosses = await db_layer.get_all_bosses(db)
        _cache_ts = time.monotonic()

    return _cache_bosses


def invalidate_boss_cache() -> None:
    """Force the next call to get_bosses_cached() to hit Firestore."""
    global _cache_ts
    _cache_ts = 0.0


# ── Lookup ────────────────────────────────────────────────────────────────────

async def find_boss(db: AsyncClient, query: str) -> Optional[Boss]:
    """
    Find a boss by:
      1. Exact ID match (lowercase, stripped).
      2. Exact name match (case-insensitive).
      3. Fuzzy match on name (difflib, cutoff=0.6).

    Returns None if no match is found.
    """
    bosses = await get_bosses_cached(db)
    q = query.strip().lower()

    # 1) Exact ID match
    for boss in bosses:
        if boss.id == q:
            return boss

    # 2) Exact name match (case-insensitive)
    for boss in bosses:
        if boss.name.lower() == q:
            return boss

    # 3) Fuzzy match on name
    name_map = {b.name.lower(): b for b in bosses}
    matches = get_close_matches(q, name_map.keys(), n=1, cutoff=0.6)
    if matches:
        matched_boss = name_map[matches[0]]
        logger.info(
            "Fuzzy match: '%s' → '%s'", query, matched_boss.name
        )
        return matched_boss

    return None

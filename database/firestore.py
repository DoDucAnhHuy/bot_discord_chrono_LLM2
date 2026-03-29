"""
Firestore data-access layer.
"""
import logging
from typing import Optional

import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore_async  # module async chính xác

from config import Config, load_firebase_credentials_info
from models.boss import Boss
from models.kill import KillRecord

logger = logging.getLogger(__name__)


def init_firebase():
    """Initialise Firebase once và trả về async Firestore client."""
    if not firebase_admin._apps:
        creds_info = load_firebase_credentials_info()
        if creds_info is not None:
            cred = credentials.Certificate(creds_info)
            logger.info("Firebase initialized from FIREBASE_CREDENTIALS_B64")
        else:
            cred = credentials.Certificate(Config.FIREBASE_CREDENTIALS_PATH)
            logger.info(
                "Firebase initialized from credentials file: %s",
                Config.FIREBASE_CREDENTIALS_PATH,
            )

        firebase_admin.initialize_app(cred)
    return firestore_async.client()  # đúng cách lấy async client


# ── Boss (dimboss) ────────────────────────────────────────────────────────────

async def get_all_bosses(db) -> list[Boss]:
    docs = db.collection("dimboss").stream()
    bosses: list[Boss] = []
    async for doc in docs:
        try:
            bosses.append(Boss.from_dict(doc.to_dict()))
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed boss doc %s: %s", doc.id, exc)
    return bosses


async def get_boss_by_id(db, boss_id: str) -> Optional[Boss]:
    doc = await db.collection("dimboss").document(boss_id).get()
    if not doc.exists:
        return None
    try:
        return Boss.from_dict(doc.to_dict())
    except (KeyError, ValueError) as exc:
        logger.error("Malformed boss doc %s: %s", boss_id, exc)
        return None


# ── Kill facts (fact_kill) ────────────────────────────────────────────────────

async def get_kill_record(db, boss_id: str) -> Optional[KillRecord]:
    doc = await db.collection("fact_kill").document(boss_id).get()
    if not doc.exists:
        return None
    try:
        return KillRecord.from_dict(doc.to_dict())
    except (KeyError, ValueError) as exc:
        logger.error("Malformed kill record for boss %s: %s", boss_id, exc)
        return None


async def upsert_kill_record(db, record: KillRecord) -> None:
    await db.collection("fact_kill").document(record.boss_id).set(record.to_dict())
    logger.info(
        "Kill record upserted: boss=%s kill_time=%s by=%s",
        record.boss_id,
        record.last_kill_time.isoformat(),
        record.updated_by,
    )


async def get_all_kill_records(db) -> dict[str, KillRecord]:
    docs = db.collection("fact_kill").stream()
    records: dict[str, KillRecord] = {}
    async for doc in docs:
        try:
            rec = KillRecord.from_dict(doc.to_dict())
            records[rec.boss_id] = rec
        except (KeyError, ValueError) as exc:
            logger.warning("Skipping malformed kill doc %s: %s", doc.id, exc)
    return records
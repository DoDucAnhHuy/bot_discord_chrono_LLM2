"""
Kill fact model - mirrors the 'fact_kill' Firestore collection.
"""
from dataclasses import dataclass
from datetime import datetime


@dataclass
class KillRecord:
    boss_id: str
    last_kill_time: datetime  # always stored/returned as UTC-aware datetime
    updated_by: str           # Discord user ID (string)

    @staticmethod
    def from_dict(data: dict) -> "KillRecord":
        """
        Parse a Firestore document dict.
        last_kill_time is stored as an ISO string in UTC.
        """
        from datetime import timezone

        raw_time = data["last_kill_time"]

        # Accept both datetime objects (from Firestore SDK) and ISO strings
        if isinstance(raw_time, datetime):
            dt = raw_time
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(raw_time))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)

        return KillRecord(
            boss_id=data["boss_id"],
            last_kill_time=dt,
            updated_by=str(data.get("updated_by", "")),
        )

    def to_dict(self) -> dict:
        return {
            "boss_id": self.boss_id,
            "last_kill_time": self.last_kill_time.isoformat(),
            "updated_by": self.updated_by,
        }

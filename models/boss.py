"""
Boss domain model - mirrors the 'dimboss' Firestore collection.
"""
from dataclasses import dataclass


@dataclass
class Boss:
    id: str            # e.g. "gahareth"
    name: str          # e.g. "Gahareth"
    cycle_minutes: int # e.g. 210

    @staticmethod
    def from_dict(data: dict) -> "Boss":
        return Boss(
            id=data["id"],
            name=data["name"],
            cycle_minutes=int(data["cycle_minutes"]),
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "cycle_minutes": self.cycle_minutes,
        }

"""
seed_firestore.py – One-time script to populate the `dimboss` collection.

Run ONCE after setting up Firebase:
    python seed_firestore.py
"""
import json
import firebase_admin
from firebase_admin import credentials, firestore

CREDENTIALS_PATH = "firebase_credentials.json"
SEED_FILE = "seed_data.json"


def main() -> None:
    cred = credentials.Certificate(CREDENTIALS_PATH)
    firebase_admin.initialize_app(cred)
    db = firestore.client()  # lấy client từ app đã init bằng credentials ở trên

    with open(SEED_FILE) as f:
        data = json.load(f)

    bosses = data.get("dimboss", [])
    col = db.collection("dimboss")

    for boss in bosses:
        col.document(boss["id"]).set(boss)
        print(f"  ✅  {boss['name']} ({boss['id']}) → cycle {boss['cycle_minutes']}m")

    print(f"\nDone – seeded {len(bosses)} bosses into 'dimboss' collection.")


if __name__ == "__main__":
    main()
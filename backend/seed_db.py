"""
Resets the database and loads the seed data.

    python seed_db.py              # runs ../seed.py to generate fresh data
    python seed_db.py seed.json    # or loads an existing JSON file
"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import text

from app.db import Base, SessionLocal, engine
from app.models import Booking, Ship

ROOT = Path(__file__).resolve().parent.parent


def load_seed(path=None):
    if path:
        return json.loads(Path(path).read_text())
    result = subprocess.run(
        [sys.executable, str(ROOT / "seed.py")],
        capture_output=True, text=True, check=True,
    )
    return json.loads(result.stdout)


def main():
    data = load_seed(sys.argv[1] if len(sys.argv) > 1 else None)

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

    with SessionLocal() as db:
        db.add_all(Ship(id=s["id"], name=s["name"]) for s in data["ships"])
        db.flush()
        db.add_all(
            Booking(
                ship_id=b["shipId"],
                pilot_name=b["pilotName"],
                start_time=datetime.fromisoformat(b["startTime"]),
                end_time=datetime.fromisoformat(b["endTime"]),
            )
            for b in data["bookings"]
        )
        # Ships were inserted with explicit ids, so move the id sequence past them.
        db.execute(text("SELECT setval(pg_get_serial_sequence('ships', 'id'), (SELECT MAX(id) FROM ships))"))
        db.commit()

    print(f"Loaded {len(data['ships'])} ships and {len(data['bookings'])} bookings.")


if __name__ == "__main__":
    main()

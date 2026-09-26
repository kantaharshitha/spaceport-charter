"""
API tests run against a separate `spaceport_test` database in the same Postgres container,
because the overlap rule lives in a Postgres exclusion constraint that SQLite can't imitate.
"""

import os

TEST_DATABASE_URL = "postgresql+psycopg://spaceport:spaceport@localhost:5432/spaceport_test"
# Must be set before app.db is imported, since it reads DATABASE_URL at import time.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL

import psycopg  # noqa: E402
import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402


@pytest.fixture(scope="session")
def test_database():
    with psycopg.connect(
        "postgresql://spaceport:spaceport@localhost:5432/postgres", autocommit=True
    ) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = 'spaceport_test'").fetchone()
        if not exists:
            conn.execute("CREATE DATABASE spaceport_test")


@pytest.fixture
def client(test_database):
    from app.db import Base, SessionLocal, engine
    from app.main import app
    from app.models import Ship

    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        db.add_all([Ship(id=1, name="USS Wanderer"), Ship(id=2, name="Nostromo")])
        db.commit()

    with TestClient(app) as c:
        yield c

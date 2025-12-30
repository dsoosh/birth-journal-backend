from __future__ import annotations

import os
from pathlib import Path

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

from backend.app.db import Base, get_engine, get_sessionmaker
from backend.app.main import create_app
from backend.app.settings import get_settings

# Load .env file from backend root directory
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def _can_connect() -> bool:
    try:
        engine = get_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False


@pytest.fixture(scope="session")
def app():
    return create_app()


@pytest.fixture(scope="session")
def client(app):
    return TestClient(app)


@pytest.fixture(scope="session", autouse=True)
def _ensure_test_db():
    # These tests require Postgres features used by the PoC (JSONB + identity/event_seq).
    # Set DATABASE_URL in your environment to run them.
    if not os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL not set; skipping DB integration tests")

    os.environ.setdefault("JWT_SECRET", "test-secret")
    os.environ.setdefault("JWT_ALGORITHM", "HS256")
    os.environ.setdefault("JWT_TTL_SECONDS", "86400")

    # Ensure settings/engine pick up env vars
    get_settings.cache_clear()
    get_engine.cache_clear()
    get_sessionmaker.cache_clear()

    if not _can_connect():
        pytest.skip("Cannot connect to DATABASE_URL; skipping DB integration tests")

    engine = get_engine()
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    yield

    Base.metadata.drop_all(bind=engine)

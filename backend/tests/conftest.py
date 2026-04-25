import os

# Must be set before any app/db module is imported so load_dotenv() doesn't
# override them (load_dotenv skips vars that are already in os.environ).
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("ANTHROPIC_API_KEY", "test-key-not-real")

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from unittest.mock import patch

# One shared in-memory engine for the whole test session.
_test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
)


@pytest.fixture(scope="session", autouse=True)
def _create_tables():
    from db import Base
    Base.metadata.create_all(_test_engine)


@pytest.fixture(autouse=True)
def _patch_db_engine():
    """Route all get_session() calls to the in-memory test engine."""
    with patch("db.get_engine", return_value=_test_engine):
        yield


@pytest.fixture(autouse=True)
def _clean_tables(_create_tables):
    """Delete all rows after every test for isolation."""
    yield
    from db import Base
    with Session(_test_engine) as s:
        for table in reversed(Base.metadata.sorted_tables):
            s.execute(table.delete())
        s.commit()


@pytest.fixture
def client(_patch_db_engine):
    from app import app
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c

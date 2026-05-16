import os
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ["CALENDAR_BACKGROUND_SYNC_ENABLED"] = "false"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["TOKEN_ENCRYPTION_KEY"] = "test-token-key"
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_ID", "test-google-client")
os.environ.setdefault("GOOGLE_CALENDAR_CLIENT_SECRET", "test-google-secret")
os.environ.setdefault("MICROSOFT_CALENDAR_CLIENT_ID", "test-microsoft-client")
os.environ.setdefault("MICROSOFT_CALENDAR_CLIENT_SECRET", "test-microsoft-secret")

from app.db.session import Base, get_db
from app.main import app
from app.models import models  # noqa: F401


engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    future=True,
)
TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@pytest.fixture(autouse=True)
def reset_database() -> Generator[None, None, None]:
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session() -> Generator[Session, None, None]:
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture()
def client(db_session: Session) -> Generator[TestClient, None, None]:
    def override_get_db() -> Generator[Session, None, None]:
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

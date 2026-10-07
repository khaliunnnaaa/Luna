"""Тест бүр хоосон, санах ойн (in-memory) SQLite сан ашиглана — dev.db-д хүрэхгүй."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

import app.models  # noqa: F401
from app.core.database import Base, get_db
from app.main import app


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(bind=engine)
    TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = TestingSession()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture()
def client(db_session):
    app.dependency_overrides[get_db] = lambda: db_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _headers_for(client, db_session, email, role):
    from app.core.security import hash_password
    from app.models.user import User

    db_session.add(
        User(email=email, full_name=role.value, password_hash=hash_password("password1"), role=role)
    )
    db_session.commit()
    r = client.post("/auth/login", json={"email": email, "password": "password1"})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture()
def admin_headers(client, db_session):
    from app.models.user import Role

    return _headers_for(client, db_session, "admin@test.mn", Role.admin)


@pytest.fixture()
def student_headers(client, db_session):
    from app.models.user import Role

    return _headers_for(client, db_session, "student@test.mn", Role.student)

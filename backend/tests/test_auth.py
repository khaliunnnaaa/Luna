"""FR-01 бүртгэл ба нэвтрэлтийн тест."""

from app.core.security import hash_password
from app.models.user import Role, User

STUDENT = {
    "email": "Bat@Example.com",
    "password": "nuutsug123",
    "full_name": "Бат",
    "role": "student",
}


def register(client, **overrides):
    return client.post("/auth/register", json={**STUDENT, **overrides})


def auth_header(token):
    return {"Authorization": f"Bearer {token}"}


def test_register_returns_token_and_user(client):
    r = register(client)
    assert r.status_code == 201
    body = r.json()
    assert body["access_token"]
    assert body["user"]["email"] == "bat@example.com"  # жижиг үсэг болгосон
    assert body["user"]["role"] == "student"
    assert "password" not in body["user"] and "password_hash" not in body["user"]


def test_register_parent(client):
    r = register(client, email="eej@example.com", role="parent")
    assert r.status_code == 201
    assert r.json()["user"]["role"] == "parent"


def test_password_is_hashed(client, db_session):
    register(client)
    user = db_session.query(User).one()
    assert user.password_hash != STUDENT["password"]
    assert user.password_hash.startswith("$argon2")


def test_duplicate_email_rejected(client):
    register(client)
    r = register(client, email="bat@example.com")
    assert r.status_code == 409


def test_cannot_self_register_as_admin(client):
    assert register(client, role="admin").status_code == 422


def test_short_password_rejected(client):
    assert register(client, password="123").status_code == 422


def test_bad_email_rejected(client):
    assert register(client, email="not-an-email").status_code == 422


def test_login_success(client):
    register(client)
    r = client.post("/auth/login", json={"email": "bat@example.com", "password": "nuutsug123"})
    assert r.status_code == 200
    assert r.json()["user"]["full_name"] == "Бат"


def test_login_wrong_password(client):
    register(client)
    r = client.post("/auth/login", json={"email": "bat@example.com", "password": "buruu12345"})
    assert r.status_code == 401


def test_login_unknown_email(client):
    r = client.post("/auth/login", json={"email": "no@example.com", "password": "nuutsug123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/auth/me").status_code == 401
    assert client.get("/auth/me", headers=auth_header("buruu.token")).status_code == 401


def test_me_returns_current_user(client):
    token = register(client).json()["access_token"]
    r = client.get("/auth/me", headers=auth_header(token))
    assert r.status_code == 200
    assert r.json()["email"] == "bat@example.com"


def test_role_check(client, db_session):
    student_token = register(client).json()["access_token"]
    assert client.get("/auth/admin-only", headers=auth_header(student_token)).status_code == 403

    db_session.add(
        User(
            email="admin@example.com",
            full_name="Админ",
            password_hash=hash_password("adminpass1"),
            role=Role.admin,
        )
    )
    db_session.commit()
    r = client.post("/auth/login", json={"email": "admin@example.com", "password": "adminpass1"})
    admin_token = r.json()["access_token"]
    assert client.get("/auth/admin-only", headers=auth_header(admin_token)).status_code == 200

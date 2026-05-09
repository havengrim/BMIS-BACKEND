from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.core.dependencies import get_current_user
from app.core.redis import get_redis_dep
from app.core.security import Security
from app.db.session import get_db
from app.modules.users.model import UserRole, UserStatus


class _Scalars:
    def __init__(self, items):
        self._items = items

    def all(self):
        return self._items


class _ExecResult:
    def __init__(self, one=None, all_items=None):
        self._one = one
        self._all_items = all_items or []

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return _Scalars(self._all_items)


@pytest.fixture
def client(monkeypatch):
    from app import main as app_main

    monkeypatch.setattr(app_main, "init_redis", AsyncMock(return_value=None))
    monkeypatch.setattr(app_main, "close_redis", AsyncMock(return_value=None))

    db = AsyncMock()
    redis = AsyncMock()

    async def override_db():
        yield db

    async def override_redis():
        yield redis

    async def override_current_user():
        return {"sub": str(uuid4()), "role": "super_admin", "jti": "access-jti"}

    app_main.app.dependency_overrides[get_db] = override_db
    app_main.app.dependency_overrides[get_redis_dep] = override_redis
    app_main.app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app_main.app) as test_client:
        yield test_client, db, redis

    app_main.app.dependency_overrides.clear()


def _make_user(email: str = "user@example.com"):
    return SimpleNamespace(
        id=uuid4(),
        email=email,
        username="testuser",
        hashed_password=Security.hash_password("Admin1234!"),
        first_name="Test",
        last_name="User",
        middle_name=None,
        contact_number=None,
        address=None,
        role=UserRole.SUPER_ADMIN,
        status=UserStatus.ACTIVE,
        is_verified=True,
        deleted_at=None,
    )


def test_auth_login_success(client):
    test_client, db, _redis = client
    user = _make_user("login@example.com")
    db.execute = AsyncMock(return_value=_ExecResult(one=user))

    response = test_client.post(
        "/auth/login",
        json={"email": "login@example.com", "password": "Admin1234!"},
    )

    assert response.status_code == 200
    body = response.json()
    assert "access_token" in body
    assert "refresh_token" in body
    assert body["token_type"] == "bearer"


def test_auth_login_invalid_credentials(client):
    test_client, db, _redis = client
    db.execute = AsyncMock(return_value=_ExecResult(one=None))

    response = test_client.post(
        "/auth/login",
        json={"email": "missing@example.com", "password": "wrong"},
    )

    assert response.status_code == 401


def test_auth_refresh_rejects_blacklisted_refresh_token(client):
    test_client, _db, redis = client
    redis.get = AsyncMock(return_value="1")

    refresh = Security.create_refresh_token({"sub": "u1", "email": "a@b.com", "role": "resident"})
    response = test_client.post("/auth/refresh", json={"refresh_token": refresh})

    assert response.status_code == 401
    assert "revoked" in response.json()["detail"].lower()


def test_auth_me_returns_current_user_payload(client):
    test_client, _db, _redis = client

    response = test_client.get("/auth/me")

    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "super_admin"
    assert "sub" in body


def test_rbac_list_permissions_route(client):
    test_client, db, _redis = client
    permission = SimpleNamespace(
        id=uuid4(),
        code="rbac.read",
        module="rbac",
        action="read",
        name="Read RBAC",
        description=None,
        created_at=datetime.now(timezone.utc),
    )
    db.execute = AsyncMock(return_value=_ExecResult(all_items=[permission]))

    response = test_client.get("/rbac/permissions")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["code"] == "rbac.read"


def test_rbac_create_permission_conflict(client):
    test_client, db, _redis = client
    db.execute = AsyncMock(return_value=_ExecResult(one=object()))

    response = test_client.post(
        "/rbac/permissions",
        json={
            "code": "complaints.read",
            "module": "complaints",
            "action": "read",
            "name": "Read complaints",
            "description": "",
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_users_list_protected_route(client):
    test_client, db, _redis = client
    db.execute = AsyncMock(return_value=_ExecResult(all_items=[_make_user("list@example.com")]))

    response = test_client.get("/users/")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["email"] == "list@example.com"

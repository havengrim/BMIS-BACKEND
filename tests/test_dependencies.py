from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app.core.dependencies import (
    get_current_user,
    invalidate_user_permissions_cache,
    require_permissions,
    require_roles,
)


@pytest.mark.asyncio
async def test_get_current_user_returns_payload_for_valid_access_token(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies.Security.decode_token",
        lambda _token: {"sub": "u1", "type": "access", "jti": "abc"},
    )

    redis = AsyncMock()
    redis.get.return_value = None

    credentials = SimpleNamespace(credentials="valid.jwt")
    payload = await get_current_user(credentials=credentials, redis=redis)

    assert payload["sub"] == "u1"


@pytest.mark.asyncio
async def test_get_current_user_raises_401_for_blacklisted_token(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies.Security.decode_token",
        lambda _token: {"sub": "u1", "type": "access", "jti": "abc"},
    )

    redis = AsyncMock()
    redis.get.return_value = "1"

    credentials = SimpleNamespace(credentials="valid.jwt")

    with pytest.raises(HTTPException) as exc:
        await get_current_user(credentials=credentials, redis=redis)

    assert exc.value.status_code == 401
    assert "revoked" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_require_roles_allows_authorized_role():
    dep = require_roles("super_admin", "barangay_admin")
    current_user = {"role": "barangay_admin"}

    result = await dep(current_user=current_user)
    assert result == current_user


@pytest.mark.asyncio
async def test_require_roles_blocks_unauthorized_role():
    dep = require_roles("super_admin", "barangay_admin")

    with pytest.raises(HTTPException) as exc:
        await dep(current_user={"role": "resident"})

    assert exc.value.status_code == 403


@pytest.mark.asyncio
async def test_require_permissions_allows_super_admin_bypass():
    dep = require_permissions("users.manage")

    result = await dep(
        current_user={"sub": "u1", "role": "super_admin"},
        db=AsyncMock(),
        redis=AsyncMock(),
    )
    assert result["role"] == "super_admin"


@pytest.mark.asyncio
async def test_require_permissions_raises_for_missing_subject():
    dep = require_permissions("users.manage")

    with pytest.raises(HTTPException) as exc:
        await dep(
            current_user={"role": "staff"},
            db=AsyncMock(),
            redis=AsyncMock(),
        )

    assert exc.value.status_code == 401


@pytest.mark.asyncio
async def test_require_permissions_barangay_admin_fallback(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies._load_user_permission_codes",
        AsyncMock(return_value=set()),
    )
    dep = require_permissions("users.manage")

    result = await dep(
        current_user={"sub": "u1", "role": "barangay_admin"},
        db=AsyncMock(),
        redis=AsyncMock(),
    )

    assert result["role"] == "barangay_admin"


@pytest.mark.asyncio
async def test_require_permissions_raises_if_missing_permission(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies._load_user_permission_codes",
        AsyncMock(return_value={"users.read"}),
    )
    dep = require_permissions("users.manage")

    with pytest.raises(HTTPException) as exc:
        await dep(
            current_user={"sub": "u1", "role": "staff"},
            db=AsyncMock(),
            redis=AsyncMock(),
        )

    assert exc.value.status_code == 403
    assert "missing permissions" in exc.value.detail.lower()


@pytest.mark.asyncio
async def test_require_permissions_allows_when_permission_present(monkeypatch):
    monkeypatch.setattr(
        "app.core.dependencies._load_user_permission_codes",
        AsyncMock(return_value={"users.manage", "users.read"}),
    )
    dep = require_permissions("users.manage")

    result = await dep(
        current_user={"sub": "u1", "role": "staff"},
        db=AsyncMock(),
        redis=AsyncMock(),
    )

    assert result["sub"] == "u1"


@pytest.mark.asyncio
async def test_invalidate_user_permissions_cache_deletes_cache_key():
    redis = AsyncMock()

    await invalidate_user_permissions_cache("u1", redis)

    redis.delete.assert_awaited_once_with("user_permissions:u1")

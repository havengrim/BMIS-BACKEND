from app.core.security import Security


def test_hash_password_and_verify_roundtrip():
    plain = "Admin1234!"
    hashed = Security.hash_password(plain)

    assert hashed != plain
    assert Security.verify_password(plain, hashed) is True
    assert Security.verify_password("wrong-password", hashed) is False


def test_access_token_contains_expected_claims():
    token = Security.create_access_token({"sub": "u1", "email": "a@b.com", "role": "resident"})
    payload = Security.decode_token(token)

    assert payload is not None
    assert payload["sub"] == "u1"
    assert payload["type"] == "access"
    assert "jti" in payload


def test_refresh_token_contains_expected_claims():
    token = Security.create_refresh_token({"sub": "u1", "email": "a@b.com", "role": "resident"})
    payload = Security.decode_token(token)

    assert payload is not None
    assert payload["type"] == "refresh"
    assert Security.is_token_type(payload, "refresh") is True
    assert Security.is_token_type(payload, "access") is False


def test_decode_token_returns_none_for_invalid_token():
    payload = Security.decode_token("not.a.real.jwt")
    assert payload is None

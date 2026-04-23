from datetime import timedelta

import pytest

from app.core.security import (
    TokenValidationError,
    create_access_token,
    decode_access_token,
    hash_token,
    hash_password,
    verify_password,
)


def test_create_and_decode_access_token():
    token = create_access_token(
        payload={"sub": "user-1", "sid": "session-1", "role": "admin"},
        secret_key="test-secret",
        expires_delta=timedelta(minutes=5),
    )

    payload = decode_access_token(token, "test-secret")

    assert payload["sub"] == "user-1"
    assert payload["sid"] == "session-1"
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "iat" in payload


def test_decode_access_token_rejects_tampering():
    token = create_access_token(
        payload={"sub": "user-1"},
        secret_key="test-secret",
        expires_delta=timedelta(minutes=5),
    )

    tampered_token = token[:-1] + ("a" if token[-1] != "a" else "b")

    with pytest.raises(TokenValidationError):
        decode_access_token(tampered_token, "test-secret")


def test_hash_token_is_stable():
    assert hash_token("refresh-token") == hash_token("refresh-token")
    assert hash_token("refresh-token") != hash_token("refresh-token-2")


def test_password_hash_round_trip():
    password_hash = hash_password("super-secret-password")

    assert password_hash != "super-secret-password"
    assert verify_password("super-secret-password", password_hash) is True
    assert verify_password("wrong-password", password_hash) is False

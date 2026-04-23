import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any


class TokenValidationError(Exception):
    """Raised when an application token fails validation."""


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(f"{data}{padding}")


def create_access_token(payload: dict[str, Any], secret_key: str, expires_delta: timedelta) -> str:
    issued_at = datetime.now(timezone.utc)
    token_payload = {
        **payload,
        "iat": int(issued_at.timestamp()),
        "exp": int((issued_at + expires_delta).timestamp()),
    }
    header = {"alg": "HS256", "typ": "JWT"}
    signing_input = ".".join(
        [
            _b64url_encode(json.dumps(header, separators=(",", ":"), sort_keys=True).encode("utf-8")),
            _b64url_encode(json.dumps(token_payload, separators=(",", ":"), sort_keys=True).encode("utf-8")),
        ]
    )
    signature = hmac.new(secret_key.encode("utf-8"), signing_input.encode("utf-8"), hashlib.sha256).digest()
    return f"{signing_input}.{_b64url_encode(signature)}"


def decode_access_token(token: str, secret_key: str) -> dict[str, Any]:
    try:
        header_segment, payload_segment, signature_segment = token.split(".")
    except ValueError as exc:
        raise TokenValidationError("Malformed token") from exc

    signing_input = f"{header_segment}.{payload_segment}"
    expected_signature = hmac.new(
        secret_key.encode("utf-8"),
        signing_input.encode("utf-8"),
        hashlib.sha256,
    ).digest()

    provided_signature = _b64url_decode(signature_segment)
    if not hmac.compare_digest(expected_signature, provided_signature):
        raise TokenValidationError("Invalid token signature")

    try:
        payload = json.loads(_b64url_decode(payload_segment))
    except json.JSONDecodeError as exc:
        raise TokenValidationError("Invalid token payload") from exc

    expires_at = payload.get("exp")
    if not isinstance(expires_at, int):
        raise TokenValidationError("Missing token expiration")
    if expires_at <= int(datetime.now(timezone.utc).timestamp()):
        raise TokenValidationError("Token expired")

    return payload


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    derived_key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=2**14,
        r=8,
        p=1,
    )
    return "$".join(
        [
            "scrypt",
            str(2**14),
            "8",
            "1",
            _b64url_encode(salt),
            _b64url_encode(derived_key),
        ]
    )


def verify_password(password: str, password_hash: str) -> bool:
    try:
        algorithm, n_value, r_value, p_value, salt_value, key_value = password_hash.split("$", 5)
    except ValueError:
        return False

    if algorithm != "scrypt":
        return False

    try:
        derived_key = hashlib.scrypt(
            password.encode("utf-8"),
            salt=_b64url_decode(salt_value),
            n=int(n_value),
            r=int(r_value),
            p=int(p_value),
        )
    except (ValueError, TypeError):
        return False

    return hmac.compare_digest(_b64url_encode(derived_key), key_value)

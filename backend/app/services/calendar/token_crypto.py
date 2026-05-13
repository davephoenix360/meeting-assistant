import base64
import hashlib
import hmac
import os

from app.core.config import settings


class TokenEncryptionError(Exception):
    pass


def _key_material() -> bytes:
    raw = (settings.token_encryption_key or "").strip()
    if not raw:
        raise TokenEncryptionError(
            "TOKEN_ENCRYPTION_KEY is required before storing calendar OAuth tokens."
        )
    return hashlib.sha256(raw.encode("utf-8")).digest()


def encrypt_token(value: str | None) -> str | None:
    if value is None:
        return None

    key = _key_material()
    nonce = os.urandom(16)
    value_bytes = value.encode("utf-8")
    stream = _keystream(key, nonce, len(value_bytes))
    ciphertext = _xor(value_bytes, stream)
    signature = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(nonce + signature + ciphertext).decode("ascii")


def decrypt_token(value: str | None) -> str | None:
    if value is None:
        return None

    key = _key_material()
    try:
        payload = base64.urlsafe_b64decode(value.encode("ascii"))
    except Exception as e:
        raise TokenEncryptionError("Stored token payload is invalid.") from e

    nonce = payload[:16]
    signature = payload[16:48]
    ciphertext = payload[48:]
    expected = hmac.new(key, nonce + ciphertext, hashlib.sha256).digest()
    if not hmac.compare_digest(signature, expected):
        raise TokenEncryptionError("Stored token payload failed integrity validation.")

    stream = _keystream(key, nonce, len(ciphertext))
    return _xor(ciphertext, stream).decode("utf-8")


def _keystream(key: bytes, nonce: bytes, length: int) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < length:
        block = hmac.new(
            key,
            nonce + counter.to_bytes(8, "big"),
            hashlib.sha256,
        ).digest()
        output.extend(block)
        counter += 1
    return bytes(output[:length])


def _xor(left: bytes, right: bytes) -> bytes:
    return bytes(a ^ b for a, b in zip(left, right))

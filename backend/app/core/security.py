"""Simple, replaceable credential helpers (stdlib only).

Passphrases are salted PBKDF2 hashes; session tokens are random and only
their SHA-256 digest is stored, so a leaked database does not leak tokens.
Swap this module for OAuth/JWT when the game is hosted."""
from __future__ import annotations

import hashlib
import hmac
import secrets

_ITERATIONS = 100_000


def hash_passphrase(passphrase: str, salt: bytes | None = None) -> tuple[bytes, bytes]:
    salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", passphrase.encode(), salt, _ITERATIONS)
    return salt, digest


def verify_passphrase(passphrase: str, salt: bytes, expected: bytes) -> bool:
    return hmac.compare_digest(hash_passphrase(passphrase, salt)[1], expected)


def new_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

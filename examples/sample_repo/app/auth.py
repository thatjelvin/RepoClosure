"""Authentication helpers for the sample application.

This module issues and verifies signed tokens. Tokens embed an expiry timestamp so
that expired credentials are rejected during verification.
"""
from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass

SECRET = b"sample-secret"
DEFAULT_TTL = 3600


class AuthError(Exception):
    """Raised when a token is missing, malformed, or expired."""


@dataclass
class Token:
    subject: str
    expires_at: float
    signature: str


def _sign(payload: str) -> str:
    return hmac.new(SECRET, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def make_token(subject: str, ttl: int = DEFAULT_TTL) -> Token:
    """Create a signed token that expires after ``ttl`` seconds."""
    expires_at = time.time() + ttl
    payload = f"{subject}:{expires_at}"
    return Token(subject=subject, expires_at=expires_at, signature=_sign(payload))


def verify_token(token: Token) -> str:
    """Return the subject if the token is valid, else raise :class:`AuthError`.

    An expired token raises ``AuthError`` with the message "token expired".
    """
    if token.expires_at < time.time():
        raise AuthError("token expired")
    expected = _sign(f"{token.subject}:{token.expires_at}")
    if not hmac.compare_digest(expected, token.signature):
        raise AuthError("bad signature")
    return token.subject


def refresh_token(token: Token, ttl: int = DEFAULT_TTL) -> Token:
    """Issue a fresh token for the same subject, ignoring expiry."""
    return make_token(token.subject, ttl=ttl)


def normalize_subject(subject: str) -> str:
    """Lower-case and strip whitespace from a subject identifier."""
    return subject.strip().lower()

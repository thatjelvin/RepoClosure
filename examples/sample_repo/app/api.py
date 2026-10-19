"""Tiny HTTP-ish API layer for the sample application."""
from __future__ import annotations

from .auth import AuthError, make_token, normalize_subject, verify_token
from .session import SessionStore

STORE = SessionStore()


def handle_login(subject: str) -> dict:
    """Log a subject in and return a token."""
    clean = normalize_subject(subject)
    token = make_token(clean)
    STORE.create(clean, token)
    return {"subject": clean, "token": token.signature}


def handle_request(subject: str, token) -> dict:
    """Handle an authenticated request, returning an error on expired tokens."""
    try:
        verified = verify_token(token)
    except AuthError as exc:
        return {"ok": False, "error": str(exc)}
    session = STORE.get(verified)
    if session is None:
        return {"ok": False, "error": "no session"}
    session.touch()
    return {"ok": session.active, "subject": verified}

"""Session management built on top of :mod:`app.auth`."""
from __future__ import annotations

from .auth import AuthError, Token, verify_token


class Session:
    """Represents a logged-in user session."""

    def __init__(self, subject: str, token: Token):
        self.subject = subject
        self.token = token
        self.active = True

    def touch(self) -> None:
        """Validate the session token, deactivating the session on failure."""
        try:
            verify_token(self.token)
        except AuthError:
            self.active = False


class SessionStore:
    """In-memory session store keyed by subject."""

    def __init__(self) -> None:
        self._sessions: dict[str, Session] = {}

    def create(self, subject: str, token: Token) -> Session:
        session = Session(subject, token)
        self._sessions[subject] = session
        return session

    def get(self, subject: str) -> Session | None:
        return self._sessions.get(subject)

    def expire(self, subject: str) -> None:
        session = self._sessions.pop(subject, None)
        if session is not None:
            session.active = False

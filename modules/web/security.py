"""Authentication and request protection for the remote dashboard."""

from __future__ import annotations

import hmac
import hashlib
import os
import secrets
import time
from collections import defaultdict, deque
from dataclasses import dataclass

from aiohttp import web
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

SESSION_COOKIE = "pokebot_session"
SESSION_TTL_SECONDS = 12 * 60 * 60
LOGIN_WINDOW_SECONDS = 5 * 60
LOGIN_ATTEMPTS = 5


@dataclass
class Session:
    csrf_token: str
    expires_at: float


class DashboardSecurity:
    """Shared signed sessions for multiple bot processes on one host."""

    def __init__(self, username: str, password_hash: str, session_secret: str) -> None:
        if not username or not password_hash or len(session_secret) < 32:
            raise RuntimeError(
                "Dashboard credentials and POKEBOT_WEB_SESSION_SECRET (32+ characters) are required."
            )
        self.username = username
        self.password_hash = password_hash
        self.session_secret = session_secret.encode("utf-8")
        self.password_hasher = PasswordHasher()
        self.login_attempts: dict[str, deque[float]] = defaultdict(deque)

    @classmethod
    def from_environment(cls) -> "DashboardSecurity":
        return cls(
            os.environ.get("POKEBOT_WEB_USERNAME", ""),
            os.environ.get("POKEBOT_WEB_PASSWORD_HASH", ""),
            os.environ.get("POKEBOT_WEB_SESSION_SECRET", ""),
        )

    def _sign(self, payload: str) -> str:
        return hmac.new(self.session_secret, payload.encode("ascii"), hashlib.sha256).hexdigest()

    def authenticate(self, username: str, password: str, remote: str) -> tuple[str, Session] | None:
        now = time.monotonic()
        attempts = self.login_attempts[remote]
        while attempts and attempts[0] <= now - LOGIN_WINDOW_SECONDS:
            attempts.popleft()
        if len(attempts) >= LOGIN_ATTEMPTS:
            raise web.HTTPTooManyRequests(text="Muitas tentativas. Aguarde cinco minutos.")

        valid_username = hmac.compare_digest(username, self.username)
        try:
            valid_password = self.password_hasher.verify(self.password_hash, password)
        except (InvalidHashError, VerificationError, VerifyMismatchError):
            valid_password = False
        if not (valid_username and valid_password):
            attempts.append(now)
            return None

        attempts.clear()
        expires_at = int(time.time()) + SESSION_TTL_SECONDS
        csrf_token = secrets.token_urlsafe(32)
        payload = f"{expires_at}.{csrf_token}.{secrets.token_urlsafe(16)}"
        token = f"{payload}.{self._sign(payload)}"
        session = Session(csrf_token=csrf_token, expires_at=expires_at)
        return token, session

    def session(self, request: web.Request) -> Session | None:
        parts = request.cookies.get(SESSION_COOKIE, "").split(".")
        if len(parts) != 4:
            return None
        expires, csrf_token, nonce, signature = parts
        payload = f"{expires}.{csrf_token}.{nonce}"
        if not hmac.compare_digest(signature, self._sign(payload)):
            return None
        try:
            expires_at = int(expires)
        except ValueError:
            return None
        if expires_at <= time.time():
            return None
        return Session(csrf_token=csrf_token, expires_at=expires_at)

    def logout(self, request: web.Request) -> None:
        return None

    def require_csrf(self, request: web.Request) -> Session:
        session = self.session(request)
        supplied = request.headers.get("X-CSRF-Token", "")
        if session is None or not hmac.compare_digest(supplied, session.csrf_token):
            raise web.HTTPForbidden(text="CSRF token inválido.")
        return session


def secure_headers(response: web.StreamResponse) -> None:
    response.headers["Cache-Control"] = "no-store"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; img-src 'self' data:; style-src 'self'; script-src 'self'; "
        "connect-src 'self'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'"
    )
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"

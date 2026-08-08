"""Session helpers backed by Flask's signed session cookie (Dash apps run on a
Flask server under the hood, `app.server`). The JWT issued by POST /auth/login
is stored in the cookie so it survives page navigation and browser refresh; it
is never persisted server-side, so nothing about this needs a shared store to
support multiple concurrent clinicians."""
from typing import Optional

from flask import session


def log_in(token: str, username: str, role: str) -> None:
    session["token"] = token
    session["username"] = username
    session["role"] = role


def log_out() -> None:
    session.clear()


def is_authenticated() -> bool:
    return "token" in session


def current_token() -> Optional[str]:
    return session.get("token")


def current_username() -> Optional[str]:
    return session.get("username")


def current_role() -> Optional[str]:
    return session.get("role")


def is_admin() -> bool:
    return session.get("role") == "admin"

"""User accounts and login sessions.

Accounts are identified by an email address OR a phone number (either one, or both), plus a
password. Passwords are hashed with scrypt (Python stdlib -- no extra dependency) using a random
per-user salt; the plain password is never stored or logged.

Sessions: logging in creates a random token that is sent to the browser as an HttpOnly cookie.
Only a SHA-256 hash of the token is stored, so a copy of legal_aid.db alone cannot be used to
impersonate anyone. Sessions expire after SESSION_DAYS.

Data separation: cases and documents carry a user_id column, and every API endpoint that reads
or changes them filters by the logged-in user (see main.py). Rows that existed before accounts
were introduced have no owner; claim_unowned_data() assigns them to the admin account at
startup so nothing is lost.
"""
from __future__ import annotations

import hashlib
import hmac
import logging
import os
import re
import secrets
import sqlite3
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

import case_store

logger = logging.getLogger("legal_aid_ai.auth")

SESSION_COOKIE = "legal_aid_session"
SESSION_DAYS = 30
# Secure cookies are only sent over HTTPS; local development runs on plain http://localhost, so
# this is off by default and must be switched on (AUTH_COOKIE_SECURE=true) when deployed.
COOKIE_SECURE = os.getenv("AUTH_COOKIE_SECURE", "false").strip().lower() in {"1", "true", "yes", "on"}

MIN_PASSWORD_CHARS = 8
MAX_PASSWORD_CHARS = 128

ADMIN_EMAIL = os.getenv("LEGAL_AID_ADMIN_EMAIL", "admin@legalaid.local").strip().lower()

# scrypt cost parameters (n=2**14, r=8, p=1: ~16 MB, the commonly recommended interactive-login
# setting). Stored alongside each hash so they can be raised later without breaking old hashes.
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1

# Brute-force protection: after MAX_FAILED_LOGINS wrong passwords for one identifier within
# LOCKOUT_WINDOW_SECONDS, further attempts are refused until the window passes. In-memory, so it
# resets on restart -- adequate for a single-process server.
MAX_FAILED_LOGINS = 5
LOCKOUT_WINDOW_SECONDS = 15 * 60
_failed_logins: dict[str, list[float]] = {}
_failed_lock = threading.Lock()

EMAIL_PATTERN = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class AuthError(ValueError):
    """A user-facing problem with sign-up or login input (shown as-is in the UI)."""


class LoginLockedError(AuthError):
    pass


def init_db(db_path: Path | None = None) -> None:
    case_store.init_db(db_path)
    with case_store.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE,
                phone TEXT UNIQUE,
                password_hash TEXT NOT NULL,
                is_admin INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                CHECK (email IS NOT NULL OR phone IS NOT NULL)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS auth_sessions (
                token_hash TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_auth_sessions_user ON auth_sessions(user_id)")


# --- Identifiers and passwords ---


def normalize_email(value: str) -> str:
    email = str(value or "").strip().lower()
    if len(email) > 254 or not EMAIL_PATTERN.match(email):
        raise AuthError("Enter a valid email address.")
    return email


def normalize_phone(value: str) -> str:
    """Stored in one canonical form so "98765 43210", "+91-9876543210" and "09876543210" are the
    same account. A bare 10-digit Indian mobile number gets +91; anything else must already carry
    a country code (+ followed by 8-15 digits)."""
    raw = str(value or "").strip()
    digits = re.sub(r"\D", "", raw)
    if raw.startswith("+"):
        if 8 <= len(digits) <= 15:
            return f"+{digits}"
        raise AuthError("Enter a valid phone number.")
    if len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    if len(digits) == 10 and digits[0] in "6789":
        return f"+91{digits}"
    raise AuthError("Enter a valid 10-digit mobile number, or include the country code (e.g. +44...).")


def parse_identifier(identifier: str) -> tuple[str, str]:
    """"Email or phone" login box -> ("email", value) or ("phone", value)."""
    text = str(identifier or "").strip()
    if not text:
        raise AuthError("Enter your email address or phone number.")
    if "@" in text:
        return "email", normalize_email(text)
    return "phone", normalize_phone(text)


def validate_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD_CHARS:
        raise AuthError(f"Password must be at least {MIN_PASSWORD_CHARS} characters.")
    if len(password) > MAX_PASSWORD_CHARS:
        raise AuthError(f"Password must be at most {MAX_PASSWORD_CHARS} characters.")


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.scrypt(password.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=32)
    return f"scrypt${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, n, r, p, salt_hex, digest_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        digest = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(digest_hex) // 2,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(digest.hex(), digest_hex)


# A real hash of a random password, checked when the account does not exist so a login attempt
# for an unknown identifier takes as long as one for a real account (no timing hint about which
# emails/phones are registered).
_DUMMY_HASH = hash_password(secrets.token_hex(16))


# --- Users ---


def public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": user["id"],
        "email": user["email"],
        "phone": user["phone"],
        "is_admin": bool(user["is_admin"]),
        "created_at": user["created_at"],
    }


def create_user(
    *,
    email: str | None = None,
    phone: str | None = None,
    password: str,
    is_admin: bool = False,
    db_path: Path | None = None,
) -> dict[str, Any]:
    email = normalize_email(email) if email and email.strip() else None
    phone = normalize_phone(phone) if phone and phone.strip() else None
    if not email and not phone:
        raise AuthError("Enter an email address or a phone number.")
    validate_password(password)
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        if email and conn.execute("SELECT 1 FROM users WHERE email = ?", (email,)).fetchone():
            raise AuthError("An account with this email already exists. Try signing in.")
        if phone and conn.execute("SELECT 1 FROM users WHERE phone = ?", (phone,)).fetchone():
            raise AuthError("An account with this phone number already exists. Try signing in.")
        try:
            cursor = conn.execute(
                "INSERT INTO users (email, phone, password_hash, is_admin, created_at) VALUES (?, ?, ?, ?, ?)",
                (email, phone, hash_password(password), int(is_admin), case_store.utc_timestamp()),
            )
        except sqlite3.IntegrityError as exc:  # a concurrent sign-up won the race
            raise AuthError("An account with these details already exists. Try signing in.") from exc
        user_id = int(cursor.lastrowid)
    return get_user(user_id, db_path)


def get_user(user_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    return dict(row) if row else None


def find_user(identifier: str, db_path: Path | None = None) -> dict[str, Any] | None:
    kind, value = parse_identifier(identifier)
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        row = conn.execute(f"SELECT * FROM users WHERE {kind} = ?", (value,)).fetchone()  # noqa: S608 -- kind is "email"/"phone"
    return dict(row) if row else None


def set_password(user_id: int, password: str, db_path: Path | None = None) -> None:
    """Changes the password and signs the user out everywhere (all existing sessions end)."""
    validate_password(password)
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (hash_password(password), user_id))
        conn.execute("DELETE FROM auth_sessions WHERE user_id = ?", (user_id,))


def authenticate(identifier: str, password: str, db_path: Path | None = None) -> dict[str, Any]:
    key = str(identifier or "").strip().lower()
    _check_not_locked(key)
    user = find_user(identifier, db_path)
    if user is None:
        verify_password(password or "", _DUMMY_HASH)
        _record_failure(key)
        raise AuthError("Incorrect email/phone or password.")
    if not verify_password(password or "", user["password_hash"]):
        _record_failure(key)
        raise AuthError("Incorrect email/phone or password.")
    with _failed_lock:
        _failed_logins.pop(key, None)
    return user


def _check_not_locked(key: str) -> None:
    now = time.monotonic()
    with _failed_lock:
        recent = [t for t in _failed_logins.get(key, []) if now - t < LOCKOUT_WINDOW_SECONDS]
        _failed_logins[key] = recent
        if len(recent) >= MAX_FAILED_LOGINS:
            raise LoginLockedError("Too many failed sign-in attempts. Please wait 15 minutes and try again.")


def _record_failure(key: str) -> None:
    with _failed_lock:
        _failed_logins.setdefault(key, []).append(time.monotonic())


# --- Sessions ---


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(user_id: int, db_path: Path | None = None) -> str:
    init_db(db_path)
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=SESSION_DAYS)
    with case_store.connect(db_path) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE expires_at < ?", (now.isoformat(timespec="seconds"),))
        conn.execute(
            "INSERT INTO auth_sessions (token_hash, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (_token_hash(token), user_id, now.isoformat(timespec="seconds"), expires.isoformat(timespec="seconds")),
        )
    return token


def user_for_session(token: str | None, db_path: Path | None = None) -> dict[str, Any] | None:
    if not token:
        return None
    init_db(db_path)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with case_store.connect(db_path) as conn:
        row = conn.execute(
            """
            SELECT users.* FROM auth_sessions
            JOIN users ON users.id = auth_sessions.user_id
            WHERE auth_sessions.token_hash = ? AND auth_sessions.expires_at > ?
            """,
            (_token_hash(token), now),
        ).fetchone()
    return dict(row) if row else None


def delete_session(token: str | None, db_path: Path | None = None) -> None:
    if not token:
        return
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        conn.execute("DELETE FROM auth_sessions WHERE token_hash = ?", (_token_hash(token),))


# --- Admin account and pre-accounts data ---


def ensure_admin(db_path: Path | None = None) -> dict[str, Any]:
    """Returns the admin account, creating it if needed. Its password comes from
    LEGAL_AID_ADMIN_PASSWORD; if that is not set, a random one is generated and logged ONCE
    (change it with `python set_admin_password.py`)."""
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM users WHERE is_admin = 1 ORDER BY id LIMIT 1").fetchone()
    if row:
        return dict(row)
    password = os.getenv("LEGAL_AID_ADMIN_PASSWORD", "")
    generated = not password
    if generated:
        password = secrets.token_urlsafe(12)
    admin = create_user(email=ADMIN_EMAIL, password=password, is_admin=True, db_path=db_path)
    if generated:
        logger.warning(
            "Created admin account %s with generated password: %s -- change it with `python set_admin_password.py`",
            ADMIN_EMAIL,
            password,
        )
    else:
        logger.info("Created admin account %s", ADMIN_EMAIL)
    return admin


def claim_unowned_data(db_path: Path | None = None) -> dict[str, int]:
    """Assigns every case and document that has no owner (i.e. created before accounts existed)
    to the admin account. Nothing is deleted or otherwise changed. Safe to run repeatedly."""
    import document_store  # deferred: document_store imports case_store too; keep this module's import light

    document_store.init_db(db_path)
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        unowned_cases = int(conn.execute("SELECT COUNT(*) FROM cases WHERE user_id IS NULL").fetchone()[0])
        unowned_documents = int(conn.execute("SELECT COUNT(*) FROM documents WHERE user_id IS NULL").fetchone()[0])
    if not unowned_cases and not unowned_documents:
        return {"cases": 0, "documents": 0}
    admin = ensure_admin(db_path)
    with case_store.connect(db_path) as conn:
        conn.execute("UPDATE cases SET user_id = ? WHERE user_id IS NULL", (admin["id"],))
        conn.execute("UPDATE documents SET user_id = ? WHERE user_id IS NULL", (admin["id"],))
    logger.info(
        "Assigned pre-account data to admin %s: cases=%s documents=%s",
        admin["email"],
        unowned_cases,
        unowned_documents,
    )
    return {"cases": unowned_cases, "documents": unowned_documents}

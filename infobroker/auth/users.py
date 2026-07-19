"""Hashed local user accounts (replaces plaintext users.json)."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from pathlib import Path
from typing import Optional

from infobroker.config import get_settings


def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000
    )
    return salt, digest.hex()


def _verify(password: str, salt: str, password_hash: str) -> bool:
    _, digest = _hash_password(password, salt)
    return secrets.compare_digest(digest, password_hash)


def load_users(path: Optional[Path] = None) -> dict:
    path = path or get_settings().users_path
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def save_users(users: dict, path: Optional[Path] = None) -> None:
    path = path or get_settings().users_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(users, indent=2), encoding="utf-8")


def register(username: str, password: str) -> str:
    users = load_users()
    if username in users:
        raise ValueError("Username already exists")
    salt, pw_hash = _hash_password(password)
    users[username] = {
        "salt": salt,
        "password_hash": pw_hash,
        "settings": {"broker": "paper"},
    }
    save_users(users)
    return username


def login(username: str, password: str) -> Optional[str]:
    users = load_users()
    user = users.get(username)
    if not user:
        return None
    # Legacy plaintext migration
    if "password" in user and "password_hash" not in user:
        if user["password"] != password:
            return None
        salt, pw_hash = _hash_password(password)
        user.pop("password", None)
        user["salt"] = salt
        user["password_hash"] = pw_hash
        users[username] = user
        save_users(users)
        return username
    if _verify(password, user["salt"], user["password_hash"]):
        return username
    return None


def migrate_legacy_users_json(legacy_path: Path) -> int:
    """One-time migrate root users.json (plaintext) into data/users.json hashed store."""
    if not legacy_path.exists():
        return 0
    settings = get_settings()
    if settings.users_path.exists():
        return 0
    legacy = json.loads(legacy_path.read_text(encoding="utf-8"))
    migrated = 0
    users: dict = {}
    for username, payload in legacy.items():
        password = payload.get("password", "")
        salt, pw_hash = _hash_password(password or secrets.token_hex(8))
        users[username] = {
            "salt": salt,
            "password_hash": pw_hash,
            "settings": {"broker": "paper"},
            "legacy_portfolio": payload.get("portfolio", {}),
        }
        migrated += 1
    save_users(users)
    return migrated

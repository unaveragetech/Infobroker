"""Persist API keys and app prefs to .env; never echo full secrets."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from infobroker.config import ROOT, get_settings

ENV_PATH = ROOT / ".env"

# Keys the UI may set
WRITABLE_KEYS = [
    "INFOBROKER_BROKER",
    "INFOBROKER_DATA_PROVIDER",
    "INFOBROKER_STARTING_CASH",
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET",
    "ALPACA_PAPER",
    "PUBLIC_PERSONAL_SECRET",
    "PUBLIC_ACCOUNT_ID",
    "TRADIER_ACCESS_TOKEN",
    "TRADIER_ACCOUNT_ID",
    "TRADIER_SANDBOX",
    "FINNHUB_API_KEY",
    "ALPHAVANTAGE_API_KEY",
]

SECRET_KEYS = {
    "ALPACA_API_KEY",
    "ALPACA_API_SECRET",
    "PUBLIC_PERSONAL_SECRET",
    "PUBLIC_ACCOUNT_ID",
    "TRADIER_ACCESS_TOKEN",
    "TRADIER_ACCOUNT_ID",
    "FINNHUB_API_KEY",
    "ALPHAVANTAGE_API_KEY",
}


def _mask(value: str) -> str:
    """UI-safe hint only — never return enough of a secret to reconstruct it."""
    if not value:
        return ""
    n = len(value)
    if n <= 4:
        return "••••"
    # Show length only + last 2 chars (account IDs / keys stay opaque)
    return f"••••••{value[-2:]} ({n} chars)"


def _read_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}
    out: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, _, val = raw.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        out[key] = val
    return out


def _write_env_file(path: Path, values: dict[str, str]) -> None:
    existing_lines: list[str] = []
    if path.exists():
        existing_lines = path.read_text(encoding="utf-8").splitlines()

    used: set[str] = set()
    new_lines: list[str] = []
    for line in existing_lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            new_lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        if key in values:
            new_lines.append(f"{key}={values[key]}")
            used.add(key)
        else:
            new_lines.append(line)

    for key, val in values.items():
        if key not in used:
            new_lines.append(f"{key}={val}")

    path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def reload_runtime_env() -> None:
    load_dotenv(ENV_PATH, override=True)
    from infobroker.data.providers import clear_provider_cache

    clear_provider_cache()


def get_public_settings() -> dict[str, Any]:
    """Settings safe for the UI — never returns full secrets or account IDs."""
    reload_runtime_env()
    s = get_settings()
    env = _read_env_file(ENV_PATH)

    def val(key: str, fallback: str = "") -> str:
        return os.getenv(key) or env.get(key) or fallback

    def secret_status(key: str) -> dict[str, Any]:
        raw = val(key)
        return {
            "configured": bool(raw),
            "masked": _mask(raw) if raw else "",
        }

    return {
        "broker": s.broker,
        "data_provider": s.data_provider,
        "starting_cash": s.starting_cash,
        "alpaca_paper": s.alpaca_paper,
        "tradier_sandbox": s.tradier_sandbox,
        "secrets": {
            "ALPACA_API_KEY": secret_status("ALPACA_API_KEY"),
            "ALPACA_API_SECRET": secret_status("ALPACA_API_SECRET"),
            "PUBLIC_PERSONAL_SECRET": secret_status("PUBLIC_PERSONAL_SECRET"),
            "PUBLIC_ACCOUNT_ID": secret_status("PUBLIC_ACCOUNT_ID"),
            "TRADIER_ACCESS_TOKEN": secret_status("TRADIER_ACCESS_TOKEN"),
            "TRADIER_ACCOUNT_ID": secret_status("TRADIER_ACCOUNT_ID"),
            "FINNHUB_API_KEY": secret_status("FINNHUB_API_KEY"),
            "ALPHAVANTAGE_API_KEY": secret_status("ALPHAVANTAGE_API_KEY"),
        },
        "flags": {
            "ALPACA_PAPER": s.alpaca_paper,
            "TRADIER_SANDBOX": s.tradier_sandbox,
        },
        "security": {
            "secrets_echo": False,
            "settings_localhost_only": True,
            "env_path": ".env (gitignored)",
        },
    }


def update_settings(payload: dict[str, Any]) -> dict[str, Any]:
    """Update .env from UI payload. Empty secret fields leave existing values."""
    current = _read_env_file(ENV_PATH)
    updates: dict[str, str] = {}

    simple_map = {
        "broker": "INFOBROKER_BROKER",
        "data_provider": "INFOBROKER_DATA_PROVIDER",
        "starting_cash": "INFOBROKER_STARTING_CASH",
        "alpaca_paper": "ALPACA_PAPER",
        "tradier_sandbox": "TRADIER_SANDBOX",
    }
    for field, env_key in simple_map.items():
        if field not in payload or payload[field] is None:
            continue
        val = payload[field]
        if isinstance(val, bool):
            updates[env_key] = "true" if val else "false"
        else:
            text = str(val).strip()
            if env_key == "INFOBROKER_BROKER":
                text = text.lower()
                if text not in {"paper", "alpaca", "public", "tradier"}:
                    raise ValueError(f"Unsupported broker: {text}")
            if env_key == "INFOBROKER_DATA_PROVIDER":
                text = text.lower().replace("yfinance", "yahoo")
                if text not in {"yahoo", "finnhub", "alphavantage", "auto"}:
                    raise ValueError(f"Unsupported data provider: {text}")
            if env_key == "INFOBROKER_STARTING_CASH":
                float(text)  # validate
            updates[env_key] = text

    secret_map = {
        "alpaca_api_key": "ALPACA_API_KEY",
        "alpaca_api_secret": "ALPACA_API_SECRET",
        "public_personal_secret": "PUBLIC_PERSONAL_SECRET",
        "public_account_id": "PUBLIC_ACCOUNT_ID",
        "tradier_access_token": "TRADIER_ACCESS_TOKEN",
        "tradier_account_id": "TRADIER_ACCOUNT_ID",
        "finnhub_api_key": "FINNHUB_API_KEY",
        "alphavantage_api_key": "ALPHAVANTAGE_API_KEY",
    }
    for field, env_key in secret_map.items():
        if field not in payload:
            continue
        val = payload[field]
        if val is None:
            continue
        text = str(val).strip()
        # Skip blanks and masked placeholders so we don't wipe keys
        if not text or "•" in text or re.fullmatch(r".*••••.*", text):
            continue
        updates[env_key] = text

    merged = {**current, **updates}
    # Only persist known keys (+ keep unknown existing)
    to_write = {k: v for k, v in merged.items() if k in WRITABLE_KEYS or k in current}
    for k, v in updates.items():
        to_write[k] = v
    _write_env_file(ENV_PATH, to_write)
    reload_runtime_env()
    return get_public_settings()

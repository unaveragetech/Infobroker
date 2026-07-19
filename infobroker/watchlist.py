"""Tracked tickers persistence."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from infobroker.config import DATA_DIR

WATCHLIST_PATH = DATA_DIR / "watchlist.json"
_SYMBOL_RE = re.compile(r"^[A-Z][A-Z0-9.\-]{0,11}$")

DEFAULT_WATCHLIST = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "SPY",
    "QQQ",
]


def _load() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not WATCHLIST_PATH.exists():
        data = {"symbols": DEFAULT_WATCHLIST, "notes": {}}
        _save(data)
        return data
    try:
        data = json.loads(WATCHLIST_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = {"symbols": list(DEFAULT_WATCHLIST), "notes": {}}
        _save(data)
        return data
    if "symbols" not in data or not isinstance(data["symbols"], list):
        data["symbols"] = list(DEFAULT_WATCHLIST)
    data.setdefault("notes", {})
    return data


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    WATCHLIST_PATH.write_text(json.dumps(data, indent=2), encoding="utf-8")


def normalize_symbol(symbol: str) -> str:
    sym = (symbol or "").strip().upper().replace(" ", "")
    # Common Yahoo quirk
    if sym == "BRK.B":
        sym = "BRK-B"
    return sym


def validate_symbol(symbol: str) -> str:
    sym = normalize_symbol(symbol)
    if not sym or not _SYMBOL_RE.match(sym):
        raise ValueError(f"Invalid ticker symbol: {symbol!r}")
    return sym


def list_symbols() -> list[str]:
    return list(_load()["symbols"])


def add_symbol(symbol: str, note: str = "") -> list[str]:
    sym = validate_symbol(symbol)
    data = _load()
    if sym not in data["symbols"]:
        data["symbols"].append(sym)
    if note:
        data["notes"][sym] = note.strip()[:200]
    _save(data)
    return data["symbols"]


def remove_symbol(symbol: str) -> list[str]:
    sym = normalize_symbol(symbol)
    data = _load()
    data["symbols"] = [s for s in data["symbols"] if s != sym]
    data["notes"].pop(sym, None)
    _save(data)
    return data["symbols"]


def get_watchlist() -> dict[str, Any]:
    data = _load()
    return {"symbols": data["symbols"], "notes": data.get("notes", {})}

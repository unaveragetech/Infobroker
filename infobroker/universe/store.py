"""Persist the market universe (listings + quote cache)."""

from __future__ import annotations

import json
import threading
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from infobroker.config import DATA_DIR

UNIVERSE_PATH = DATA_DIR / "universe.json"
_LOCK = threading.RLock()

_EMPTY: dict[str, Any] = {
    "version": 1,
    "listings_as_of": None,
    "quotes_as_of": None,
    "refresh_cursor": 0,
    "symbols": {},  # symbol -> meta + optional quote
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _default() -> dict[str, Any]:
    return deepcopy(_EMPTY)


def load_universe() -> dict[str, Any]:
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        if not UNIVERSE_PATH.exists():
            data = _default()
            save_universe(data)
            return data
        try:
            data = json.loads(UNIVERSE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            data = _default()
            save_universe(data)
            return data
        if not isinstance(data.get("symbols"), dict):
            data["symbols"] = {}
        data.setdefault("version", 1)
        data.setdefault("listings_as_of", None)
        data.setdefault("quotes_as_of", None)
        data.setdefault("refresh_cursor", 0)
        return data


def save_universe(data: dict[str, Any]) -> None:
    with _LOCK:
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        tmp = UNIVERSE_PATH.with_suffix(".tmp")
        payload = json.dumps(data, indent=2, ensure_ascii=False)
        tmp.write_text(payload, encoding="utf-8")
        tmp.replace(UNIVERSE_PATH)


def symbol_count(data: Optional[dict[str, Any]] = None) -> int:
    d = data if data is not None else load_universe()
    return len(d.get("symbols") or {})


def quote_count(data: Optional[dict[str, Any]] = None) -> int:
    d = data if data is not None else load_universe()
    return sum(1 for v in (d.get("symbols") or {}).values() if v.get("quote"))


def path() -> Path:
    return UNIVERSE_PATH

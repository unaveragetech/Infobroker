"""Auto-track universe gainers onto the watchlist."""

from __future__ import annotations

import json
import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from infobroker.config import DATA_DIR
from infobroker.watchlist import add_symbol, list_symbols

AUTO_TRACK_PATH = DATA_DIR / "auto_track.json"

_DEFAULT: dict[str, Any] = {
    "enabled": False,
    "min_change_pct": 5.0,
    "exchanges": [],  # empty = all
    "asset_classes": ["stock", "adr"],  # empty = all
    "max_adds_per_scan": 12,
    "poll_sec": 60,
    "include_etf": False,
    "last_run": None,
    "last_added": [],
    "last_hits": 0,
    "last_error": None,
}

_lock = threading.RLock()
_worker: Optional[threading.Thread] = None
_stop = threading.Event()
_status: dict[str, Any] = {
    "running": False,
    "last_cycle_at": None,
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not AUTO_TRACK_PATH.exists():
        _save(dict(_DEFAULT))
        return dict(_DEFAULT)
    try:
        data = json.loads(AUTO_TRACK_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        data = dict(_DEFAULT)
        _save(data)
        return data
    out = dict(_DEFAULT)
    out.update(data or {})
    # normalize types
    out["enabled"] = bool(out.get("enabled"))
    out["min_change_pct"] = float(out.get("min_change_pct") or 5.0)
    out["max_adds_per_scan"] = max(1, min(int(out.get("max_adds_per_scan") or 12), 50))
    out["poll_sec"] = max(30, min(int(out.get("poll_sec") or 60), 600))
    out["exchanges"] = list(out.get("exchanges") or [])
    out["asset_classes"] = list(out.get("asset_classes") or [])
    out["include_etf"] = bool(out.get("include_etf"))
    out.setdefault("last_added", [])
    return out


def _save(data: dict[str, Any]) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = AUTO_TRACK_PATH.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    tmp.replace(AUTO_TRACK_PATH)


def get_auto_track_settings() -> dict[str, Any]:
    with _lock:
        cfg = _load()
        return {
            **cfg,
            "worker": dict(_status),
            "path": str(AUTO_TRACK_PATH),
        }


def update_auto_track_settings(payload: dict[str, Any]) -> dict[str, Any]:
    with _lock:
        cfg = _load()
        if "enabled" in payload and payload["enabled"] is not None:
            cfg["enabled"] = bool(payload["enabled"])
        if "min_change_pct" in payload and payload["min_change_pct"] is not None:
            cfg["min_change_pct"] = max(0.5, min(float(payload["min_change_pct"]), 100.0))
        if "max_adds_per_scan" in payload and payload["max_adds_per_scan"] is not None:
            cfg["max_adds_per_scan"] = max(1, min(int(payload["max_adds_per_scan"]), 50))
        if "poll_sec" in payload and payload["poll_sec"] is not None:
            cfg["poll_sec"] = max(30, min(int(payload["poll_sec"]), 600))
        if "include_etf" in payload and payload["include_etf"] is not None:
            cfg["include_etf"] = bool(payload["include_etf"])
        if "exchanges" in payload and payload["exchanges"] is not None:
            raw = payload["exchanges"]
            if isinstance(raw, str):
                cfg["exchanges"] = [x.strip() for x in raw.split(",") if x.strip()]
            else:
                cfg["exchanges"] = [str(x).strip() for x in raw if str(x).strip()]
        if "asset_classes" in payload and payload["asset_classes"] is not None:
            raw = payload["asset_classes"]
            if isinstance(raw, str):
                cfg["asset_classes"] = [x.strip().lower() for x in raw.split(",") if x.strip()]
            else:
                cfg["asset_classes"] = [str(x).strip().lower() for x in raw if str(x).strip()]
        _save(cfg)
        return get_auto_track_settings()


def scan_and_track(force: bool = False) -> dict[str, Any]:
    """Scan quoted universe for gainers and add new hits to the watchlist."""
    from infobroker.universe.engine import quoted_rows

    with _lock:
        cfg = _load()
        if not cfg["enabled"] and not force:
            return {
                "ok": True,
                "skipped": True,
                "reason": "auto-track disabled",
                "added": [],
                "hits": 0,
            }

        threshold = float(cfg["min_change_pct"])
        exchanges = {e.lower() for e in (cfg.get("exchanges") or [])}
        classes = {c.lower() for c in (cfg.get("asset_classes") or [])}
        include_etf = bool(cfg.get("include_etf"))
        max_adds = int(cfg["max_adds_per_scan"])

        watched = set(list_symbols())
        candidates: list[dict[str, Any]] = []
        for row in quoted_rows():
            pct = row.get("change_pct_day")
            if pct is None or float(pct) < threshold:
                continue
            if row.get("etf") and not include_etf:
                continue
            exch = (row.get("exchange") or "").lower()
            if exchanges and not any(e in exch for e in exchanges):
                continue
            ac = (row.get("asset_class") or "").lower()
            if classes and ac and ac not in classes:
                # allow "other" stocks through if stock requested
                if not (ac == "other" and "stock" in classes):
                    continue
            sym = row["symbol"]
            if sym in watched:
                continue
            candidates.append(row)

        candidates.sort(key=lambda r: float(r.get("change_pct_day") or 0), reverse=True)
        added: list[dict[str, Any]] = []
        for row in candidates[:max_adds]:
            sym = row["symbol"]
            note = f"auto-gainer +{float(row.get('change_pct_day') or 0):.1f}% day"
            try:
                add_symbol(sym, note=note)
                watched.add(sym)
                added.append(
                    {
                        "symbol": sym,
                        "change_pct_day": row.get("change_pct_day"),
                        "price": row.get("price"),
                        "exchange": row.get("exchange"),
                        "name": row.get("name"),
                    }
                )
            except Exception:
                continue

        cfg["last_run"] = _now()
        cfg["last_added"] = added
        cfg["last_hits"] = len(candidates)
        cfg["last_error"] = None
        _save(cfg)
        with _lock:
            _status["last_cycle_at"] = cfg["last_run"]

        return {
            "ok": True,
            "skipped": False,
            "threshold": threshold,
            "candidates": len(candidates),
            "added": added,
            "hits": len(candidates),
            "as_of": cfg["last_run"],
            "settings": {
                "exchanges": cfg.get("exchanges"),
                "asset_classes": cfg.get("asset_classes"),
                "include_etf": include_etf,
            },
        }


def _worker_loop() -> None:
    _status["running"] = True
    try:
        while not _stop.is_set():
            cfg = _load()
            wait = int(cfg.get("poll_sec") or 60)
            if cfg.get("enabled"):
                try:
                    scan_and_track(force=False)
                except Exception as exc:  # noqa: BLE001
                    with _lock:
                        c = _load()
                        c["last_error"] = str(exc)[:200]
                        _save(c)
            # wake periodically; shorter sleep chunks so stop is responsive
            for _ in range(max(1, wait // 5)):
                if _stop.wait(5):
                    break
    finally:
        _status["running"] = False


def start_auto_track_worker() -> None:
    global _worker
    if _worker and _worker.is_alive():
        return
    _stop.clear()
    _worker = threading.Thread(target=_worker_loop, name="auto-track-gainers", daemon=True)
    _worker.start()


def stop_auto_track_worker() -> None:
    _stop.set()
    t = _worker
    if t and t.is_alive():
        t.join(timeout=3)

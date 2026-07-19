"""Market-wide universe engine: listings sync + rotating quote refresh."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

from infobroker.data.multisource import fetch_snapshot_multisource, provider_status
from infobroker.universe.listings import fetch_us_listings
from infobroker.universe.store import (
    load_universe,
    path as universe_path,
    quote_count,
    save_universe,
    symbol_count,
)

# Prefer liquid / index names when the quote cache is still filling
_SEED_PRIORITY = [
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
    "VTI",
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "JPM",
    "XOM",
    "UNH",
    "LLY",
    "V",
    "MA",
    "WMT",
    "COST",
    "AVGO",
    "NFLX",
    "BAC",
    "DIS",
]

_LISTINGS_MAX_AGE_SEC = 24 * 3600
_WORKER_INTERVAL_SEC = 35
_DEFAULT_BATCH = 160
_MAX_BATCH = 400

_worker_thread: Optional[threading.Thread] = None
_worker_stop = threading.Event()
_worker_status: dict[str, Any] = {
    "running": False,
    "last_cycle_at": None,
    "last_error": None,
    "last_batch_ok": 0,
    "last_batch_size": 0,
}
_status_lock = threading.Lock()
_refresh_lock = threading.Lock()


def _parse_iso(raw: Optional[str]) -> Optional[datetime]:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return None


def _age_seconds(raw: Optional[str]) -> Optional[float]:
    dt = _parse_iso(raw)
    if not dt:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc) - dt).total_seconds()


def listings_stale(data: Optional[dict[str, Any]] = None) -> bool:
    d = data if data is not None else load_universe()
    if symbol_count(d) < 100:
        return True
    age = _age_seconds(d.get("listings_as_of"))
    if age is None:
        return True
    return age > _LISTINGS_MAX_AGE_SEC


def refresh_listings(force: bool = False) -> dict[str, Any]:
    """Pull official NASDAQ/NYSE directories into data/universe.json."""
    with _refresh_lock:
        data = load_universe()
        if not force and not listings_stale(data):
            return {
                "ok": True,
                "skipped": True,
                "reason": "listings still fresh",
                "count": symbol_count(data),
                "listings_as_of": data.get("listings_as_of"),
            }

        rows = fetch_us_listings()
        if not rows:
            raise RuntimeError("NASDAQ symbol directory returned zero rows")

        old = data.get("symbols") or {}
        merged: dict[str, Any] = {}
        for row in rows:
            sym = row["symbol"]
            prev = old.get(sym) or {}
            merged[sym] = {
                "symbol": sym,
                "name": row.get("name") or prev.get("name") or sym,
                "exchange": row.get("exchange") or prev.get("exchange") or "Unknown",
                "etf": bool(row.get("etf")),
                "asset_class": row.get("asset_class") or prev.get("asset_class") or "other",
                "source": row.get("source") or prev.get("source"),
                "quote": prev.get("quote"),
            }

        # Drop symbols no longer listed (keep if they still have a quote? no — trust directory)
        data["symbols"] = merged
        data["listings_as_of"] = datetime.now(timezone.utc).isoformat()
        # Keep cursor in range
        data["refresh_cursor"] = int(data.get("refresh_cursor") or 0) % max(len(merged), 1)
        save_universe(data)
        return {
            "ok": True,
            "skipped": False,
            "count": len(merged),
            "listings_as_of": data["listings_as_of"],
            "exchanges": _exchange_counts(merged),
        }


def _exchange_counts(symbols: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for meta in symbols.values():
        ex = meta.get("exchange") or "Unknown"
        counts[ex] = counts.get(ex, 0) + 1
    return dict(sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])))


def _ordered_symbols(data: dict[str, Any]) -> list[str]:
    """Priority seeds → never-quoted → stale quotes → fresh (cursor rotates through)."""
    symbols = data.get("symbols") or {}
    if not symbols:
        return []
    priority = [s for s in _SEED_PRIORITY if s in symbols]
    pri_set = set(priority)
    unquoted: list[str] = []
    stale: list[str] = []
    fresh: list[str] = []
    for sym, meta in symbols.items():
        if sym in pri_set:
            continue
        q = meta.get("quote") or {}
        if q.get("price") is None:
            unquoted.append(sym)
            continue
        age = _age_seconds(q.get("as_of"))
        if age is None or age > 45 * 60:
            stale.append(sym)
        else:
            fresh.append(sym)
    unquoted.sort()
    stale.sort()
    fresh.sort()
    return priority + unquoted + stale + fresh


def _apply_quote(meta: dict[str, Any], snap: dict[str, Any]) -> None:
    prev_q = meta.get("quote") or {}
    spark = (snap.get("sparkline") or [])[-12:]
    if not spark:
        spark = (prev_q.get("sparkline") or [])[-12:]
    week = snap.get("change_pct_week")
    if week is None:
        week = prev_q.get("change_pct_week")
    meta["quote"] = {
        "price": snap.get("price"),
        "change_abs_day": snap.get("change_abs_day"),
        "change_pct_day": snap.get("change_pct_day"),
        "change_pct_week": week,
        "volume": snap.get("volume"),
        "rel_volume": snap.get("rel_volume"),
        "high": snap.get("high"),
        "low": snap.get("low"),
        "sparkline": spark,
        "as_of": snap.get("as_of"),
        "source": snap.get("source") or "yahoo",
    }
    if snap.get("name") and (not meta.get("name") or meta.get("name") == meta.get("symbol")):
        meta["name"] = snap["name"]


def refresh_quotes(batch_size: int = _DEFAULT_BATCH) -> dict[str, Any]:
    """Refresh the next rotating batch — bulk Yahoo first, then per-symbol fallback."""
    from infobroker.data.highlights import fetch_yahoo_quotes_bulk

    batch_size = max(10, min(int(batch_size), _MAX_BATCH))
    if listings_stale():
        try:
            refresh_listings(force=False)
        except Exception as exc:  # noqa: BLE001
            with _status_lock:
                _worker_status["last_error"] = f"listings: {exc}"

    sources_used: dict[str, int] = {}
    with _refresh_lock:
        data = load_universe()
        ordered = _ordered_symbols(data)
        if not ordered:
            return {"ok": False, "error": "universe empty — refresh listings first", "updated": 0}

        cursor = int(data.get("refresh_cursor") or 0) % len(ordered)
        batch = []
        for i in range(batch_size):
            batch.append(ordered[(cursor + i) % len(ordered)])
        data["refresh_cursor"] = (cursor + batch_size) % len(ordered)

        bulk = fetch_yahoo_quotes_bulk(batch)
        updated = 0
        errors = 0
        missing: list[str] = []
        for sym in batch:
            meta = data["symbols"].get(sym)
            if not meta:
                continue
            snap = bulk.get(sym)
            if snap:
                src = snap.get("source") or "yahoo_bulk"
                sources_used[src] = sources_used.get(src, 0) + 1
                _apply_quote(meta, snap)
                updated += 1
            else:
                missing.append(sym)

        # Parallel chart / Finnhub fallback for bulk misses (fills sparklines too)
        if missing:
            from concurrent.futures import ThreadPoolExecutor, as_completed

            def _one(sym: str) -> tuple[str, Optional[dict[str, Any]]]:
                return sym, fetch_snapshot_multisource(
                    sym, allow_finnhub=True, allow_alphavantage=False
                )

            workers = min(18, max(4, len(missing)))
            with ThreadPoolExecutor(max_workers=workers) as pool:
                futs = [pool.submit(_one, s) for s in missing]
                for fut in as_completed(futs):
                    try:
                        sym, snap = fut.result()
                    except Exception:
                        errors += 1
                        continue
                    meta = data["symbols"].get(sym)
                    if not meta:
                        continue
                    if snap:
                        src = snap.get("source") or "yahoo"
                        sources_used[src] = sources_used.get(src, 0) + 1
                        _apply_quote(meta, snap)
                        updated += 1
                    else:
                        errors += 1

        data["quotes_as_of"] = datetime.now(timezone.utc).isoformat()
        save_universe(data)
        result = {
            "ok": True,
            "updated": updated,
            "errors": errors,
            "batch_size": len(batch),
            "bulk_hits": len(bulk),
            "cursor": data["refresh_cursor"],
            "quoted": quote_count(data),
            "total": symbol_count(data),
            "quotes_as_of": data["quotes_as_of"],
            "sources_used": sources_used,
            "providers": provider_status(),
        }
        with _status_lock:
            _worker_status["last_cycle_at"] = data["quotes_as_of"]
            _worker_status["last_batch_ok"] = updated
            _worker_status["last_batch_size"] = len(batch)
            if errors and not updated:
                _worker_status["last_error"] = f"{errors} quote failures in batch"
            elif updated:
                _worker_status["last_error"] = None
        return result


def ensure_universe(force_listings: bool = False) -> dict[str, Any]:
    """Make sure listings exist; kick a small quote batch if cache is empty."""
    info = refresh_listings(force=force_listings)
    data = load_universe()
    if quote_count(data) < 20:
        q = refresh_quotes(batch_size=60)
        info["quotes"] = q
    return info


def universe_status() -> dict[str, Any]:
    data = load_universe()
    symbols = data.get("symbols") or {}
    with _status_lock:
        worker = dict(_worker_status)
    classes: dict[str, int] = {}
    for meta in symbols.values():
        ac = meta.get("asset_class") or "other"
        classes[ac] = classes.get(ac, 0) + 1
    return {
        "total": len(symbols),
        "quoted": quote_count(data),
        "listings_as_of": data.get("listings_as_of"),
        "quotes_as_of": data.get("quotes_as_of"),
        "listings_stale": listings_stale(data),
        "refresh_cursor": data.get("refresh_cursor") or 0,
        "exchanges": _exchange_counts(symbols),
        "asset_classes": dict(sorted(classes.items(), key=lambda kv: (-kv[1], kv[0]))),
        "worker": worker,
        "path": str(universe_path()),
    }


def list_universe(
    q: str = "",
    exchange: str = "",
    asset_class: str = "",
    etf: Optional[bool] = None,
    has_quote: Optional[bool] = None,
    limit: int = 100,
    offset: int = 0,
) -> dict[str, Any]:
    data = load_universe()
    qn = (q or "").strip().upper()
    exch = (exchange or "").strip().lower()
    ac = (asset_class or "").strip().lower()
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))

    rows: list[dict[str, Any]] = []
    for sym, meta in (data.get("symbols") or {}).items():
        if qn and qn not in sym and qn not in (meta.get("name") or "").upper():
            continue
        if exch and exch not in (meta.get("exchange") or "").lower():
            continue
        if ac and (meta.get("asset_class") or "").lower() != ac:
            continue
        if etf is not None and bool(meta.get("etf")) != etf:
            continue
        quote = meta.get("quote")
        if has_quote is True and not quote:
            continue
        if has_quote is False and quote:
            continue
        rows.append(
            {
                "symbol": sym,
                "name": meta.get("name") or sym,
                "exchange": meta.get("exchange"),
                "etf": bool(meta.get("etf")),
                "asset_class": meta.get("asset_class"),
                "price": (quote or {}).get("price"),
                "change_pct_day": (quote or {}).get("change_pct_day"),
                "change_pct_week": (quote or {}).get("change_pct_week"),
                "volume": (quote or {}).get("volume"),
                "rel_volume": (quote or {}).get("rel_volume"),
                "as_of": (quote or {}).get("as_of"),
                "has_quote": bool(quote),
            }
        )

    # Quoted names first, then by |day move|, then symbol
    rows.sort(
        key=lambda r: (
            0 if r.get("has_quote") else 1,
            -(abs(r.get("change_pct_day") or 0)),
            r["symbol"],
        )
    )
    total = len(rows)
    page = rows[offset : offset + limit]
    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": page,
        "listings_as_of": data.get("listings_as_of"),
        "quotes_as_of": data.get("quotes_as_of"),
    }


def get_symbol(symbol: str) -> Optional[dict[str, Any]]:
    sym = (symbol or "").strip().upper().replace(".", "-")
    data = load_universe()
    meta = (data.get("symbols") or {}).get(sym)
    if not meta:
        return None
    return {
        "symbol": sym,
        "name": meta.get("name"),
        "exchange": meta.get("exchange"),
        "etf": bool(meta.get("etf")),
        "asset_class": meta.get("asset_class"),
        "source": meta.get("source"),
        "quote": meta.get("quote"),
    }


def quoted_rows() -> list[dict[str, Any]]:
    """All symbols that currently have a quote snapshot (for movers / highlights)."""
    data = load_universe()
    out: list[dict[str, Any]] = []
    for sym, meta in (data.get("symbols") or {}).items():
        q = meta.get("quote")
        if not q or q.get("price") is None:
            continue
        out.append(
            {
                "symbol": sym,
                "name": meta.get("name") or sym,
                "price": q.get("price"),
                "change_abs_day": q.get("change_abs_day"),
                "change_pct_day": q.get("change_pct_day"),
                "change_pct_week": q.get("change_pct_week"),
                "volume": q.get("volume"),
                "rel_volume": q.get("rel_volume"),
                "high": q.get("high"),
                "low": q.get("low"),
                "sparkline": q.get("sparkline") or [],
                "as_of": q.get("as_of"),
                "source": q.get("source") or "yahoo",
                "etf": bool(meta.get("etf")),
                "asset_class": meta.get("asset_class"),
                "exchange": meta.get("exchange"),
            }
        )
    return out


def movers(limit: int = 15) -> dict[str, Any]:
    rows = quoted_rows()
    # Prefer equities/ADRs for "stocks of day"; keep ETFs in volume
    equities = [
        r
        for r in rows
        if r.get("asset_class") in {"stock", "adr", "other"} and r["symbol"] not in {"SPY", "QQQ", "IWM", "DIA"}
    ]
    pool = equities or [r for r in rows if r["symbol"] not in {"SPY", "QQQ", "IWM", "DIA"}]
    limit = max(3, min(int(limit), 50))
    gainers = sorted(pool, key=lambda r: r.get("change_pct_day") or -999, reverse=True)[:limit]
    losers = sorted(pool, key=lambda r: r.get("change_pct_day") or 999)[:limit]
    week_gainers = sorted(pool, key=lambda r: r.get("change_pct_week") or -999, reverse=True)[:limit]
    week_losers = sorted(pool, key=lambda r: r.get("change_pct_week") or 999)[:limit]
    volume_leaders = sorted(
        [r for r in rows if r.get("volume")],
        key=lambda r: r.get("volume") or 0,
        reverse=True,
    )[:limit]
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "quoted": len(rows),
        "stocks_of_day": {"gainers": gainers, "losers": losers},
        "stocks_of_week": {"gainers": week_gainers, "losers": week_losers},
        "volume_leaders": volume_leaders,
    }


def liquid_scan_symbols(n: int = 120) -> list[str]:
    """Symbols to feed the strategy scanner — liquid quoted names, not just watchlist."""
    n = max(10, min(int(n), 300))
    rows = quoted_rows()
    # Prefer non-ETF with volume; fall back to any quoted
    equities = [
        r
        for r in rows
        if not r.get("etf") and r.get("asset_class") in {"stock", "adr", "other"}
    ]
    pool = equities if len(equities) >= 20 else rows
    pool = sorted(pool, key=lambda r: (r.get("volume") or 0), reverse=True)
    syms = [r["symbol"] for r in pool[:n]]
    if len(syms) < n:
        data = load_universe()
        for s in _SEED_PRIORITY + sorted((data.get("symbols") or {}).keys()):
            if s not in syms:
                syms.append(s)
            if len(syms) >= n:
                break
    return syms[:n]


def _worker_loop() -> None:
    with _status_lock:
        _worker_status["running"] = True
    try:
        try:
            ensure_universe(force_listings=False)
        except Exception as exc:  # noqa: BLE001
            with _status_lock:
                _worker_status["last_error"] = str(exc)

        while not _worker_stop.wait(_WORKER_INTERVAL_SEC):
            try:
                if listings_stale():
                    refresh_listings(force=False)
                refresh_quotes(batch_size=_DEFAULT_BATCH)
            except Exception as exc:  # noqa: BLE001
                with _status_lock:
                    _worker_status["last_error"] = str(exc)
                time.sleep(5)
    finally:
        with _status_lock:
            _worker_status["running"] = False


def start_background_engine() -> None:
    global _worker_thread
    if _worker_thread and _worker_thread.is_alive():
        return
    _worker_stop.clear()
    _worker_thread = threading.Thread(
        target=_worker_loop,
        name="universe-engine",
        daemon=True,
    )
    _worker_thread.start()


def stop_background_engine() -> None:
    _worker_stop.set()
    t = _worker_thread
    if t and t.is_alive():
        t.join(timeout=3)

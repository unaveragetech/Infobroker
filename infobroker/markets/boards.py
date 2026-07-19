"""Switchable market boards — US venues + foreign session proxies (US-listed)."""

from __future__ import annotations

from typing import Any, Optional

from infobroker.data.highlights import fetch_yahoo_quotes_bulk
from infobroker.markets.sessions import market_clocks
from infobroker.universe.engine import quoted_rows

# US exchange filters (substring match on listing exchange)
_US_VENUES: dict[str, dict[str, Any]] = {
    "us": {"label": "US All", "short": "US", "exchange": "", "session_id": "nyse"},
    "nasdaq": {"label": "NASDAQ", "short": "NASDAQ", "exchange": "NASDAQ", "session_id": "nyse"},
    "nyse": {"label": "NYSE", "short": "NYSE", "exchange": "NYSE", "session_id": "nyse"},
    "arca": {"label": "NYSE Arca", "short": "Arca", "exchange": "NYSE Arca", "session_id": "nyse"},
    "amex": {"label": "NYSE American", "short": "AMEX", "exchange": "NYSE American", "session_id": "nyse"},
}

# Foreign cash sessions → liquid US-listed ETFs / ADRs / indexes (Yahoo symbols)
_FOREIGN: dict[str, dict[str, Any]] = {
    "london": {
        "label": "London / UK",
        "short": "LDN",
        "session_id": "london",
        "note": "UK session proxies: US-listed ETFs and ADRs (Yahoo).",
        "symbols": [
            "EWU",
            "FXB",
            "BP",
            "SHEL",
            "UL",
            "HSBC",
            "DEO",
            "NGG",
            "BTI",
            "VOD",
            "LYG",
            "BCS",
            "RIO",
            "RELX",
            "AZN",
            "GSK",
        ],
    },
    "frankfurt": {
        "label": "Frankfurt / EU",
        "short": "FRA",
        "session_id": "frankfurt",
        "note": "Europe session proxies: US-listed ETFs and ADRs.",
        "symbols": [
            "EWG",
            "FEZ",
            "IEUR",
            "VGK",
            "SAP",
            "SIEGY",
            "ADDYY",
            "DB",
            "VWAGY",
            "NVO",
            "ASML",
            "SNY",
            "SAN",
            "BBVA",
            "ING",
            "PHG",
        ],
    },
    "tokyo": {
        "label": "Tokyo / Japan",
        "short": "TYO",
        "session_id": "tokyo",
        "note": "Japan session proxies: US-listed ETFs and ADRs.",
        "symbols": [
            "EWJ",
            "DXJ",
            "BBJP",
            "TM",
            "HMC",
            "SONY",
            "MUFG",
            "SMFG",
            "MFG",
            "NMR",
            "TAK",
            "SFTBY",
            "NTDOY",
            "CAJ",
        ],
    },
    "hongkong": {
        "label": "Hong Kong / China",
        "short": "HK",
        "session_id": "hongkong",
        "note": "HK / China session proxies: US-listed ETFs and ADRs.",
        "symbols": [
            "FXI",
            "MCHI",
            "KWEB",
            "EWH",
            "BABA",
            "JD",
            "PDD",
            "BIDU",
            "NIO",
            "LI",
            "XPEV",
            "TSM",
            "HDB",
            "INFY",
        ],
    },
    "sydney": {
        "label": "Sydney / Australia",
        "short": "SYD",
        "session_id": "sydney",
        "note": "Australia session proxies: US-listed ETFs and ADRs.",
        "symbols": [
            "EWA",
            "FXA",
            "BHP",
            "RIO",
            "WBK",
            "NABZY",
            "CMWAY",
            "JHX",
            "MESO",
        ],
    },
}

_ALL_FOCUSES = {**_US_VENUES, **_FOREIGN}


def list_market_focuses() -> list[dict[str, Any]]:
    clocks = {m["id"]: m for m in market_clocks().get("markets") or []}
    out: list[dict[str, Any]] = []
    for key, meta in _ALL_FOCUSES.items():
        sess = clocks.get(meta.get("session_id") or "")
        out.append(
            {
                "id": key,
                "label": meta["label"],
                "short": meta["short"],
                "kind": "us" if key in _US_VENUES else "foreign",
                "session_id": meta.get("session_id"),
                "is_open": bool(sess and sess.get("is_open")),
                "local_time": (sess or {}).get("local_time"),
                "hint": (sess or {}).get("hint"),
            }
        )
    return out


def _sort_rows(items: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    key = (sort or "volume").strip().lower()
    if key in {"change_desc", "gainers"}:
        return sorted(items, key=lambda r: r.get("change_pct_day") if r.get("change_pct_day") is not None else -9999, reverse=True)
    if key in {"change_asc", "losers"}:
        return sorted(items, key=lambda r: r.get("change_pct_day") if r.get("change_pct_day") is not None else 9999)
    if key in {"abs_change"}:
        return sorted(items, key=lambda r: abs(r.get("change_pct_day") or 0), reverse=True)
    if key == "symbol":
        return sorted(items, key=lambda r: r.get("symbol") or "")
    if key in {"rel_volume", "rvol"}:
        return sorted(items, key=lambda r: r.get("rel_volume") or 0, reverse=True)
    return sorted(items, key=lambda r: r.get("volume") or 0, reverse=True)


def _from_universe(exchange: str, limit: int, sort: str) -> list[dict[str, Any]]:
    exch = (exchange or "").strip().lower()
    rows = quoted_rows()
    if exch:
        rows = [r for r in rows if exch in (r.get("exchange") or "").lower()]
    rows = [r for r in rows if r.get("price") is not None]
    return _sort_rows(rows, sort)[: max(1, min(limit, 2000))]


def _from_symbols(symbols: list[str], label: str, limit: int, sort: str) -> list[dict[str, Any]]:
    bulk = fetch_yahoo_quotes_bulk(symbols[:80])
    # Prefer universe cache when present (sparklines / exchange)
    by_sym = {r["symbol"]: r for r in quoted_rows()}
    rows: list[dict[str, Any]] = []
    for sym in symbols:
        cached = by_sym.get(sym)
        snap = bulk.get(sym)
        if cached and cached.get("price") is not None:
            row = dict(cached)
            if snap and snap.get("price") is not None:
                row["price"] = snap["price"]
                row["change_pct_day"] = snap.get("change_pct_day", row.get("change_pct_day"))
                row["change_abs_day"] = snap.get("change_abs_day", row.get("change_abs_day"))
                row["volume"] = snap.get("volume") or row.get("volume")
                row["rel_volume"] = snap.get("rel_volume") or row.get("rel_volume")
            row["board"] = label
            rows.append(row)
        elif snap and snap.get("price") is not None:
            rows.append(
                {
                    "symbol": sym,
                    "name": snap.get("name") or sym,
                    "price": snap.get("price"),
                    "change_abs_day": snap.get("change_abs_day"),
                    "change_pct_day": snap.get("change_pct_day"),
                    "change_pct_week": snap.get("change_pct_week"),
                    "volume": snap.get("volume"),
                    "rel_volume": snap.get("rel_volume"),
                    "high": snap.get("high"),
                    "low": snap.get("low"),
                    "sparkline": snap.get("sparkline") or [],
                    "as_of": snap.get("as_of"),
                    "source": snap.get("source") or "yahoo_bulk",
                    "etf": False,
                    "asset_class": "stock",
                    "exchange": label,
                    "board": label,
                }
            )
    return _sort_rows(rows, sort)[: max(1, min(limit, 200))]


def build_market_board(
    focus: str = "us",
    limit: int = 180,
    sort: str = "volume",
) -> dict[str, Any]:
    """Board for a US venue or foreign session proxy list."""
    key = (focus or "us").strip().lower()
    if key in {"ny", "newyork", "new_york"}:
        key = "us"
    if key not in _ALL_FOCUSES:
        key = "us"

    meta = _ALL_FOCUSES[key]
    clocks = market_clocks()
    sess = next(
        (m for m in clocks.get("markets") or [] if m.get("id") == meta.get("session_id")),
        None,
    )

    if key in _US_VENUES:
        items = _from_universe(meta.get("exchange") or "", limit, sort)
        kind = "us"
        note = "US listings from the universe quote cache."
    else:
        items = _from_symbols(list(meta.get("symbols") or []), meta["label"], limit, sort)
        kind = "foreign"
        note = meta.get("note") or "Regional proxies."

    up_n = sum(1 for r in items if (r.get("change_pct_day") or 0) > 0.15)
    down_n = sum(1 for r in items if (r.get("change_pct_day") or 0) < -0.15)

    return {
        "focus": key,
        "kind": kind,
        "label": meta["label"],
        "short": meta["short"],
        "note": note,
        "session": sess,
        "is_open": bool(sess and sess.get("is_open")),
        "sort": sort,
        "items": items,
        "count": len(items),
        "breadth": {"up": up_n, "down": down_n, "flat": max(0, len(items) - up_n - down_n)},
        "focuses": list_market_focuses(),
        "as_of": clocks.get("as_of"),
    }


def resolve_focus_from_session(session_id: str) -> Optional[str]:
    """Map clock session id (nyse/london/…) to a board focus key."""
    sid = (session_id or "").strip().lower()
    if sid == "nyse":
        return "us"
    for key, meta in _FOREIGN.items():
        if meta.get("session_id") == sid:
            return key
    return None

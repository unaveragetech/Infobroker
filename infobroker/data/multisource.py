"""Multi-source quotes: Yahoo primary, Finnhub / Alpha Vantage fallbacks (rate-limited)."""

from __future__ import annotations

import threading
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from infobroker.config import get_settings
from infobroker.data.highlights import fetch_ticker_snapshot
from infobroker.data.providers import (
    AlphaVantageProvider,
    FinnhubProvider,
    MarketDataError,
)

_UA = "Mozilla/5.0 (compatible; Infobroker/0.8; +local)"


class _MinuteBudget:
    """Simple rolling 60s call budget (thread-safe)."""

    def __init__(self, max_per_minute: int):
        self.max_per_minute = max(1, int(max_per_minute))
        self._times: deque[float] = deque()
        self._lock = threading.Lock()

    def try_acquire(self) -> bool:
        now = time.time()
        with self._lock:
            while self._times and now - self._times[0] > 60.0:
                self._times.popleft()
            if len(self._times) >= self.max_per_minute:
                return False
            self._times.append(now)
            return True

    def used(self) -> int:
        now = time.time()
        with self._lock:
            while self._times and now - self._times[0] > 60.0:
                self._times.popleft()
            return len(self._times)


# Finnhub free ~60/min — leave headroom for live + quote APIs
_FINNHUB_BUDGET = _MinuteBudget(40)
# Alpha Vantage free ~5/min — emergency fallback only
_AV_BUDGET = _MinuteBudget(4)

_profile_cache: dict[str, tuple[float, dict[str, Any]]] = {}
_PROFILE_TTL = 6 * 3600


def provider_status() -> dict[str, Any]:
    """Which data/broker keys are configured (booleans only — no secret values)."""
    s = get_settings()
    return {
        "yahoo": True,
        "finnhub": bool(s.finnhub_key),
        "alphavantage": bool(s.alphavantage_key),
        "public": bool(s.public_secret),
        "finnhub_budget_used": _FINNHUB_BUDGET.used(),
        "alphavantage_budget_used": _AV_BUDGET.used(),
    }


def _snap_from_quote(symbol: str, q: dict[str, Any], source: str) -> dict[str, Any]:
    price = float(q.get("Price") or q.get("price") or 0)
    prev = float(q.get("Previous Close") or q.get("previous_close") or 0) or price
    high = float(q.get("Daily High") or q.get("high") or price)
    low = float(q.get("Daily Low") or q.get("low") or price)
    vol_raw = q.get("Volume")
    try:
        volume = float(vol_raw) if vol_raw not in (None, "N/A", "") else 0.0
    except (TypeError, ValueError):
        volume = 0.0
    if q.get("change_pct_day") is not None:
        day_chg = float(q["change_pct_day"])
    else:
        day_chg = ((price / prev) - 1.0) * 100 if prev else 0.0
    return {
        "symbol": symbol.upper(),
        "name": q.get("name") or symbol.upper(),
        "price": round(price, 4),
        "change_abs_day": round(price - prev, 4),
        "change_pct_day": round(day_chg, 2),
        "change_pct_week": q.get("change_pct_week"),
        "volume": volume,
        "rel_volume": None,
        "high": round(high, 4),
        "low": round(low, 4),
        "sparkline": [],
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": source,
    }


def _finnhub() -> Optional[FinnhubProvider]:
    key = get_settings().finnhub_key
    if not key:
        return None
    try:
        return FinnhubProvider(key)
    except MarketDataError:
        return None


def _alphavantage() -> Optional[AlphaVantageProvider]:
    key = get_settings().alphavantage_key
    if not key:
        return None
    try:
        return AlphaVantageProvider(key)
    except MarketDataError:
        return None


def fetch_finnhub_snapshot(symbol: str) -> Optional[dict[str, Any]]:
    if not _FINNHUB_BUDGET.try_acquire():
        return None
    fh = _finnhub()
    if not fh:
        return None
    try:
        q = fh.get_quote(symbol)
        snap = _snap_from_quote(symbol, q, "finnhub")
        # Finnhub quote includes dp (percent change) sometimes more accurate intraday
        return snap
    except Exception:
        return None


def fetch_alphavantage_snapshot(symbol: str) -> Optional[dict[str, Any]]:
    if not _AV_BUDGET.try_acquire():
        return None
    av = _alphavantage()
    if not av:
        return None
    try:
        q = av.get_quote(symbol)
        return _snap_from_quote(symbol, q, "alphavantage")
    except Exception:
        return None


def fetch_snapshot_multisource(
    symbol: str,
    *,
    allow_finnhub: bool = True,
    allow_alphavantage: bool = False,
) -> Optional[dict[str, Any]]:
    """
    Yahoo chart first; Finnhub on miss (budgeted); Alpha Vantage only when explicitly allowed
    (single-symbol / live enrich — not full universe batches).
    """
    sym = (symbol or "").strip().upper()
    if not sym:
        return None

    yahoo = fetch_ticker_snapshot(sym)
    if yahoo:
        yahoo["source"] = yahoo.get("source") or "yahoo"
        return yahoo

    if allow_finnhub:
        fh = fetch_finnhub_snapshot(sym)
        if fh:
            return fh

    if allow_alphavantage:
        av = fetch_alphavantage_snapshot(sym)
        if av:
            return av
    return None


def cross_check_snapshot(
    symbol: str,
    primary: dict[str, Any],
    *,
    max_pct_drift: float = 0.75,
) -> dict[str, Any]:
    """
    Compare Yahoo/primary vs Finnhub. If Finnhub differs meaningfully, prefer Finnhub
    for live prices and annotate agreement.
    """
    out = dict(primary)
    out.setdefault("source", "yahoo")
    out["sources_checked"] = [out["source"]]
    out["cross_check"] = "skipped"
    fh = fetch_finnhub_snapshot(symbol)
    if not fh:
        return out
    out["sources_checked"].append("finnhub")
    p = float(primary.get("price") or 0)
    f = float(fh.get("price") or 0)
    if not p or not f:
        return out
    drift = abs(f - p) / p * 100
    out["cross_check_drift_pct"] = round(drift, 3)
    if drift >= max_pct_drift:
        # Prefer Finnhub for intraday live when Yahoo chart lags
        merged = dict(fh)
        merged["name"] = primary.get("name") or fh.get("name")
        merged["change_pct_week"] = primary.get("change_pct_week")
        merged["sparkline"] = primary.get("sparkline") or []
        merged["rel_volume"] = primary.get("rel_volume")
        merged["sources_checked"] = out["sources_checked"]
        merged["cross_check"] = "finnhub_preferred"
        merged["yahoo_price"] = p
        return merged
    out["cross_check"] = "agree"
    return out


def finnhub_company_profile(symbol: str) -> Optional[dict[str, Any]]:
    fh = _finnhub()
    if not fh:
        return None
    sym = symbol.upper()
    now = time.time()
    cached = _profile_cache.get(sym)
    if cached and now - cached[0] < _PROFILE_TTL:
        return cached[1]
    if not _FINNHUB_BUDGET.try_acquire():
        return cached[1] if cached else None
    try:
        data = fh._get("/stock/profile2", symbol=sym)  # noqa: SLF001 — shared helper
        if not data:
            return None
        profile = {
            "symbol": sym,
            "name": data.get("name") or sym,
            "exchange": data.get("exchange"),
            "industry": data.get("finnhubIndustry") or data.get("industry"),
            "market_cap": data.get("marketCapitalization"),
            "logo": data.get("logo"),
            "weburl": data.get("weburl"),
            "source": "finnhub",
        }
        _profile_cache[sym] = (now, profile)
        return profile
    except Exception:
        return cached[1] if cached else None


def finnhub_market_news(limit: int = 12) -> list[dict[str, Any]]:
    fh = _finnhub()
    if not fh or not _FINNHUB_BUDGET.try_acquire():
        return []
    try:
        rows = fh._get("/news", category="general")  # noqa: SLF001
        if not isinstance(rows, list):
            return []
        out = []
        for row in rows[: max(1, min(int(limit), 30))]:
            out.append(
                {
                    "headline": row.get("headline") or "",
                    "source": row.get("source") or "",
                    "url": row.get("url") or "",
                    "datetime": row.get("datetime"),
                    "related": row.get("related") or "",
                    "provider": "finnhub",
                }
            )
        return out
    except Exception:
        return []


def finnhub_market_status() -> Optional[dict[str, Any]]:
    key = get_settings().finnhub_key
    if not key or not _FINNHUB_BUDGET.try_acquire():
        return None
    try:
        resp = requests.get(
            "https://finnhub.io/api/v1/stock/market-status",
            params={"exchange": "US", "token": key},
            headers={"User-Agent": _UA},
            timeout=15,
        )
        if resp.status_code >= 400:
            return None
        data = resp.json()
        return {
            "exchange": data.get("exchange") or "US",
            "is_open": bool(data.get("isOpen")),
            "session": data.get("session"),
            "timezone": data.get("timezone"),
            "provider": "finnhub",
        }
    except Exception:
        return None


def _sort_live_items(items: list[dict[str, Any]], sort: str) -> list[dict[str, Any]]:
    key = (sort or "abs_change").strip().lower()
    if key in {"change_desc", "change_pct", "gainers"}:
        return sorted(items, key=lambda r: r.get("change_pct_day") if r.get("change_pct_day") is not None else -9999, reverse=True)
    if key in {"change_asc", "losers"}:
        return sorted(items, key=lambda r: r.get("change_pct_day") if r.get("change_pct_day") is not None else 9999)
    if key in {"volume", "vol"}:
        return sorted(items, key=lambda r: r.get("volume") or 0, reverse=True)
    if key in {"rel_volume", "rvol"}:
        return sorted(items, key=lambda r: r.get("rel_volume") or 0, reverse=True)
    if key == "price":
        return sorted(items, key=lambda r: r.get("price") or 0, reverse=True)
    if key == "symbol":
        return sorted(items, key=lambda r: r.get("symbol") or "")
    if key in {"week", "change_week"}:
        return sorted(items, key=lambda r: r.get("change_pct_week") if r.get("change_pct_week") is not None else -9999, reverse=True)
    # default: absolute day move
    return sorted(items, key=lambda r: abs(r.get("change_pct_day") or 0), reverse=True)


def build_live_board(
    mode: str = "universe",
    asset_class: str = "",
    limit: int = 0,
    enrich: bool = True,
    sort: str = "abs_change",
    exchange: str = "",
) -> dict[str, Any]:
    """Live heat board backed by universe cache + optional Finnhub cross-check / news.

    limit=0 means return every quoted symbol (full universe board).
    """
    from infobroker.universe.engine import movers, quoted_rows
    from infobroker.universe.store import load_universe, symbol_count

    mode_n = (mode or "universe").strip().lower()
    ac = (asset_class or "").strip().lower()
    exch = (exchange or "").strip().lower()
    sort_n = (sort or "abs_change").strip().lower()
    limit_n = int(limit)
    # 0 = all quoted; otherwise clamp for focused modes
    if limit_n < 0:
        limit_n = 0
    if limit_n > 0:
        limit_n = min(limit_n, 20000)
    status = provider_status()

    items: list[dict[str, Any]] = []
    if mode_n in {"gainers", "losers", "volume"}:
        mv_limit = limit_n if limit_n > 0 else 120
        mv = movers(limit=min(200, mv_limit))
        if mode_n == "gainers":
            items = list((mv.get("stocks_of_day") or {}).get("gainers") or [])
            if sort_n == "abs_change":
                sort_n = "change_desc"
        elif mode_n == "losers":
            items = list((mv.get("stocks_of_day") or {}).get("losers") or [])
            if sort_n == "abs_change":
                sort_n = "change_asc"
        else:
            items = list(mv.get("volume_leaders") or [])
            if sort_n == "abs_change":
                sort_n = "volume"
    else:
        # heat / universe — full quoted universe by default
        items = quoted_rows()
        if mode_n == "heat" and limit_n == 0:
            # "Top movers" convenience slice when no explicit limit
            limit_n = 180

    if ac == "etf":
        items = [r for r in items if r.get("etf") or r.get("asset_class") == "etf"]
    elif ac == "stock":
        items = [
            r
            for r in items
            if not r.get("etf") and (r.get("asset_class") or "stock") in {"stock", "adr", "other"}
        ]

    if exch:
        items = [r for r in items if exch in (r.get("exchange") or "").lower()]

    items = [r for r in items if r.get("price") is not None]
    items = _sort_live_items(items, sort_n)
    if limit_n > 0:
        items = items[:limit_n]

    # Exchange volume rollup for "markets" view
    by_exchange: dict[str, dict[str, Any]] = {}
    for r in items:
        ex = r.get("exchange") or "Unknown"
        bucket = by_exchange.setdefault(
            ex,
            {"exchange": ex, "count": 0, "volume": 0.0, "avg_change_pct": 0.0, "_chg_sum": 0.0},
        )
        bucket["count"] += 1
        bucket["volume"] += float(r.get("volume") or 0)
        bucket["_chg_sum"] += float(r.get("change_pct_day") or 0)
    markets = []
    for bucket in by_exchange.values():
        n = max(1, bucket["count"])
        markets.append(
            {
                "exchange": bucket["exchange"],
                "count": bucket["count"],
                "volume": bucket["volume"],
                "avg_change_pct": round(bucket["_chg_sum"] / n, 2),
            }
        )
    markets.sort(key=lambda m: m["volume"], reverse=True)

    cross_checked = 0
    if enrich and status.get("finnhub") and items:
        # Cross-check the most visible tiles so Live stays honest vs Yahoo lag
        sample_n = min(12, len(items))
        for i in range(sample_n):
            row = items[i]
            sym = row["symbol"]
            try:
                checked = cross_check_snapshot(sym, row)
                items[i] = {**row, **{k: checked[k] for k in checked if k != "sparkline" or checked.get("sparkline")}}
                if checked.get("sparkline"):
                    items[i]["sparkline"] = checked["sparkline"]
                if checked.get("cross_check") == "finnhub_preferred":
                    cross_checked += 1
                # Fill company name from Finnhub profile when listing name is thin
                if len(items[i].get("name") or "") < 3 or items[i].get("name") == sym:
                    prof = finnhub_company_profile(sym)
                    if prof and prof.get("name"):
                        items[i]["name"] = prof["name"]
                        items[i]["industry"] = prof.get("industry")
                        items[i]["market_cap"] = prof.get("market_cap")
            except Exception:
                continue

    news = finnhub_market_news(10) if status.get("finnhub") else []
    mkt = finnhub_market_status() if status.get("finnhub") else None
    data = load_universe()
    total = symbol_count(data)
    quoted = sum(1 for v in (data.get("symbols") or {}).values() if (v.get("quote") or {}).get("price") is not None)
    up_n = sum(1 for r in items if (r.get("change_pct_day") or 0) > 0.15)
    down_n = sum(1 for r in items if (r.get("change_pct_day") or 0) < -0.15)

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "mode": mode_n,
        "sort": sort_n,
        "exchange": exchange or None,
        "items": items,
        "count": len(items),
        "markets": markets,
        "breadth": {"up": up_n, "down": down_n, "flat": max(0, len(items) - up_n - down_n)},
        "coverage": {
            "quoted": quoted,
            "total": total,
            "pct": round((quoted / total) * 100, 1) if total else 0.0,
            "unquoted": max(0, total - quoted),
        },
        "quoted_universe": quoted,
        "providers": status,
        "cross_checked": cross_checked,
        "market_status": mkt,
        "news": news,
        "listings_as_of": data.get("listings_as_of"),
        "quotes_as_of": data.get("quotes_as_of"),
    }


__all__ = [
    "build_live_board",
    "cross_check_snapshot",
    "fetch_snapshot_multisource",
    "finnhub_company_profile",
    "finnhub_market_news",
    "finnhub_market_status",
    "provider_status",
]

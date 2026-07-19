"""Throttled live ticks + intraday bars via Yahoo chart (no crumb)."""

from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from typing import Any, Optional

import requests

from infobroker.markets.sessions import market_clocks

_UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
}

# Per-symbol tick cache — keeps many clients from hammering Yahoo
_cache_lock = threading.Lock()
_tick_cache: dict[str, dict[str, Any]] = {}
_MIN_TICK_SEC_OPEN = 0.85
_MIN_TICK_SEC_CLOSED = 12.0


def _norm(symbol: str) -> str:
    return (symbol or "").strip().upper().replace(".", "-")


def _chart_json(symbol: str, range_: str, interval: str) -> Optional[dict[str, Any]]:
    sym = _norm(symbol)
    try:
        resp = requests.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
            params={"range": range_, "interval": interval},
            headers=_UA,
            timeout=12,
        )
        if resp.status_code >= 400:
            resp = requests.get(
                f"https://query2.finance.yahoo.com/v8/finance/chart/{sym}",
                params={"range": range_, "interval": interval},
                headers=_UA,
                timeout=12,
            )
        if resp.status_code >= 400:
            return None
        result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
        return result
    except Exception:
        return None


def fetch_live_tick(symbol: str, force: bool = False) -> dict[str, Any]:
    """Lightweight last price tick. Cached ~1s when US open, slower when closed."""
    sym = _norm(symbol)
    clocks = market_clocks()
    us_open = bool(clocks.get("us_open"))
    min_age = _MIN_TICK_SEC_OPEN if us_open else _MIN_TICK_SEC_CLOSED

    with _cache_lock:
        cached = _tick_cache.get(sym)
        if (
            not force
            and cached
            and (time.monotonic() - float(cached.get("_mono") or 0)) < min_age
        ):
            out = {k: v for k, v in cached.items() if not k.startswith("_")}
            out["cached"] = True
            return out

    result = _chart_json(sym, range_="1d", interval="1m")
    if not result:
        return {
            "symbol": sym,
            "ok": False,
            "error": "no tick",
            "us_open": us_open,
            "as_of": datetime.now(timezone.utc).isoformat(),
        }

    meta = result.get("meta") or {}
    ts = result.get("timestamp") or []
    quote = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    closes = quote.get("close") or []
    volumes = quote.get("volume") or []
    last_close = None
    last_vol = None
    last_ts = None
    for i in range(len(closes) - 1, -1, -1):
        if closes[i] is not None:
            last_close = float(closes[i])
            last_vol = float(volumes[i] or 0) if i < len(volumes) else None
            last_ts = int(ts[i]) if i < len(ts) else None
            break

    price = meta.get("regularMarketPrice")
    if price is None:
        price = last_close
    prev = meta.get("chartPreviousClose") or meta.get("previousClose")
    chg = None
    chg_pct = None
    if price is not None and prev:
        try:
            price_f = float(price)
            prev_f = float(prev)
            chg = price_f - prev_f
            chg_pct = ((price_f / prev_f) - 1.0) * 100 if prev_f else None
        except (TypeError, ValueError):
            pass

    tick = {
        "ok": True,
        "symbol": sym,
        "price": round(float(price), 4) if price is not None else None,
        "change_abs": round(chg, 4) if chg is not None else None,
        "change_pct": round(chg_pct, 2) if chg_pct is not None else None,
        "prev_close": float(prev) if prev is not None else None,
        "day_high": meta.get("regularMarketDayHigh"),
        "day_low": meta.get("regularMarketDayLow"),
        "volume": last_vol,
        "bar_time": last_ts,
        "currency": meta.get("currency") or "USD",
        "exchange": meta.get("exchangeName") or meta.get("fullExchangeName"),
        "market_state": meta.get("marketState"),  # REGULAR / PRE / POST / CLOSED
        "us_open": us_open,
        "source": "yahoo_chart",
        "as_of": datetime.now(timezone.utc).isoformat(),
        "cached": False,
        "poll_sec": min_age,
    }
    with _cache_lock:
        _tick_cache[sym] = {**tick, "_mono": time.monotonic()}
    return tick


def fetch_intraday_bars(
    symbol: str,
    interval: str = "1m",
    range_: str = "1d",
) -> dict[str, Any]:
    """Intraday OHLCV for live charting (1m / 5m)."""
    sym = _norm(symbol)
    interval_n = interval if interval in {"1m", "2m", "5m", "15m", "30m", "60m"} else "1m"
    range_n = range_ if range_ in {"1d", "5d", "1mo"} else "1d"
    result = _chart_json(sym, range_=range_n, interval=interval_n)
    clocks = market_clocks()
    if not result:
        return {
            "symbol": sym,
            "interval": interval_n,
            "range": range_n,
            "bars": [],
            "us_open": clocks.get("us_open"),
            "error": "no intraday data",
        }

    meta = result.get("meta") or {}
    ts = result.get("timestamp") or []
    q = ((result.get("indicators") or {}).get("quote") or [{}])[0]
    bars: list[dict[str, Any]] = []
    for i, t in enumerate(ts):
        o, h, l, c = (
            (q.get("open") or [None])[i],
            (q.get("high") or [None])[i],
            (q.get("low") or [None])[i],
            (q.get("close") or [None])[i],
        )
        if c is None:
            continue
        bars.append(
            {
                "t": datetime.fromtimestamp(int(t), tz=timezone.utc).isoformat(),
                "o": float(o if o is not None else c),
                "h": float(h if h is not None else c),
                "l": float(l if l is not None else c),
                "c": float(c),
                "v": float((q.get("volume") or [0])[i] or 0),
            }
        )

    return {
        "symbol": sym,
        "interval": interval_n,
        "range": range_n,
        "bars": bars,
        "last": bars[-1]["c"] if bars else meta.get("regularMarketPrice"),
        "market_state": meta.get("marketState"),
        "us_open": clocks.get("us_open"),
        "as_of": datetime.now(timezone.utc).isoformat(),
        "source": "yahoo_chart",
    }

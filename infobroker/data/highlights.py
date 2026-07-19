"""Market highlights: movers, stocks of the day/week, notable tracked names."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

import pandas as pd
import yfinance as yf

from infobroker.watchlist import list_symbols

# Liquid US names used when scanning "day/week" notables without a paid screener
UNIVERSE = [
    "AAPL",
    "MSFT",
    "NVDA",
    "GOOGL",
    "AMZN",
    "META",
    "TSLA",
    "AMD",
    "NFLX",
    "AVGO",
    "CRM",
    "COST",
    "JPM",
    "XOM",
    "UNH",
    "LLY",
    "V",
    "MA",
    "BAC",
    "WMT",
    "DIS",
    "INTC",
    "BA",
    "PYPL",
    "UBER",
    "COIN",
    "PLTR",
    "SMCI",
    "MU",
    "QCOM",
    "SPY",
    "QQQ",
    "IWM",
    "DIA",
]


def _safe_float(v: Any) -> Optional[float]:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def _history_via_chart(symbol: str, days: int = 15) -> Optional[pd.DataFrame]:
    """Yahoo chart API — avoids crumb/cookie failures from yfinance."""
    try:
        import requests

        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol.upper()}"
        resp = requests.get(
            url,
            params={"range": f"{max(days, 5)}d", "interval": "1d"},
            headers={"User-Agent": "Mozilla/5.0 (compatible; Infobroker/0.5)"},
            timeout=20,
        )
        if resp.status_code >= 400:
            return None
        result = ((resp.json().get("chart") or {}).get("result") or [None])[0]
        if not result:
            return None
        ts = result.get("timestamp") or []
        q = ((result.get("indicators") or {}).get("quote") or [{}])[0]
        rows = []
        for i, t in enumerate(ts):
            c = (q.get("close") or [None])[i]
            if c is None:
                continue
            rows.append(
                {
                    "Date": pd.Timestamp(t, unit="s"),
                    "Open": float((q.get("open") or [c])[i] or c),
                    "High": float((q.get("high") or [c])[i] or c),
                    "Low": float((q.get("low") or [c])[i] or c),
                    "Close": float(c),
                    "Volume": float((q.get("volume") or [0])[i] or 0),
                }
            )
        if not rows:
            return None
        return pd.DataFrame(rows).set_index("Date").sort_index()
    except Exception:
        return None


_yahoo_session: dict[str, Any] = {"cookie": None, "crumb": None, "fetched_at": 0.0}


def _yahoo_auth(session: Any) -> tuple[Optional[Any], Optional[str]]:
    """Obtain Yahoo cookie + crumb for authenticated quote endpoints."""
    import time

    ua = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    now = time.time()
    if (
        _yahoo_session.get("cookie")
        and _yahoo_session.get("crumb")
        and now - float(_yahoo_session.get("fetched_at") or 0) < 6 * 3600
    ):
        return _yahoo_session["cookie"], _yahoo_session["crumb"]

    try:
        session.get("https://fc.yahoo.com", headers=ua, timeout=15)
    except Exception:
        pass
    try:
        crumb_resp = session.get(
            "https://query2.finance.yahoo.com/v1/test/getcrumb",
            headers=ua,
            timeout=15,
        )
        crumb = (crumb_resp.text or "").strip()
        if crumb_resp.status_code >= 400 or not crumb or "<" in crumb:
            return None, None
        _yahoo_session["cookie"] = session.cookies
        _yahoo_session["crumb"] = crumb
        _yahoo_session["fetched_at"] = now
        return session.cookies, crumb
    except Exception:
        return None, None


def fetch_yahoo_quotes_bulk(symbols: list[str], chunk_size: int = 80) -> dict[str, dict[str, Any]]:
    """Fast multi-symbol quotes via Yahoo quote API (no sparklines).

    Returns {SYMBOL: snapshot_dict}. Failures are omitted — caller may fall back
    to per-symbol chart snapshots.
    """
    import requests

    seen: set[str] = set()
    ordered: list[str] = []
    for s in symbols:
        sym = (s or "").strip().upper().replace(".", "-")
        if sym and sym not in seen:
            seen.add(sym)
            ordered.append(sym)
    if not ordered:
        return {}

    out: dict[str, dict[str, Any]] = {}
    ua = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        )
    }
    sess = requests.Session()
    cookies, crumb = _yahoo_auth(sess)
    chunk_size = max(10, min(int(chunk_size), 100))
    for i in range(0, len(ordered), chunk_size):
        chunk = ordered[i : i + chunk_size]
        try:
            params: dict[str, Any] = {"symbols": ",".join(chunk)}
            if crumb:
                params["crumb"] = crumb
            resp = sess.get(
                "https://query1.finance.yahoo.com/v7/finance/quote",
                params=params,
                headers=ua,
                cookies=cookies,
                timeout=25,
            )
            if resp.status_code in {401, 403}:
                # Refresh crumb once and retry
                _yahoo_session["fetched_at"] = 0
                cookies, crumb = _yahoo_auth(sess)
                if crumb:
                    params["crumb"] = crumb
                resp = sess.get(
                    "https://query2.finance.yahoo.com/v7/finance/quote",
                    params=params,
                    headers=ua,
                    cookies=cookies,
                    timeout=25,
                )
            elif resp.status_code >= 400:
                resp = sess.get(
                    "https://query2.finance.yahoo.com/v7/finance/quote",
                    params=params,
                    headers=ua,
                    cookies=cookies,
                    timeout=25,
                )
            if resp.status_code >= 400:
                continue
            results = ((resp.json().get("quoteResponse") or {}).get("result")) or []
            for q in results:
                sym = (q.get("symbol") or "").upper().replace(".", "-")
                if not sym:
                    continue
                price = _safe_float(q.get("regularMarketPrice"))
                if price is None:
                    continue
                prev = _safe_float(q.get("regularMarketPreviousClose"))
                chg_abs = _safe_float(q.get("regularMarketChange"))
                chg_pct = _safe_float(q.get("regularMarketChangePercent"))
                if chg_pct is None and prev and prev > 0 and price is not None:
                    chg_pct = ((price / prev) - 1.0) * 100
                if chg_abs is None and prev is not None:
                    chg_abs = price - prev
                vol = _safe_float(q.get("regularMarketVolume")) or 0.0
                avg_vol = _safe_float(q.get("averageDailyVolume3Month") or q.get("averageDailyVolume10Day"))
                rvol = (vol / avg_vol) if avg_vol else None
                name = q.get("shortName") or q.get("longName") or sym
                bid = _safe_float(q.get("bid"))
                ask = _safe_float(q.get("ask"))
                if bid is None:
                    bid = _safe_float(q.get("bidPrice"))
                if ask is None:
                    ask = _safe_float(q.get("askPrice"))
                # Spread fallback when exchange doesn't publish bid/ask
                if price is not None:
                    if bid is None:
                        bid = round(price * 0.9995, 4)
                    if ask is None:
                        ask = round(price * 1.0005, 4)
                out[sym] = {
                    "symbol": sym,
                    "name": name,
                    "price": round(price, 4),
                    "bid": round(bid, 4) if bid is not None else None,
                    "ask": round(ask, 4) if ask is not None else None,
                    "change_abs_day": round(chg_abs, 4) if chg_abs is not None else None,
                    "change_pct_day": round(chg_pct, 2) if chg_pct is not None else None,
                    "change_pct_week": None,
                    "volume": vol,
                    "rel_volume": round(rvol, 2) if rvol is not None else None,
                    "high": _safe_float(q.get("regularMarketDayHigh")),
                    "low": _safe_float(q.get("regularMarketDayLow")),
                    "sparkline": [],
                    "as_of": datetime.now(timezone.utc).isoformat(),
                    "source": "yahoo_bulk",
                }
        except Exception:
            continue
    return out


def fetch_ticker_snapshot(symbol: str) -> Optional[dict[str, Any]]:
    """One-symbol snapshot via Yahoo chart (primary), yfinance fallback."""
    try:
        hist = _history_via_chart(symbol, days=15)
        if hist is None or hist.empty:
            t = yf.Ticker(symbol)
            hist = t.history(period="10d", auto_adjust=True)
        if hist is None or hist.empty:
            return None
        close = hist["Close"].astype(float)
        last = float(close.iloc[-1])
        prev = float(close.iloc[-2]) if len(close) > 1 else last
        day_chg = ((last / prev) - 1.0) * 100 if prev else 0.0

        week_ref = close.iloc[0]
        # Prefer ~5 trading days back when available
        if len(close) >= 6:
            week_ref = float(close.iloc[-6])
        week_chg = ((last / week_ref) - 1.0) * 100 if week_ref else 0.0

        volume = float(hist["Volume"].iloc[-1]) if "Volume" in hist else 0.0
        avg_vol = float(hist["Volume"].tail(5).mean()) if "Volume" in hist else 0.0
        rvol = (volume / avg_vol) if avg_vol else None

        name = symbol
        spark = [round(float(x), 4) for x in close.tolist()]
        return {
            "symbol": symbol,
            "name": name,
            "price": round(last, 4),
            "change_abs_day": round(last - prev, 4),
            "change_pct_day": round(day_chg, 2),
            "change_pct_week": round(week_chg, 2),
            "volume": volume,
            "rel_volume": round(rvol, 2) if rvol is not None else None,
            "high": round(float(hist["High"].iloc[-1]), 4),
            "low": round(float(hist["Low"].iloc[-1]), 4),
            "sparkline": spark,
            "as_of": datetime.now(timezone.utc).isoformat(),
            "source": "yahoo",
        }
    except Exception:
        return None


def _batch_snapshots(symbols: list[str], max_workers: int = 14) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    # Dedupe preserve order
    seen: set[str] = set()
    ordered: list[str] = []
    for s in symbols:
        if s and s not in seen:
            seen.add(s)
            ordered.append(s)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(fetch_ticker_snapshot, s): s for s in ordered}
        for fut in as_completed(futures):
            row = fut.result()
            if row:
                out.append(row)
    return out


def get_tracked_quotes(symbols: Optional[list[str]] = None) -> list[dict[str, Any]]:
    syms = symbols or list_symbols()
    rows = _batch_snapshots(syms)
    # Keep watchlist order
    rank = {s: i for i, s in enumerate(syms)}
    rows.sort(key=lambda r: rank.get(r["symbol"], 999))
    return rows


def get_market_highlights() -> dict[str, Any]:
    """Stocks of the day/week from the market universe cache + notable tracked names."""
    tracked = list_symbols()
    index_syms = ["SPY", "QQQ", "IWM", "DIA"]
    need_live = list(dict.fromkeys(tracked + index_syms))
    live_rows = _batch_snapshots(need_live)
    by_sym = {r["symbol"]: r for r in live_rows}

    # Broad movers: prefer universe quote cache (thousands of names as it fills)
    mv_day_g: list[dict[str, Any]] = []
    mv_day_l: list[dict[str, Any]] = []
    mv_week_g: list[dict[str, Any]] = []
    mv_week_l: list[dict[str, Any]] = []
    volume_leaders: list[dict[str, Any]] = []
    universe_quoted = 0
    try:
        from infobroker.universe import movers as universe_movers

        mv = universe_movers(limit=8)
        universe_quoted = int(mv.get("quoted") or 0)
        if universe_quoted >= 25:
            mv_day_g = (mv.get("stocks_of_day") or {}).get("gainers") or []
            mv_day_l = (mv.get("stocks_of_day") or {}).get("losers") or []
            mv_week_g = (mv.get("stocks_of_week") or {}).get("gainers") or []
            mv_week_l = (mv.get("stocks_of_week") or {}).get("losers") or []
            volume_leaders = (mv.get("volume_leaders") or [])[:5]
    except Exception:
        universe_quoted = 0

    # Fallback seed universe until the engine has enough quotes
    if universe_quoted < 25:
        seed_rows = _batch_snapshots(list(dict.fromkeys(tracked + UNIVERSE)))
        by_sym.update({r["symbol"]: r for r in seed_rows})
        equity_rows = [r for r in seed_rows if r["symbol"] not in set(index_syms)]
        mv_day_g = sorted(equity_rows, key=lambda r: r.get("change_pct_day") or -999, reverse=True)[:5]
        mv_day_l = sorted(equity_rows, key=lambda r: r.get("change_pct_day") or 999)[:5]
        mv_week_g = sorted(equity_rows, key=lambda r: r.get("change_pct_week") or -999, reverse=True)[:5]
        mv_week_l = sorted(equity_rows, key=lambda r: r.get("change_pct_week") or 999)[:5]
        volume_leaders = sorted(
            [r for r in equity_rows if r.get("rel_volume")],
            key=lambda r: r.get("rel_volume") or 0,
            reverse=True,
        )[:5]

    if not by_sym and not mv_day_g:
        return {
            "as_of": datetime.utcnow().isoformat() + "Z",
            "indices": [],
            "tracked_notable": [],
            "stocks_of_day": {"gainers": [], "losers": []},
            "stocks_of_week": {"gainers": [], "losers": []},
            "volume_leaders": [],
            "universe_quoted": universe_quoted,
            "error": "No market data returned — check network / Yahoo",
        }

    indices = [by_sym[s] for s in index_syms if s in by_sym]
    tracked_rows = [by_sym[s] for s in tracked if s in by_sym]
    tracked_notable = sorted(
        tracked_rows,
        key=lambda r: (
            abs(r.get("change_pct_day") or 0),
            r.get("rel_volume") or 0,
        ),
        reverse=True,
    )[:8]

    return {
        "as_of": datetime.utcnow().isoformat() + "Z",
        "indices": indices,
        "tracked_notable": tracked_notable,
        "stocks_of_day": {
            "gainers": mv_day_g[:5],
            "losers": mv_day_l[:5],
        },
        "stocks_of_week": {
            "gainers": mv_week_g[:5],
            "losers": mv_week_l[:5],
        },
        "volume_leaders": volume_leaders[:5],
        "universe_quoted": universe_quoted,
    }


def sparkline_closes(symbol: str, days: int = 30) -> list[float]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=days + 10)
    df = yf.download(
        symbol,
        start=start.isoformat(),
        end=end.isoformat(),
        progress=False,
        auto_adjust=True,
    )
    if df is None or df.empty:
        return []
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    closes = df["Close"].dropna().astype(float).tolist()
    return [round(c, 4) for c in closes[-days:]]

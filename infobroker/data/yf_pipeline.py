"""
Canonical market-data pipeline:

  yfinance  →  Pandas DataFrame  →  TA-Lib indicators
"""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import yfinance as yf

from infobroker.data.indicators import enrich_ohlcv, latest_snapshot


def download_history(
    symbol: str,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: Optional[str] = None,
    interval: str = "1d",
    auto_adjust: bool = True,
) -> pd.DataFrame:
    """
    Download OHLCV with yfinance into a clean Pandas DataFrame.

    Prefer `start`/`end` (YYYY-MM-DD) or a yfinance `period` (e.g. '6mo', '1y').
    """
    sym = symbol.upper().strip()
    kwargs: dict[str, Any] = {
        "interval": interval,
        "auto_adjust": auto_adjust,
        "progress": False,
        "threads": False,
    }
    if period:
        kwargs["period"] = period
    else:
        if not start or not end:
            raise ValueError("Provide start+end or period")
        kwargs["start"] = start
        kwargs["end"] = end

    df = yf.download(sym, **kwargs)
    if df is None or df.empty:
        # Fallback: Ticker.history
        t = yf.Ticker(sym)
        if period:
            df = t.history(period=period, interval=interval, auto_adjust=auto_adjust)
        else:
            df = t.history(start=start, end=end, interval=interval, auto_adjust=auto_adjust)

    if df is None or df.empty:
        raise ValueError(f"yfinance returned no data for {sym}")

    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    rename = {c: str(c).title() for c in df.columns}
    df = df.rename(columns=rename)
    needed = ["Open", "High", "Low", "Close"]
    for col in needed:
        if col not in df.columns:
            raise ValueError(f"yfinance frame missing {col} for {sym}")
    if "Volume" not in df.columns:
        df["Volume"] = 0.0

    df = df[needed + ["Volume"]].astype(float).dropna(how="any")
    df.index = pd.to_datetime(df.index)
    df.index.name = "Date"
    return df.sort_index()


def download_quote(symbol: str) -> dict[str, Any]:
    """Real-time-ish quote via yfinance + Pandas last bar."""
    sym = symbol.upper().strip()
    t = yf.Ticker(sym)
    hist = t.history(period="5d", interval="1d", auto_adjust=True)
    if hist is None or hist.empty:
        raise ValueError(f"No yfinance quote history for {sym}")
    if isinstance(hist.columns, pd.MultiIndex):
        hist.columns = hist.columns.get_level_values(0)
    last = hist.iloc[-1]
    info: dict[str, Any] = {}
    try:
        info = t.fast_info.__dict__ if hasattr(t, "fast_info") else {}
    except Exception:
        info = {}
    price = float(last["Close"])
    return {
        "symbol": sym,
        "Price": price,
        "Daily High": float(last["High"]),
        "Daily Low": float(last["Low"]),
        "Volume": float(last.get("Volume") or 0),
        "Previous Close": float(hist["Close"].iloc[-2]) if len(hist) > 1 else price,
        "Market Cap": info.get("market_cap", "N/A"),
        "provider": "yfinance",
        "engine": "yfinance+pandas",
    }


def analyze_symbol(
    symbol: str,
    *,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "1y",
) -> dict[str, Any]:
    """
    Full analysis pack: yfinance download → Pandas → TA-Lib enrich.
    """
    if start and end:
        df = download_history(symbol, start=start, end=end)
    else:
        df = download_history(symbol, period=period)
    enriched = enrich_ohlcv(df)
    snap = latest_snapshot(enriched)
    # Tail for API consumers (avoid huge payloads)
    tail = enriched.tail(120).copy()
    records = []
    for ts, row in tail.iterrows():
        records.append(
            {
                "t": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": float(row["Volume"]),
                "sma20": _num(row.get("SMA_20")),
                "sma50": _num(row.get("SMA_50")),
                "sma200": _num(row.get("SMA_200")),
                "rsi": _num(row.get("RSI_14")),
                "macd": _num(row.get("MACD")),
                "macd_signal": _num(row.get("MACD_signal")),
                "macd_hist": _num(row.get("MACD_hist")),
                "atr": _num(row.get("ATR_14")),
                "bb_upper": _num(row.get("BB_upper")),
                "bb_lower": _num(row.get("BB_lower")),
            }
        )
    return {
        "symbol": symbol.upper(),
        "rows": len(enriched),
        "start": str(enriched.index[0].date()) if len(enriched) else None,
        "end": str(enriched.index[-1].date()) if len(enriched) else None,
        "snapshot": snap,
        "bars": records,
        "stack": ["yfinance", "pandas", "TA-Lib"],
    }


def _num(v: Any) -> float | None:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return round(float(v), 4)
    except Exception:
        return None

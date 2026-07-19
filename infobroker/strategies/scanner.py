"""Scan watchlist for simple teaching-friendly signals."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd

from infobroker.data.indicators import calculate_macd, calculate_rsi, sma
from infobroker.data.market import fetch_ohlcv
from infobroker.watchlist import list_symbols


def _scan_one(symbol: str) -> Optional[dict[str, Any]]:
    end = datetime.utcnow().date()
    start = end - timedelta(days=220)
    try:
        df = fetch_ohlcv(symbol, start.isoformat(), end.isoformat())
    except Exception:
        return None
    if df is None or df.empty or "Close" not in df.columns:
        return None
    close = df["Close"].astype(float).dropna()
    if len(close) < 50:
        return None

    rsi = calculate_rsi(close, 14)
    macd = calculate_macd(close)
    ma50 = float(sma(close, 50).iloc[-1])
    ma200 = float(sma(close, 200).iloc[-1]) if len(close) >= 200 else None
    last = float(close.iloc[-1])
    prev = float(close.iloc[-2])
    day_chg = ((last / prev) - 1.0) * 100 if prev else 0.0

    signals: list[str] = []
    severity = 0  # higher = more notable

    if isinstance(rsi, (int, float)):
        if rsi <= 30:
            signals.append(f"RSI oversold ({rsi})")
            severity += 3
        elif rsi >= 70:
            signals.append(f"RSI overbought ({rsi})")
            severity += 3
        elif rsi <= 40:
            signals.append(f"RSI cooling ({rsi})")
            severity += 1

    if ma200 is not None:
        if last > ma50 > ma200:
            signals.append("Uptrend stack (price > MA50 > MA200)")
            severity += 2
        elif last < ma50 < ma200:
            signals.append("Downtrend stack (price < MA50 < MA200)")
            severity += 2
        if prev <= ma50 < last:
            signals.append("Reclaimed MA50")
            severity += 2
        if prev >= ma50 > last:
            signals.append("Lost MA50")
            severity += 2

    hist = macd.get("histogram", 0)
    if hist > 0 and macd.get("macd_line", 0) > macd.get("signal_line", 0):
        if abs(day_chg) > 1.5:
            signals.append("MACD bullish + active day")
            severity += 1
    if hist < 0 and macd.get("macd_line", 0) < macd.get("signal_line", 0):
        if abs(day_chg) > 1.5:
            signals.append("MACD bearish + active day")
            severity += 1

    if not signals:
        return None

    # Teaching tip tied to strongest signal
    tip = "Confirm with level + volume before acting."
    if any("oversold" in s.lower() for s in signals):
        tip = "Oversold is not a buy alone — wait for a higher low or reclaim of support."
    elif any("overbought" in s.lower() for s in signals):
        tip = "Overbought can stay hot in trends — tighten risk, don't short blindly."
    elif any("Downtrend" in s for s in signals):
        tip = "Against the stack, keep size small or stand aside."
    elif any("Uptrend" in s for s in signals):
        tip = "Trend-aligned pulls to MA50 are usually cleaner than chasing green candles."

    return {
        "symbol": symbol,
        "price": round(last, 4),
        "change_pct_day": round(day_chg, 2),
        "rsi": rsi if isinstance(rsi, (int, float)) else None,
        "ma50": round(ma50, 4),
        "ma200": round(ma200, 4) if ma200 is not None else None,
        "signals": signals,
        "severity": severity,
        "tip": tip,
    }


def scan_watchlist(symbols: Optional[list[str]] = None, max_workers: int = 6) -> dict[str, Any]:
    syms = symbols or list_symbols()
    rows: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {pool.submit(_scan_one, s): s for s in syms}
        for fut in as_completed(futures):
            row = fut.result()
            if row:
                rows.append(row)
    rows.sort(
        key=lambda r: (r["severity"], abs(r.get("change_pct_day") or 0)),
        reverse=True,
    )
    return {
        "as_of": datetime.utcnow().isoformat() + "Z",
        "scanned": len(syms),
        "hits": len(rows),
        "items": rows[:20],
    }

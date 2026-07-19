"""Multi-panel chart pack: yfinance + Pandas + TA-Lib."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from typing import Any

import pandas as pd

from infobroker.data.indicators import calculate_macd, enrich_ohlcv, latest_snapshot
from infobroker.data.yf_pipeline import download_history


def build_chart_pack(symbol: str, start: str, end: str) -> dict[str, Any]:
    """OHLC + SMA/RSI/MACD/ATR/Bollinger via the required analysis stack."""
    df = enrich_ohlcv(download_history(symbol, start=start, end=end))
    bars = []
    for ts, row in df.iterrows():
        bars.append(
            {
                "t": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                "o": float(row["Open"]),
                "h": float(row["High"]),
                "l": float(row["Low"]),
                "c": float(row["Close"]),
                "v": float(row["Volume"]),
                "sma20": _f(row["SMA_20"] if "SMA_20" in df.columns else None),
                "sma50": _f(row["SMA_50"] if "SMA_50" in df.columns else None),
                "sma200": _f(row["SMA_200"] if "SMA_200" in df.columns else None),
                "rsi": _f(row["RSI_14"] if "RSI_14" in df.columns else None),
                "macd": _f(row["MACD"] if "MACD" in df.columns else None),
                "macd_signal": _f(row["MACD_signal"] if "MACD_signal" in df.columns else None),
                "macd_hist": _f(row["MACD_hist"] if "MACD_hist" in df.columns else None),
                "atr": _f(row["ATR_14"] if "ATR_14" in df.columns else None),
                "bb_upper": _f(row["BB_upper"] if "BB_upper" in df.columns else None),
                "bb_lower": _f(row["BB_lower"] if "BB_lower" in df.columns else None),
            }
        )
    if not bars:
        raise ValueError(f"No data for {symbol} between {start} and {end}")
    last = bars[-1]
    snap = latest_snapshot(df)
    return {
        "symbol": symbol.upper(),
        "start": start,
        "end": end,
        "bars": bars,
        "summary": {
            "last": last["c"],
            "high": max(b["h"] for b in bars),
            "low": min(b["l"] for b in bars),
            "rsi": last.get("rsi") or snap.get("rsi_14"),
            "macd": calculate_macd(df["Close"]),
            "atr": last.get("atr"),
            "change_pct": round((last["c"] / bars[0]["c"] - 1) * 100, 2) if bars[0]["c"] else None,
            "bars": len(bars),
            "data_source": "yfinance + pandas + TA-Lib",
            "stack": ["yfinance", "pandas", "TA-Lib"],
        },
        "panels": ["price_ma", "volume", "rsi", "macd"],
        "snapshot": snap,
    }


def _f(v: Any) -> float | None:
    try:
        if v is None or (isinstance(v, float) and pd.isna(v)):
            return None
        return round(float(v), 4)
    except Exception:
        return None


def build_chart_pack_async_batch(
    symbols: list[str], start: str, end: str, max_workers: int = 6
) -> dict[str, Any]:
    """Fetch several tickers' packs in parallel."""
    out: dict[str, Any] = {}
    errors: dict[str, str] = {}

    def _one(sym: str):
        return sym, build_chart_pack(sym, start, end)

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futs = [pool.submit(_one, s.upper()) for s in symbols if s]
        for fut in futs:
            try:
                sym, pack = fut.result()
                out[sym] = pack
            except Exception as exc:  # noqa: BLE001
                errors[str(exc)] = str(exc)
    return {"packs": out, "errors": errors}

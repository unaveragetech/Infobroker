"""Technical indicators via TA-Lib + Pandas Series/DataFrames."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd
import talib


def _as_float64(prices: pd.Series | np.ndarray) -> np.ndarray:
    arr = np.asarray(prices, dtype=np.float64)
    if arr.ndim != 1:
        raise ValueError("prices must be 1-D")
    return arr


def _series_like(index: pd.Index, values: np.ndarray, name: str) -> pd.Series:
    return pd.Series(values, index=index, name=name, dtype="float64")


def rsi_series(prices: pd.Series, period: int = 14) -> pd.Series:
    """Full RSI series (TA-Lib RSI)."""
    close = prices.astype(float)
    out = talib.RSI(_as_float64(close), timeperiod=int(period))
    return _series_like(close.index, out, f"RSI_{period}")


def calculate_rsi(prices: pd.Series, period: int = 14) -> float | str:
    """Latest RSI value (TA-Lib)."""
    series = rsi_series(prices, period).dropna()
    if series.empty:
        return "N/A"
    return round(float(series.iloc[-1]), 2)


def macd_series(
    prices: pd.Series,
    short_period: int = 12,
    long_period: int = 26,
    signal_period: int = 9,
) -> pd.DataFrame:
    """MACD line, signal, histogram as a Pandas DataFrame (TA-Lib MACD)."""
    close = prices.astype(float)
    macd_line, signal_line, hist = talib.MACD(
        _as_float64(close),
        fastperiod=int(short_period),
        slowperiod=int(long_period),
        signalperiod=int(signal_period),
    )
    return pd.DataFrame(
        {
            "macd_line": macd_line,
            "signal_line": signal_line,
            "histogram": hist,
        },
        index=close.index,
    )


def calculate_macd(
    prices: pd.Series,
    short_period: int = 12,
    long_period: int = 26,
    signal_period: int = 9,
) -> dict[str, float]:
    """Latest MACD snapshot (TA-Lib)."""
    df = macd_series(prices, short_period, long_period, signal_period).dropna()
    if df.empty:
        return {"macd_line": 0.0, "signal_line": 0.0, "histogram": 0.0}
    last = df.iloc[-1]
    return {
        "macd_line": float(last["macd_line"]),
        "signal_line": float(last["signal_line"]),
        "histogram": float(last["histogram"]),
    }


def sma(prices: pd.Series, window: int) -> pd.Series:
    """Simple moving average (TA-Lib SMA)."""
    close = prices.astype(float)
    out = talib.SMA(_as_float64(close), timeperiod=int(window))
    return _series_like(close.index, out, f"SMA_{window}")


def ema(prices: pd.Series, window: int) -> pd.Series:
    """Exponential moving average (TA-Lib EMA)."""
    close = prices.astype(float)
    out = talib.EMA(_as_float64(close), timeperiod=int(window))
    return _series_like(close.index, out, f"EMA_{window}")


def atr_series(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Average True Range from OHLC columns (TA-Lib ATR)."""
    high = df["High"].astype(float)
    low = df["Low"].astype(float)
    close = df["Close"].astype(float)
    out = talib.ATR(
        _as_float64(high),
        _as_float64(low),
        _as_float64(close),
        timeperiod=int(period),
    )
    return _series_like(df.index, out, f"ATR_{period}")


def bollinger_bands(
    prices: pd.Series, period: int = 20, nbdev: float = 2.0
) -> pd.DataFrame:
    """Bollinger Bands (TA-Lib BBANDS)."""
    close = prices.astype(float)
    upper, mid, lower = talib.BBANDS(
        _as_float64(close),
        timeperiod=int(period),
        nbdevup=float(nbdev),
        nbdevdn=float(nbdev),
        matype=0,
    )
    return pd.DataFrame(
        {"bb_upper": upper, "bb_mid": mid, "bb_lower": lower},
        index=close.index,
    )


def enrich_ohlcv(df: pd.DataFrame) -> pd.DataFrame:
    """
    Attach standard TA-Lib columns to an OHLCV Pandas frame.
    Expects columns: Open, High, Low, Close[, Volume].
    """
    if df is None or df.empty:
        return df
    out = df.copy()
    # Normalize column names
    rename = {c: str(c).title() for c in out.columns}
    out = out.rename(columns=rename)
    close = out["Close"].astype(float)
    out["SMA_20"] = sma(close, 20)
    out["SMA_50"] = sma(close, 50)
    if len(close) >= 200:
        out["SMA_200"] = sma(close, 200)
    out["EMA_12"] = ema(close, 12)
    out["EMA_26"] = ema(close, 26)
    out["RSI_14"] = rsi_series(close, 14)
    macd = macd_series(close)
    out["MACD"] = macd["macd_line"]
    out["MACD_signal"] = macd["signal_line"]
    out["MACD_hist"] = macd["histogram"]
    if {"High", "Low", "Close"}.issubset(out.columns):
        out["ATR_14"] = atr_series(out, 14)
    bb = bollinger_bands(close, 20, 2.0)
    out["BB_upper"] = bb["bb_upper"]
    out["BB_mid"] = bb["bb_mid"]
    out["BB_lower"] = bb["bb_lower"]
    return out


def latest_snapshot(df: pd.DataFrame) -> dict[str, Any]:
    """Compact latest indicator values from an enriched OHLCV frame."""
    if df is None or df.empty:
        return {}
    frame = enrich_ohlcv(df)
    row = frame.iloc[-1]

    def g(key: str):
        if key not in frame.columns:
            return None
        v = row[key]
        try:
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return None
            return round(float(v), 4)
        except Exception:
            return None

    return {
        "close": g("Close"),
        "rsi_14": g("RSI_14"),
        "sma_20": g("SMA_20"),
        "sma_50": g("SMA_50"),
        "sma_200": g("SMA_200"),
        "macd": g("MACD"),
        "macd_signal": g("MACD_signal"),
        "macd_hist": g("MACD_hist"),
        "atr_14": g("ATR_14"),
        "bb_upper": g("BB_upper"),
        "bb_lower": g("BB_lower"),
        "engine": "TA-Lib",
    }

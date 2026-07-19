"""Market data facade — yfinance + Pandas primary, Finnhub / Alpha Vantage cascade."""

from __future__ import annotations

from typing import Any, Optional

import pandas as pd
import yfinance as yf

from infobroker.data.providers import get_provider
from infobroker.data.yf_pipeline import download_history, download_quote


def _retry(fn, attempts: int = 3, delay: float = 0.35):
    import time

    last_exc: Exception | None = None
    for i in range(attempts):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if i < attempts - 1:
                time.sleep(delay * (i + 1))
    if last_exc:
        raise last_exc
    raise RuntimeError("retry failed")


def get_last_price(symbol: str) -> Optional[float]:
    try:
        q = _retry(lambda: download_quote(symbol))
        return float(q["Price"])
    except Exception:
        try:
            return _retry(lambda: get_provider().get_last_price(symbol))
        except Exception:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1d")
            if hist is None or hist.empty:
                info = ticker.info or {}
                price = info.get("regularMarketPrice") or info.get("currentPrice")
                return float(price) if price is not None else None
            return float(hist["Close"].iloc[-1])


def get_stock_quote(symbol: str) -> dict[str, Any]:
    """Single-symbol quote: Yahoo → Finnhub → Alpha Vantage (via provider cascade)."""
    try:
        q = _retry(lambda: download_quote(symbol))
        q["provider"] = q.get("provider") or "yahoo"
        return q
    except Exception:
        q = _retry(lambda: get_provider().get_quote(symbol))
        return q


def get_historical_data(symbol: str, start: str, end: str) -> pd.DataFrame:
    """OHLCV via yfinance → Pandas (required stack), with provider cascade fallback."""
    try:
        return _retry(lambda: download_history(symbol, start=start, end=end))
    except Exception:
        return get_provider().get_history(symbol, start, end)


def get_fundamentals(symbol: str) -> dict[str, Any]:
    # Fundamentals via yfinance (primary integrated source)
    stock = yf.Ticker(symbol)
    info = stock.info or {}
    return {
        "Company Name": info.get("longName", "N/A"),
        "Sector": info.get("sector", "N/A"),
        "PE Ratio": info.get("trailingPE", "N/A"),
        "EPS": info.get("trailingEps", "N/A"),
        "Dividend Yield": info.get("dividendYield", "N/A"),
        "Market Cap": info.get("marketCap", "N/A"),
        "52 Week High": info.get("fiftyTwoWeekHigh", "N/A"),
        "52 Week Low": info.get("fiftyTwoWeekLow", "N/A"),
        "Beta": info.get("beta", "N/A"),
        "source": "yfinance",
    }


def fetch_ohlcv(symbol: str, start: str, end: str) -> pd.DataFrame:
    return get_historical_data(symbol, start, end)

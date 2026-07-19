"""Market data providers: yfinance (primary), Finnhub, Alpha Vantage."""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Optional

import pandas as pd
import requests
import yfinance as yf

from infobroker.config import Settings, get_settings


class MarketDataError(Exception):
    pass


def _short_body(text: str, limit: int = 120) -> str:
    """Sanitize provider error bodies — never dump full responses / keys."""
    raw = (text or "").replace("\n", " ").strip()
    return raw[:limit] + ("…" if len(raw) > limit else "")


class MarketDataProvider(ABC):
    name: str

    @abstractmethod
    def get_quote(self, symbol: str) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        raise NotImplementedError

    def get_last_price(self, symbol: str) -> Optional[float]:
        q = self.get_quote(symbol)
        price = q.get("Price") or q.get("price") or q.get("c")
        return float(price) if price is not None else None


class YahooProvider(MarketDataProvider):
    """Yahoo / yfinance provider — Pandas frames from the yfinance library."""

    name = "yahoo"

    def get_quote(self, symbol: str) -> dict[str, Any]:
        from infobroker.data.yf_pipeline import download_quote

        try:
            q = download_quote(symbol)
            q["provider"] = self.name
            return q
        except Exception as exc:  # noqa: BLE001
            stock = yf.Ticker(symbol)
            data = stock.history(period="5d")
            if data is None or data.empty:
                raise MarketDataError(f"No Yahoo data for {symbol}: {exc}") from exc
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            latest = data.iloc[-1]
            return {
                "Price": float(latest["Close"]),
                "Daily High": float(latest["High"]),
                "Daily Low": float(latest["Low"]),
                "Volume": float(latest["Volume"]),
                "Previous Close": float(data["Close"].iloc[-2]) if len(data) > 1 else float(latest["Close"]),
                "Market Cap": "N/A",
                "provider": self.name,
            }

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        from infobroker.data.yf_pipeline import download_history

        try:
            return download_history(symbol, start=start, end=end)
        except Exception as exc:  # noqa: BLE001
            df = yf.download(symbol, start=start, end=end, progress=False, auto_adjust=True)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            if df is None or df.empty:
                raise MarketDataError(f"No Yahoo history for {symbol}: {exc}") from exc
            rename = {c: str(c).title() for c in df.columns}
            return df.rename(columns=rename)


class FinnhubProvider(MarketDataProvider):
    name = "finnhub"
    BASE = "https://finnhub.io/api/v1"

    def __init__(self, api_key: str):
        if not api_key:
            raise MarketDataError("FINNHUB_API_KEY required")
        self.api_key = api_key

    def _get(self, path: str, **params: Any) -> Any:
        params = {**params, "token": self.api_key}
        resp = requests.get(f"{self.BASE}{path}", params=params, timeout=30)
        if resp.status_code >= 400:
            raise MarketDataError(
                f"Finnhub {path}: {resp.status_code} {_short_body(resp.text)}"
            )
        return resp.json()

    def get_quote(self, symbol: str) -> dict[str, Any]:
        q = self._get("/quote", symbol=symbol.upper())
        if q.get("c") in (None, 0):
            raise MarketDataError(f"No Finnhub quote for {symbol}")
        # Prefer Finnhub's intraday % when present
        pc = float(q.get("pc") or 0)
        price = float(q["c"])
        return {
            "Price": price,
            "Daily High": float(q.get("h") or 0),
            "Daily Low": float(q.get("l") or 0),
            "Volume": "N/A",
            "Previous Close": pc,
            "change_pct_day": float(q["dp"]) if q.get("dp") is not None else None,
            "Market Cap": "N/A",
            "provider": self.name,
        }

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        start_ts = int(datetime.strptime(start, "%Y-%m-%d").timestamp())
        end_ts = int(datetime.strptime(end, "%Y-%m-%d").timestamp())
        data = self._get(
            "/stock/candle",
            **{
                "symbol": symbol.upper(),
                "resolution": "D",
                "from": start_ts,
                "to": end_ts,
            },
        )
        if data.get("s") != "ok":
            raise MarketDataError(f"No Finnhub candles for {symbol}")
        df = pd.DataFrame(
            {
                "Open": data["o"],
                "High": data["h"],
                "Low": data["l"],
                "Close": data["c"],
                "Volume": data["v"],
            },
            index=pd.to_datetime(data["t"], unit="s"),
        )
        df.index.name = "Date"
        return df


class AlphaVantageProvider(MarketDataProvider):
    name = "alphavantage"
    BASE = "https://www.alphavantage.co/query"

    def __init__(self, api_key: str):
        if not api_key:
            raise MarketDataError("ALPHAVANTAGE_API_KEY required")
        self.api_key = api_key

    def _get(self, **params: Any) -> Any:
        params = {**params, "apikey": self.api_key}
        resp = requests.get(self.BASE, params=params, timeout=30)
        if resp.status_code >= 400:
            raise MarketDataError(
                f"Alpha Vantage error: {resp.status_code} {_short_body(resp.text)}"
            )
        data = resp.json()
        if "Note" in data or "Information" in data:
            raise MarketDataError(_short_body(str(data.get("Note") or data.get("Information"))))
        if "Error Message" in data:
            raise MarketDataError(_short_body(str(data["Error Message"])))
        return data

    def get_quote(self, symbol: str) -> dict[str, Any]:
        data = self._get(function="GLOBAL_QUOTE", symbol=symbol.upper())
        gq = data.get("Global Quote") or {}
        if not gq:
            raise MarketDataError(f"No Alpha Vantage quote for {symbol}")
        return {
            "Price": float(gq.get("05. price") or 0),
            "Daily High": float(gq.get("03. high") or 0),
            "Daily Low": float(gq.get("04. low") or 0),
            "Volume": float(gq.get("06. volume") or 0),
            "Previous Close": float(gq.get("08. previous close") or 0),
            "Market Cap": "N/A",
            "provider": self.name,
        }

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        data = self._get(
            function="TIME_SERIES_DAILY_ADJUSTED",
            symbol=symbol.upper(),
            outputsize="full",
        )
        series = data.get("Time Series (Daily)") or {}
        if not series:
            raise MarketDataError(f"No Alpha Vantage history for {symbol}")
        rows = []
        for day, vals in series.items():
            if start <= day <= end:
                rows.append(
                    {
                        "Date": pd.Timestamp(day),
                        "Open": float(vals["1. open"]),
                        "High": float(vals["2. high"]),
                        "Low": float(vals["3. low"]),
                        "Close": float(vals["4. close"]),
                        "Volume": float(vals["6. volume"]),
                    }
                )
        if not rows:
            raise MarketDataError(f"No Alpha Vantage rows in range for {symbol}")
        df = pd.DataFrame(rows).set_index("Date").sort_index()
        return df


class CascadingProvider(MarketDataProvider):
    """Try preferred providers in order until one succeeds."""

    name = "auto"

    def __init__(self, providers: list[MarketDataProvider]):
        self.providers = providers

    def get_quote(self, symbol: str) -> dict[str, Any]:
        errors: list[str] = []
        for p in self.providers:
            try:
                return p.get_quote(symbol)
            except Exception as exc:  # noqa: BLE001 — cascade
                errors.append(f"{p.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "No providers configured")

    def get_history(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        errors: list[str] = []
        for p in self.providers:
            try:
                return p.get_history(symbol, start, end)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{p.name}: {exc}")
        raise MarketDataError("; ".join(errors) or "No providers configured")


def build_market_data(settings: Settings | None = None) -> MarketDataProvider:
    """Build provider cascade.

    Default (auto): yfinance first — already integrated and reliable — then
    Finnhub / Alpha Vantage when keys are present as complementary sources.
    """
    settings = settings or get_settings()
    preferred = settings.data_provider.strip().lower()
    if preferred in {"yfinance", "yf"}:
        preferred = "yahoo"

    # yfinance is always first-class, never optional
    available: list[MarketDataProvider] = [YahooProvider()]
    if settings.finnhub_key:
        available.append(FinnhubProvider(settings.finnhub_key))
    if settings.alphavantage_key:
        available.append(AlphaVantageProvider(settings.alphavantage_key))

    by_name = {p.name: p for p in available}
    if preferred in by_name and preferred != "auto":
        ordered = [by_name[preferred]] + [p for p in available if p.name != preferred]
        return CascadingProvider(ordered)
    # auto: keep yfinance first
    return CascadingProvider(available)


_PROVIDER: Optional[MarketDataProvider] = None


def clear_provider_cache() -> None:
    global _PROVIDER
    _PROVIDER = None


def get_provider() -> MarketDataProvider:
    global _PROVIDER
    if _PROVIDER is None:
        _PROVIDER = build_market_data()
    return _PROVIDER

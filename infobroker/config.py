"""Environment-driven configuration (reads env at call time)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
load_dotenv(ROOT / ".env")


def _bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    broker: str
    data_provider: str
    starting_cash: float
    users_path: Path
    ledger_path: Path
    cache_path: Path
    web_host: str
    web_port: int
    alpaca_key: str
    alpaca_secret: str
    alpaca_paper: bool
    public_secret: str
    public_account_id: str
    public_base: str
    tradier_token: str
    tradier_account: str
    tradier_sandbox: bool
    finnhub_key: str
    alphavantage_key: str
    ibkr_base: str
    schwab_key: str
    schwab_secret: str
    schwab_refresh: str
    schwab_account: str
    tradestation_token: str
    tradestation_account: str
    tradestation_sim: bool


def get_settings() -> Settings:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    load_dotenv(ROOT / ".env", override=True)
    data_provider = os.getenv("INFOBROKER_DATA_PROVIDER", "yahoo").strip().lower()
    if data_provider in {"yfinance", "yf"}:
        data_provider = "yahoo"
    return Settings(
        broker=os.getenv("INFOBROKER_BROKER", "paper").strip().lower(),
        data_provider=data_provider,
        starting_cash=float(os.getenv("INFOBROKER_STARTING_CASH", "10000")),
        users_path=DATA_DIR / "users.json",
        ledger_path=DATA_DIR / "ledger.json",
        cache_path=ROOT / "stock_cache.json",
        web_host=os.getenv("INFOBROKER_WEB_HOST", "127.0.0.1"),
        web_port=int(os.getenv("INFOBROKER_WEB_PORT", "8000")),
        alpaca_key=os.getenv("ALPACA_API_KEY", ""),
        alpaca_secret=os.getenv("ALPACA_API_SECRET", ""),
        alpaca_paper=_bool("ALPACA_PAPER", True),
        public_secret=os.getenv("PUBLIC_PERSONAL_SECRET", ""),
        public_account_id=os.getenv("PUBLIC_ACCOUNT_ID", ""),
        public_base=os.getenv("PUBLIC_API_BASE_URL", "https://api.public.com"),
        tradier_token=os.getenv("TRADIER_ACCESS_TOKEN", ""),
        tradier_account=os.getenv("TRADIER_ACCOUNT_ID", ""),
        tradier_sandbox=_bool("TRADIER_SANDBOX", True),
        finnhub_key=os.getenv("FINNHUB_API_KEY", ""),
        alphavantage_key=os.getenv("ALPHAVANTAGE_API_KEY", ""),
        ibkr_base=os.getenv("IBKR_CLIENT_PORTAL_BASE", "https://localhost:5000"),
        schwab_key=os.getenv("SCHWAB_APP_KEY", ""),
        schwab_secret=os.getenv("SCHWAB_APP_SECRET", ""),
        schwab_refresh=os.getenv("SCHWAB_REFRESH_TOKEN", ""),
        schwab_account=os.getenv("SCHWAB_ACCOUNT_HASH", ""),
        tradestation_token=os.getenv("TRADESTATION_ACCESS_TOKEN", ""),
        tradestation_account=os.getenv("TRADESTATION_ACCOUNT_ID", ""),
        tradestation_sim=_bool("TRADESTATION_SIM", True),
    )

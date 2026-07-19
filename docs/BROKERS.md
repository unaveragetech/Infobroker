# Free APIs for Infobroker

Two layers: **execution brokers** (place orders) and **market data** (quotes/history for charts, teaching, backtests).

## Execution — ranked

| Rank | Broker | Speed | Notes |
|------|--------|-------|-------|
| **0** | **paper** | Instant | Local ledger; Yahoo/Finnhub fills — **default, no keys** |
| **1** | **Alpaca** | Excellent (REST + WS) | $0 stocks; paper ≈ live API |
| **2** | **Public** | Strong | Individual Trader API — **live**; practice in paper first |
| **3** | **Tradier** | Good | Sandbox available; options path later |

```bash
INFOBROKER_BROKER=paper   # or alpaca | public | tradier
```

## Market data — ranked

| Rank | Provider | Free tier | Best for |
|------|----------|-----------|----------|
| **1** | **Yahoo Finance (`yfinance`)** | No key | Default research/charts/backtests |
| **2** | **Finnhub** | Free REST | Backup quotes / news |
| **3** | **Alpha Vantage** | Free key (rate-limited) | Extra OHLCV |

```bash
INFOBROKER_DATA_PROVIDER=yahoo   # yahoo | finnhub | alphavantage | auto
FINNHUB_API_KEY=
ALPHAVANTAGE_API_KEY=
```

`auto` prefers **yfinance first**, then keyed providers. Closed US cash still serves **last cached** quotes from the universe engine — see [DATA.md](DATA.md).

## Env vars (execution)

Copy [`.env.example`](../.env.example) → `.env`. Leave values blank until you need them.

```bash
# Alpaca
ALPACA_API_KEY=
ALPACA_API_SECRET=
ALPACA_PAPER=true

# Public — https://public.com/api/docs
PUBLIC_PERSONAL_SECRET=
PUBLIC_ACCOUNT_ID=
PUBLIC_API_BASE_URL=https://api.public.com

# Tradier
TRADIER_ACCESS_TOKEN=
TRADIER_ACCOUNT_ID=
TRADIER_SANDBOX=true
```

**Never commit `.env`.** Prefer the desk **API Keys** modal (localhost-only) over pasting secrets into chat logs.

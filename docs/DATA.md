# How Infobroker market data works

Also available in the desk under **Settings → Docs → How market data works**.

## Pipeline

```
Listings (NASDAQ Trader directories)
        ↓
Universe cache (data/universe.json)  ← rotating Yahoo quote refresh
        ↓
Live board / Movers / Grapevine get_prices
        ↓
Charts & backtests ← yfinance → pandas → TA-Lib
```

## Providers

| Priority | Provider | Needs key? | Used for |
|----------|----------|------------|----------|
| 1 | Yahoo via yfinance | No | Default quotes, history, backtests |
| 2 | Finnhub | Yes | Backup quotes / news |
| 3 | Alpha Vantage | Yes | Backup OHLCV |

```bash
INFOBROKER_DATA_PROVIDER=yahoo   # yahoo | finnhub | alphavantage | auto
```

## Closed markets

US cash closed does **not** clear the universe cache. Last `price`, `change_pct_day`, and `as_of` remain available for:

- Markets → Live / Movers
- Grapevine `get_prices` / `get_watchlist_quotes` / `get_quote`
- Trading board (last quotes)

## Live board behavior

| State | Behavior |
|-------|----------|
| US open | Tick updates ~1s (shared server cache) |
| US closed | Last/delayed quotes; clocks red; stream slows |

## Key modules

| Module | Role |
|--------|------|
| `infobroker/universe/engine.py` | Listings + quote cache |
| `infobroker/data/yf_pipeline.py` | Yahoo download helpers |
| `infobroker/data/multisource.py` | Live board assembly |
| `infobroker/data/highlights.py` | Movers / tracked notables |
| `infobroker/markets/sessions.py` | World clocks / open-closed |

## APIs (desk running)

- `GET /api/live` — live board
- `GET /api/markets/clocks` — session clocks
- `GET /api/universe` — listings page
- `GET /api/quote/{symbol}` — single quote
- `GET /api/docs` — documentation catalog

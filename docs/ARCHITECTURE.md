# Architecture

## Package layout

```
infobroker/
  assistant/       # Grapevine agent, tools, desk snapshot, follow-ups
  brokers/         # paper, alpaca, public, tradier (+ optional adapters)
  data/            # yfinance pipeline, highlights, multisource live board
  universe/        # NASDAQ Trader listings + rotating quote cache
  markets/         # session clocks, foreign proxy boards
  risk/            # pre-trade checks
  education/       # lessons, tutor, trade stories
  strategies/      # backtests + scanner
  services/        # Ollama / MCP process control
  web/             # FastAPI desk + static UI
  portfolio.py     # account / P&L rollup
  trading_board.py
  auto_track.py
  docs_catalog.py  # Settings → Docs source
  mcp_server.py
  cli.py
docs/              # Markdown reference (also served in Settings)
data/              # local runtime only (gitignored): universe, ledger, logs
```

## Request path

1. Browser → FastAPI (`infobroker/web/app.py`)
2. Heavy work often `asyncio.to_thread(...)` so clocks / live stay responsive
3. Universe / data / broker adapters
4. JSON → `web/static/app.js`

## Desk surface

| Tab | Purpose |
|-----|---------|
| Markets | Live board, universe, movers, scanner, symbol |
| Trading | Bid/ask board + quick buy/sell |
| Portfolio | Equity, positions, orders, auto-track |
| Learning | Tutor, journal, lessons |
| Strategies / Chart studio | Free yfinance backtests and OHLC packs |
| Services & keys | Ollama, MCP, acquire keys |
| Settings | Project docs + about/health |

Right rail: order ticket + blotter. Far right: Grapevine coach (follow-up chips, optional overlays).

## Persistence (local only)

| Path | Contents |
|------|----------|
| `.env` | Secrets (never commit) |
| `data/universe.json` | Listings + quote cache |
| `data/ledger.json` | Paper broker ledger |
| `data/watchlist.json` | Watchlist |
| `data/auto_track.json` | Auto-track rules |
| `data/users.json` | Hashed desk users (migrated from legacy plaintext) |

## Related

- [DATA.md](DATA.md) — quote cascade and closed markets
- [MCP.md](MCP.md) — Grapevine + MCP
- [BROKERS.md](BROKERS.md) — brokers and data providers

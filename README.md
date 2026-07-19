# Infobroker

Local trading desk: learn chart & risk skills, research US equities, paper trade, then connect free broker APIs when ready.

New work lives in the `infobroker/` package. Root scripts (`app.py`, `graph.py`, `ai.py`, `tick.py`, …) are **legacy CLI** and are not required for the desk.

## Docs

| Link | Contents |
|------|----------|
| [docs/README.md](docs/README.md) | Documentation index |
| [docs/DATA.md](docs/DATA.md) | How market data & the universe cache work |
| [docs/BROKERS.md](docs/BROKERS.md) | Brokers + data providers |
| [docs/MCP.md](docs/MCP.md) | Grapevine assistant + MCP |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Package layout |

In the running desk: **Settings → Docs** (same catalog via `/api/docs`).

## Free stack

### Execution

| Rank | Broker | Why |
|------|--------|-----|
| 0 | **paper** | Local ledger, no keys — default |
| 1 | **Alpaca** | Fast REST/WS, paper≈live, $0 stocks |
| 2 | **Public** | Commission-free Individual Trader API (live — practice first) |
| 3 | **Tradier** | Solid REST; options path later |

### Market data & analysis

| Layer | Library | Role |
|-------|---------|------|
| Download | [yfinance](https://pypi.org/project/yfinance/) | Yahoo history + near-real-time quotes |
| Frames | [pandas](https://pypi.org/project/pandas/) | OHLCV tables |
| Indicators | [TA-Lib](https://pypi.org/project/TA-Lib/) | RSI, MACD, SMA/EMA, ATR, … |

Optional: Finnhub, Alpha Vantage (keys in the desk). Details: [docs/BROKERS.md](docs/BROKERS.md), [docs/DATA.md](docs/DATA.md).

## Quick start

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env

# Desk UI
python -m infobroker.web.app
# → http://127.0.0.1:8000/
# → OpenAPI http://127.0.0.1:8000/docs

# Optional CLI
python -m infobroker
```

Default broker is **paper**. For live-capable brokers, set keys only in local `.env` (never commit):

```bash
INFOBROKER_BROKER=alpaca   # or public | tradier
ALPACA_PAPER=true
```

## Desk features

- **Markets** — live board, universe, movers, scanner, symbol detail; world clocks
- **Trading** — bid/ask board + quick buy/sell
- **Portfolio** — equity, positions, orders, auto-track gainers
- **Learning** — tutor path, trade journal, skill lessons
- **Strategies / Chart studio** — free yfinance backtests and OHLC packs
- **Services & keys** — Ollama, MCP process, acquire API keys
- **Settings** — project docs and technical reference
- **Grapevine** — local Ollama coach: prices (even when closed), hunt, follow-up chips, optional UI coach
- **Order ticket** — market/limit/stop + risk preview; paper by default

## Project layout

```
infobroker/          # package (desk, brokers, data, assistant, …)
docs/                # markdown reference
.env.example         # template — copy to .env locally
data/                # runtime only (gitignored): universe cache, paper ledger
```

## Safety

- Start on `INFOBROKER_BROKER=paper` or Alpaca paper
- **Never commit `.env`, API secrets, or `users.json`**
- Public.com Individual API is **live** — practice in paper first
- Grapevine paper tools refuse live fills

## MCP (Cursor)

See [docs/MCP.md](docs/MCP.md) and the safe fragment [docs/mcp.example.json](docs/mcp.example.json). Do not commit machine-specific `.cursor/mcp.json` paths.

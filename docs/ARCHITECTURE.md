# Architecture

Infobroker is a **local-first trading desk**: FastAPI + static UI, a universe quote cache, optional brokers, and a Grapevine (Ollama) assistant.

Also in the desk: **Settings → Docs**.

## Full stack

```mermaid
flowchart TB
  subgraph Client["Browser desk"]
    UI[Markets / Trading / Portfolio / Learning]
    GV[Grapevine chat + follow-ups]
    Ticket[Order ticket + blotter]
  end

  subgraph Server["Python process — infobroker.web.app"]
    API[FastAPI REST + SSE]
    Asst[Assistant agent + tools]
    Univ[Universe engine worker]
    Risk[Risk guardrails]
    Paper[Paper / broker adapters]
  end

  subgraph Local["Local machine"]
    ENV[".env secrets"]
    DATA["data/ universe · ledger · watchlist"]
    OLLAMA[Ollama arriella-grapevine]
  end

  subgraph External["External APIs"]
    YF[Yahoo Finance]
    FH[Finnhub optional]
    AV[Alpha Vantage optional]
    BR[Alpaca / Public / Tradier]
  end

  UI --> API
  GV --> API
  Ticket --> API
  API --> Univ
  API --> Asst
  API --> Risk
  API --> Paper
  Asst --> OLLAMA
  Asst --> Univ
  Univ --> DATA
  Univ --> YF
  Paper --> BR
  Paper --> DATA
  API --> YF
  API --> FH
  API --> AV
  ENV -.-> API
```

## Desk request path

```mermaid
sequenceDiagram
  participant B as Browser
  participant F as FastAPI
  participant T as Thread pool
  participant C as Universe / tick cache
  participant Y as Yahoo / brokers

  B->>F: GET /api/live or /api/assistant/chat
  alt heavy work
    F->>T: asyncio.to_thread(...)
    T->>C: read / refresh
    C->>Y: only on cache miss / batch
    Y-->>C: quotes
    C-->>T: rows
    T-->>F: result
  else light / cached
    F->>C: read
    C-->>F: rows
  end
  F-->>B: JSON
```

## Data plane

```mermaid
flowchart LR
  L[NASDAQ Trader listings] --> U[Universe store]
  U --> Q[Rotating quote batches]
  Q --> Y[Yahoo bulk]
  Y --> U
  U --> Live[Live board]
  U --> Movers[Movers]
  U --> GV[Grapevine get_prices]
  Y -.->|miss| FH[Finnhub]
  FH -.->|explicit| AV[Alpha Vantage]
```

## Package layout

```
infobroker/
  assistant/       # Grapevine agent, tools, desk snapshot, follow-ups
  brokers/         # paper, alpaca, public, tradier (+ optional adapters)
  data/            # yfinance pipeline, highlights, multisource live board
  universe/        # listings + quote cache engine
  markets/         # session clocks, foreign proxy boards, live ticks
  risk/            # pre-trade checks
  education/       # lessons, tutor, trade stories
  strategies/      # backtests + scanner
  services/        # Ollama / MCP process control
  web/             # FastAPI desk + static UI
  portfolio.py
  trading_board.py
  auto_track.py
  docs_catalog.py
  mcp_server.py
  cli.py
docs/              # Markdown reference (+ Settings → Docs)
data/              # runtime only (gitignored)
```

## Desk surface

| Tab | Purpose |
|-----|---------|
| Markets | Live board, universe, movers, scanner, symbol |
| Trading | Bid/ask board + quick buy/sell |
| Portfolio | Equity, positions, orders, auto-track |
| Learning | Tutor, journal, lessons |
| Strategies / Chart studio | Free yfinance backtests and OHLC packs |
| Services & keys | Ollama, MCP, acquire keys |
| Settings | Docs, about/health, donate |

## Persistence (local only)

| Path | Contents |
|------|----------|
| `.env` | Secrets (never commit) |
| `data/universe.json` | Listings + quote cache |
| `data/ledger.json` | Paper broker ledger |
| `data/watchlist.json` | Watchlist |
| `data/auto_track.json` | Auto-track rules |

## Related

- [RATE_LIMITS.md](RATE_LIMITS.md) — quotas and avoidance strategies  
- [DATA.md](DATA.md) — quote cascade and closed markets  
- [MCP.md](MCP.md) — Grapevine + MCP  
- [BROKERS.md](BROKERS.md) — brokers and data providers  

"""Project documentation catalog for the Settings → Docs desk panel."""

from __future__ import annotations

import html
import re
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]

# Curated technical pages (always available even if markdown files move)
_BUILTIN: dict[str, dict[str, str]] = {
    "overview": {
        "title": "Overview",
        "group": "Start here",
        "body": """# Infobroker technical overview

Infobroker is a **local trading desk**: learn chart/risk skills, research US equities, paper trade, then connect free broker APIs when ready.

## What runs locally

| Piece | Role |
|-------|------|
| FastAPI desk (`python -m infobroker.web.app`) | UI + REST API on `http://127.0.0.1:8000` |
| Universe engine | NASDAQ Trader listings + rotating Yahoo quote cache |
| Paper broker | Local ledger — no keys required |
| Grapevine | Ollama assistant (`arriella-grapevine`) with desk tools |
| MCP server | Optional Cursor tool bridge (`python -m infobroker.mcp_server`) |

## First run

After `python -m infobroker.web.app`, open the desk and click **Tour**. Full usage, screenshots, and model requirements: open **Usage & insights (repo)** in this list, or `docs/USAGE.md`.

## Desk tabs

- **Markets** — live board, universe, movers, scanner, symbol detail
- **Trading** — bid/ask board + quick buy/sell
- **Portfolio** — equity, positions, orders, auto-track gainers
- **Learning** — tutor, journal, skill lessons
- **Strategies / Chart studio** — free yfinance backtests and OHLC packs
- **Services & keys** — Ollama, MCP process, API key signup
- **Settings** — this documentation and technical reference

## Grapevine

Designed for **arriella-grapevine**. Alternates need chat completion, image summary, image→text, thinking, and reductive output.

## OpenAPI

Interactive API schema: [http://127.0.0.1:8000/docs](/docs)
""",
    },
    "usage": {
        "title": "Usage & first tour",
        "group": "Start here",
        "body": """# Usage & first tour

## After you start the desk

1. Open `http://127.0.0.1:8000/`
2. Click **Tour** in the top bar (or in the Grapevine sidebar)

The guided tour is the recommended onboarding path. Re-run anytime.

## Grapevine (highly advised)

```bash
ollama pull arriella-grapevine
```

Grapevine was designed for this desk. If you use another model it should support:

- Chat completion
- Image summary
- Image → text
- Thinking (multi-step tool plans)
- Reductive (short) output

Without Ollama, fast-path answers (prices, gainers, cash, open/closed) still work.

## Quick first session

1. Finish **Tour**
2. Confirm `broker: paper`
3. Add watchlist tickers → **Refresh**
4. Try Grapevine chips (“Show my watchlist prices”)
5. Open **Learning → Tutor**

Screenshots and deeper tab insights: open **Usage (repo file)** in this docs list (`docs/USAGE.md`).
""",
    },
    "data-pipeline": {
        "title": "How market data works",
        "group": "Data",
        "body": """# How market data works

## Stack (required)

| Layer | Library | Role |
|-------|---------|------|
| Download | **yfinance** | Yahoo Finance history + near-real-time quotes |
| Frames | **pandas** | OHLCV tables, joins, resampling |
| Indicators | **TA-Lib** | RSI, MACD, SMA/EMA, ATR, Bollinger, … |

Optional complements (keys in desk): **Finnhub**, **Alpha Vantage**.

Set provider:

```bash
INFOBROKER_DATA_PROVIDER=yahoo   # yahoo | finnhub | alphavantage | auto
```

`auto` still prefers yfinance first, then keyed providers.

## Quote cascade

1. **Universe cache** — last snapshot stored on each listing (works when US cash is **closed**)
2. **Yahoo / yfinance** — primary live pull
3. **Finnhub / Alpha Vantage** — fallback when configured

Grapevine tools `get_prices` / `get_watchlist_quotes` read the universe cache first so closed sessions still show last prices.

## Universe engine

- Listings from **NASDAQ Trader** directories (NASDAQ / NYSE / Arca / …)
- Background worker rotates quote refresh across the universe
- Movers / volume leaders / live board read **quoted** rows only
- Paths: `infobroker/universe/engine.py`, cache under `data/`

## Live board vs closed market

| State | Behavior |
|-------|----------|
| US open | Tick stream ~1s (shared server cache); board updates aggressively |
| US closed | Last session / delayed quotes remain; clocks show red; stream slows |

**Closed ≠ no prices.** The desk keeps `as_of` timestamps on cached quotes.

## Charts & analysis

- Intraday OHLC: `/api/ohlc/{symbol}/intraday`
- Chart pack (studio): `/api/charts/pack` via yfinance → pandas → TA-Lib
- Symbol analyze: `/api/analyze`
""",
    },
    "live-universe": {
        "title": "Live board & universe",
        "group": "Data",
        "body": """# Live board & universe

## Markets → Live

- Modes: full universe, heat, gainers, losers, volume
- Views: tiles, blocks, volume map, table, by venue
- Foreign clocks (LDN/FRA/TYO/HK/SYD) open **proxy boards** (US-listed ETFs/ADRs)

API: `GET /api/live`, `GET /api/markets/board`, `GET /api/markets/clocks`

## Universe tab

- Paginated listings with optional “quoted only”
- **Fill quotes / Refresh quotes** pushes Yahoo batches into the cache
- Status: `GET /api/universe/status`

## Movers & scanner

- Movers prefer universe quote cache (gainers/losers/week/volume)
- Scanner runs RSI/MA/MACD teaching signals over liquid quoted names (or watchlist)

## Trading board

`GET /api/trading/board` — watchlist + liquid names with bid/ask/last and position qty for one-click paper buy/sell.
""",
    },
    "brokers-risk": {
        "title": "Brokers, orders & risk",
        "group": "Trading",
        "body": """# Brokers, orders & risk

## Execution rank

| Rank | Broker | Notes |
|------|--------|-------|
| 0 | **paper** | Local ledger, Yahoo fills — default, no keys |
| 1 | **Alpaca** | $0 stocks; paper≈live API |
| 2 | **Public** | Individual Trader API (live — practice first) |
| 3 | **Tradier** | Sandbox available; options path later |

Env: `INFOBROKER_BROKER=paper|alpaca|public|tradier`

## Order ticket

Supports market / limit / stop / stop-limit plus stop-loss & take-profit brackets.
Always **Preview risk** before Submit.

## Risk guardrails (`infobroker/risk`)

- Max position % of equity
- Required stop on live buys (configurable)
- Teaching checklist on the desk
- Grapevine `place_paper_order` refuses live mode

## Portfolio & auto-track

- Portfolio rollup: cash, equity, positions, orders, unrealized P&L
- Auto-track: scan quoted universe for day gainers ≥ X% and add to watchlist
""",
    },
    "grapevine": {
        "title": "Grapevine & MCP",
        "group": "Assistant",
        "body": """# Grapevine assistant & MCP

## Grapevine (desk sidebar)

Local Ollama model `arriella-grapevine` (override with `INFOBROKER_OLLAMA_MODEL`).

- Fast path answers common desk Q&A without LLM
- Tool loop for deeper actions (prices, hunt, preview, paper orders)
- Coach overlays can highlight desk widgets (manual Next — light UI)
- **Send view** captures the active panel only (not full page)

Important tools:

- `get_prices` / `get_watchlist_quotes` — last prices from universe (works when closed)
- `find_opportunities` — small cached scan
- `explain_desk` — UI guide
- `get_portfolio`, `get_clocks`, `get_trading_board`

## MCP server

```bash
python -m infobroker.mcp_server
```

Cursor wires this via `.cursor/mcp.json`. Services tab can start/stop/restart the desk-managed MCP process.

See also the **MCP (repo file)** page in this Settings docs list.
""",
    },
    "architecture": {
        "title": "Architecture & layout",
        "group": "Reference",
        "body": """# Architecture & project layout

```
infobroker/
  assistant/     # Grapevine agent, tools, desk snapshot
  brokers/       # paper, alpaca, public, tradier
  data/          # yfinance pipeline, highlights, multisource live board
  universe/      # listings + quote cache engine
  markets/       # session clocks, foreign proxy boards
  risk/          # pre-trade checks
  education/     # lessons, tutor, trade stories
  strategies/    # backtests + scanner
  portfolio.py   # account / P&L rollup
  trading_board.py
  auto_track.py
  web/           # FastAPI + static desk UI
  mcp_server.py
  docs_catalog.py  # this Settings docs source
docs/
  BROKERS.md
  MCP.md
  DATA.md
exchanges.md
```

## Request path (typical)

1. Browser → FastAPI route (`infobroker/web/app.py`)
2. Heavy work often `asyncio.to_thread(...)` so clocks/live stay responsive
3. Data layer / universe / broker adapters
4. JSON back to `app.js`

## Persistence

- `.env` — secrets (gitignored)
- `data/` — universe cache, paper ledger, users, auto-track, MCP log
- Watchlist stored locally via watchlist module
""",
    },
    "rate-limits": {
        "title": "Rate limits & avoidance",
        "group": "Data",
        "body": """# Rate limits & how Infobroker avoids them

Free Yahoo / Finnhub / Alpha Vantage tiers punish aggressive polling. Infobroker is built around **caches and rotation**.

## Strategies

1. **Universe cache** — rotating batches (~160 symbols / ~35s) into `data/universe.json`
2. **Shared tick cache** — ~0.85s when US open, ~12s when closed
3. **Bulk Yahoo first**, per-symbol only on misses
4. **Cascade** Yahoo → Finnhub → Alpha Vantage (AV never for full universe)
5. **Grapevine light path** — cache prices; opportunity scan cached ~3 min
6. **Retries with backoff** — no tight spin loops

Full detail with diagrams: open the **Rate limits (repo)** page in this docs list, or `docs/RATE_LIMITS.md`.
""",
    },
    "env-safety": {
        "title": "Environment & safety",
        "group": "Reference",
        "body": """# Environment & safety

## Essential env

```bash
INFOBROKER_BROKER=paper
INFOBROKER_DATA_PROVIDER=yahoo
ALPACA_PAPER=true
OLLAMA_HOST=http://127.0.0.1:11434
INFOBROKER_OLLAMA_MODEL=arriella-grapevine:latest
```

Copy `.env.example` → `.env`. **Never commit secrets.**

## Safety defaults

- Start on paper or Alpaca paper
- Public.com Individual API is live — practice first
- Grapevine will not claim live broker fills from paper tools
- Passwords hashed (PBKDF2); legacy plaintext migrated into `data/users.json`

## Useful URLs

| URL | Purpose |
|-----|---------|
| `/` | Desk UI |
| `/docs` | FastAPI OpenAPI |
| `/api/health` | Broker, data provider, Ollama/MCP chips |
| `/api/docs` | This documentation catalog (JSON) |
""",
    },
}

_FILE_DOCS: list[tuple[str, str, str, Path]] = [
    ("readme", "README (repo)", "Project files", ROOT / "README.md"),
    ("docs-index", "Docs index", "Project files", ROOT / "docs" / "README.md"),
    ("usage-md", "Usage (repo file)", "Project files", ROOT / "docs" / "USAGE.md"),
    ("brokers-md", "Brokers & data APIs", "Project files", ROOT / "docs" / "BROKERS.md"),
    ("mcp-md", "MCP (repo file)", "Project files", ROOT / "docs" / "MCP.md"),
    ("data-md", "Data deep-dive (repo)", "Project files", ROOT / "docs" / "DATA.md"),
    ("architecture-md", "Architecture (repo)", "Project files", ROOT / "docs" / "ARCHITECTURE.md"),
    ("rate-limits-md", "Rate limits (repo)", "Project files", ROOT / "docs" / "RATE_LIMITS.md"),
    ("donate-md", "Donate (repo)", "Project files", ROOT / "DONATE.md"),
    ("license-md", "LICENSE (SDUC)", "Project files", ROOT / "LICENSE"),
    ("exchanges-md", "Exchanges notes", "Project files", ROOT / "exchanges.md"),
]


def _md_to_html(md: str) -> str:
    """Small safe-ish Markdown subset → HTML for the Settings docs viewer."""
    text = md.replace("\r\n", "\n")
    lines = text.split("\n")
    out: list[str] = []
    in_code = False
    code_lang = ""
    in_ul = False
    in_ol = False
    in_table = False
    table_rows: list[list[str]] = []

    def close_lists() -> None:
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    def flush_table() -> None:
        nonlocal in_table, table_rows
        if not table_rows:
            in_table = False
            return
        out.append('<div class="docs-table-wrap"><table class="docs-table">')
        for i, cells in enumerate(table_rows):
            tag = "th" if i == 0 else "td"
            # skip markdown separator row
            if i == 1 and all(re.fullmatch(r":?-+:?", c.strip()) for c in cells):
                continue
            out.append("<tr>" + "".join(f"<{tag}>{_inline(c.strip())}</{tag}>" for c in cells) + "</tr>")
        out.append("</table></div>")
        table_rows = []
        in_table = False

    def _doc_img_src(src: str) -> str:
        raw = src.strip()
        if raw.startswith(("http://", "https://", "/")):
            return raw
        # docs/USAGE.md → images/foo.png  (served at /docs-images/)
        name = raw.replace("\\", "/").split("/")[-1]
        return f"/docs-images/{name}"

    def _inline(s: str) -> str:
        s = html.escape(s)
        s = re.sub(r"`([^`]+)`", r'<code class="docs-code">\1</code>', s)
        s = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", s)
        s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", s)
        # Images before links so ![alt](url) is not treated as a bare link
        s = re.sub(
            r"!\[([^\]]*)\]\(([^)]+)\)",
            lambda m: (
                f'<img class="docs-img" src="{html.escape(_doc_img_src(m.group(2)))}" '
                f'alt="{html.escape(m.group(1))}" loading="lazy" />'
            ),
            s,
        )
        s = re.sub(
            r"\[([^\]]+)\]\(([^)]+)\)",
            r'<a href="\2" target="_blank" rel="noopener">\1</a>',
            s,
        )
        return s

    for line in lines:
        if line.startswith("```"):
            close_lists()
            flush_table()
            if not in_code:
                in_code = True
                code_lang = line[3:].strip()
                out.append(f'<pre class="docs-pre" data-lang="{html.escape(code_lang)}"><code>')
            else:
                in_code = False
                out.append("</code></pre>")
            continue
        if in_code:
            out.append(html.escape(line) + "\n")
            continue

        if "|" in line and line.strip().startswith("|"):
            close_lists()
            cells = [c.strip() for c in line.strip().strip("|").split("|")]
            table_rows.append(cells)
            in_table = True
            continue
        if in_table:
            flush_table()

        if not line.strip():
            close_lists()
            continue

        img_only = re.fullmatch(r"!\[([^\]]*)\]\(([^)]+)\)", line.strip())
        if img_only:
            close_lists()
            alt = html.escape(img_only.group(1))
            src = html.escape(_doc_img_src(img_only.group(2)))
            out.append(
                f'<figure class="docs-figure"><img class="docs-img" src="{src}" alt="{alt}" '
                f'loading="lazy" />'
                + (f"<figcaption>{alt}</figcaption>" if img_only.group(1) else "")
                + "</figure>"
            )
            continue

        h = re.match(r"^(#{1,4})\s+(.*)$", line)
        if h:
            close_lists()
            level = len(h.group(1))
            out.append(f"<h{level}>{_inline(h.group(2))}</h{level}>")
            continue

        if re.match(r"^[-*]\s+", line):
            if in_ol:
                out.append("</ol>")
                in_ol = False
            if not in_ul:
                out.append("<ul>")
                in_ul = True
            out.append(f"<li>{_inline(re.sub(r'^[-*]\\s+', '', line))}</li>")
            continue

        if re.match(r"^\d+\.\s+", line):
            if in_ul:
                out.append("</ul>")
                in_ul = False
            if not in_ol:
                out.append("<ol>")
                in_ol = True
            out.append(f"<li>{_inline(re.sub(r'^\\d+\\.\\s+', '', line))}</li>")
            continue

        close_lists()
        out.append(f"<p>{_inline(line)}</p>")

    close_lists()
    flush_table()
    if in_code:
        out.append("</code></pre>")
    return "\n".join(out)


def list_docs() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for doc_id, meta in _BUILTIN.items():
        rows.append(
            {
                "id": doc_id,
                "title": meta["title"],
                "group": meta["group"],
                "source": "builtin",
            }
        )
    for doc_id, title, group, path in _FILE_DOCS:
        rows.append(
            {
                "id": doc_id,
                "title": title,
                "group": group,
                "source": "file",
                "exists": path.is_file(),
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
            }
        )
    return rows


def get_doc(doc_id: str) -> Optional[dict[str, Any]]:
    key = (doc_id or "").strip().lower()
    if key in _BUILTIN:
        meta = _BUILTIN[key]
        return {
            "id": key,
            "title": meta["title"],
            "group": meta["group"],
            "source": "builtin",
            "markdown": meta["body"],
            "html": _md_to_html(meta["body"]),
        }
    for fid, title, group, path in _FILE_DOCS:
        if fid == key:
            if not path.is_file():
                return {
                    "id": fid,
                    "title": title,
                    "group": group,
                    "source": "file",
                    "missing": True,
                    "markdown": f"# Missing\n\n`{path.name}` was not found in the repo.",
                    "html": f"<p class='muted'>File not found: <code>{html.escape(path.name)}</code></p>",
                }
            text = path.read_text(encoding="utf-8", errors="replace")
            return {
                "id": fid,
                "title": title,
                "group": group,
                "source": "file",
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "markdown": text,
                "html": _md_to_html(text),
            }
    return None

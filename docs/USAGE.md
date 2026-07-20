# Using Infobroker — tour, desk, and Grapevine

This guide is for after you have the desk running. Setup lives in the [root README](../README.md). Here: **what to do first**, how each major surface works, and how to get the most out of the assistant.

---

## First thing after you start the desk

1. Open **http://127.0.0.1:8000/**
2. Click **Tour** in the top bar (or **Tour** in the Grapevine sidebar)

The guided tour walks the Markets board, Trading, Portfolio, Learning, Strategies, Chart Studio, Services, Settings, and Grapevine. It is the fastest way to learn where things live. Re-run it anytime — nothing is locked after you finish.

**Do not skip the tour on a first run.** Reading this page helps; clicking through the UI once with Tour is what sticks.

---

## Desk at a glance

### Markets — live board and universe

![Infobroker Markets tab](images/desk-markets.png)

- **Live** — tiles / heat / movers over the quoted universe  
- World clocks (NY, LDN, FRA, TYO, HK, SYD) — foreign sessions open **proxy boards** (US-listed ETFs/ADRs)  
- **Universe** — listings + quote fill; movers and scanner prefer cached quotes  
- Header chips show broker, data provider, paper/sim mode, and the Ollama model  

**Insight:** When the US badge says closed, last prices still appear from the universe cache (`as_of` on each quote). Closed session ≠ empty board.

### Trading — bid / ask board

![Infobroker Trading tab](images/desk-trading.png)

- Watchlist + liquid names with bid / ask / last / day %  
- Account strip: cash, equity, buying power, positions  
- One-click paper buy/sell with risk preview before submit  

**Insight:** Stay on **paper** until you understand the order ticket and risk checklist. Live brokers are opt-in via env / API Keys.

### Chart studio — price, volume, RSI, MACD

![Infobroker Chart studio](images/desk-charts.png)

![Infobroker chart indicators](images/desk-charts-indicators.png)

Load a ticker + date range → **Load all charts**. Hover for OHLC, drag to zoom, draw trend / H-lines on the price panel.

### Guided tour overlay

![Infobroker guided tour](images/desk-tour.png)

- Spotlight + step card (Back / Next / Done)  
- ~26 steps covering the whole desk  
- Finish lands you ready for Learning → Tutor or a watchlist + Scan  

### Grapevine — desk coach

![Infobroker Grapevine sidebar](images/desk-grapevine.png)

- Chat + follow-up chips, Find trades / Send view / LLM warm  
- Action stream shows tool calls  
- Coach can point at widgets (manual Next — kept light so the UI stays responsive)  

---

## Recommended first session (15 minutes)

| Step | Action | Why |
|------|--------|-----|
| 1 | Click **Tour** and finish it | Mental map of every tab |
| 2 | Confirm header shows `broker: paper` and a data provider | Safe defaults |
| 3 | Add 2–3 tickers to the watchlist | Personal board |
| 4 | **Refresh** once; open **Markets → Movers** | See cache-backed quotes |
| 5 | Ask Grapevine: “Show my watchlist prices” or use a chip | Fast path works even without a warm LLM |
| 6 | Open **Learning → Tutor** | Skill path after the tour |

Optional next: **Scan** / Grapevine **Find trades**, then paper a small size with stop preview.

---

## Model: Grapevine (strongly recommended)

Infobroker’s assistant was designed around **Arriella Grapevine** on local Ollama:

```bash
ollama pull arriella-grapevine
# optional pin in .env:
# INFOBROKER_OLLAMA_MODEL=arriella-grapevine:latest
```

Grapevine is tuned for this desk: short reductive answers, tool use, teaching overlays, and vision-friendly “send view” coaching. **It is highly advised to use Grapevine** for the full experience.

### If you use another model

Any substitute must be capable of **all** of the following (not just chat):

| Capability | Why the desk needs it |
|------------|------------------------|
| **Chat completion** | Multi-turn coach in the sidebar |
| **Image summary** | Understand a captured panel (“Send view”) |
| **Image → text** | Read labels, tables, and board text from screenshots |
| **Thinking** | Multi-step tool plans (hunt → quote → explain) without hallucinating fills |
| **Reductive output** | Short, desk-usable replies — not essay dumps that bury the action |

Set the model with `INFOBROKER_OLLAMA_MODEL` (or the desk Services controls). If the model cannot do vision, leave **Send view** unused and stick to text + tools. If it cannot stay reductive, answers will feel noisy next to the fast-path chips.

**Without Ollama at all:** the desk still runs. Price / open-closed / gainers / cash style questions use the **fast path** (no LLM). Tool-heavy coaching and vision need a capable model.

---

## Tab-by-tab usage notes

### Markets

- Prefer **quoted** universe rows for movers and scanner — fill quotes if the board looks thin  
- Foreign clocks are educational proxies, not full foreign exchanges  
- Auto-refresh (header) is enough for most sessions; avoid spam-clicking Yahoo-heavy actions  

### Trading & Portfolio

- Preview risk before every non-trivial order  
- Portfolio shows equity, positions, orders, unrealized P&L  
- Auto-track can add day gainers to the watchlist — useful, but prune noise  

### Learning

- Tutor path after Tour  
- Journal + skill lessons reinforce chart/risk habits  

### Strategies & Chart Studio

- Free yfinance backtests and OHLC packs  
- Teaching signals (RSI/MA/MACD) — not a live signal service  

### Services & keys / Settings

- Warm Ollama, restart MCP, manage keys locally  
- **Settings → Docs** mirrors this repo’s technical pages  
- Donate / About live under Settings  

---

## Grapevine habits that work well

**Good prompts**

- “Is the market open?”  
- “Show top gainers” / “Show my watchlist prices”  
- “How do I trade on this desk?”  
- “Hunt for opportunities on the liquid board”  
- After **Send view**: “What am I looking at and what should I click next?”  

**Insights**

- Fast-path answers for prices do **not** require the LLM — trust the chips when Ollama is cold  
- Hunt/scan is cached and light; do not expect a full-universe AI sweep every few seconds  
- Paper tools refuse live fills from the assistant path — intentional safety  

---

## Closed market reality check

| You see | Meaning |
|---------|---------|
| US closed (red) | Cash session off; clocks still show other venues |
| Last / bid / ask still filled | Universe cache + delayed/last prints |
| Grapevine “can’t see prices” | Should be rare — ask for watchlist prices or use `get_prices` path |

Details: [DATA.md](DATA.md), [RATE_LIMITS.md](RATE_LIMITS.md).

---

## Safety reminders

- Default broker is **paper**  
- Never commit `.env`, ledgers, or `users.json`  
- Public.com Individual API is **live** — practice in paper first  
- Grapevine is a coach, not a broker or fiduciary  

---

## Related docs

| Doc | Topic |
|-----|--------|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Stack diagrams |
| [DATA.md](DATA.md) | Quote cascade & universe |
| [MCP.md](MCP.md) | Assistant + Cursor MCP |
| [BROKERS.md](BROKERS.md) | Execution & data providers |
| [../README.md](../README.md) | Clone, setup scripts, feature list |

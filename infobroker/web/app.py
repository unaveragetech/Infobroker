"""Infobroker technical dashboard API + static UI."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from infobroker.brokers import (
    OrderRequest,
    OrderSide,
    OrderType,
    create_broker,
    ranked_free_brokers,
)
from infobroker.brokers.base import BrokerError
from infobroker.brokers.paper import PaperBroker
from infobroker.config import get_settings
from infobroker.data import fetch_ohlcv, get_fundamentals, get_stock_quote
from infobroker.data.chartpack import build_chart_pack
from infobroker.data.highlights import get_market_highlights, get_tracked_quotes, sparkline_closes
from infobroker.data.multisource import build_live_board, provider_status
from infobroker.data.yf_pipeline import analyze_symbol
from infobroker.education import get_lesson, list_lessons
from infobroker.education.trade_stories import build_trade_stories, sample_demo_stories
from infobroker.education.tutor import get_tutor, list_tutor_summary
from infobroker.risk import evaluate_order, teaching_checklist
from infobroker.settings_store import get_public_settings, update_settings
from infobroker.assistant.agent import hunt_once, run_assistant
from infobroker.assistant.ollama_client import ollama_healthy
from infobroker.assistant.tools import KEY_LINKS, execute_tool, list_actions
from infobroker.services.process_control import (
    mcp_restart,
    mcp_start,
    mcp_status,
    mcp_stop,
    ollama_control,
)
from infobroker.strategies import list_strategies, run_backtest, run_strategy_backtest, scan_watchlist
from infobroker.auto_track import (
    get_auto_track_settings,
    scan_and_track,
    start_auto_track_worker,
    stop_auto_track_worker,
    update_auto_track_settings,
)
from infobroker.portfolio import build_portfolio
from infobroker.trading_board import build_trading_board
from infobroker.markets import (
    build_market_board,
    fetch_intraday_bars,
    fetch_live_tick,
    list_market_focuses,
    market_clocks,
)
from infobroker.universe import (
    ensure_universe,
    get_symbol as universe_get_symbol,
    liquid_scan_symbols,
    list_universe,
    movers as universe_movers,
    refresh_listings,
    refresh_quotes,
    start_background_engine,
    stop_background_engine,
    universe_status,
)
from infobroker.watchlist import add_symbol, get_watchlist, list_symbols, remove_symbol, validate_symbol

STATIC_DIR = Path(__file__).resolve().parent / "static"

_LOCAL_HOSTS = {"127.0.0.1", "::1", "localhost", "testclient"}


def _require_localhost(request: Request) -> None:
    """Keep key management off the LAN — desk is meant for local use."""
    client = (request.client.host if request.client else "") or ""
    if client not in _LOCAL_HOSTS:
        raise HTTPException(
            403,
            "Settings and key updates are only allowed from localhost.",
        )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    # Market-wide listings + rotating quote refresh (not watchlist-only)
    try:
        await asyncio.to_thread(ensure_universe, False)
    except Exception:
        pass
    start_background_engine()
    start_auto_track_worker()
    yield
    stop_auto_track_worker()
    stop_background_engine()


app = FastAPI(title="Infobroker", version="0.8.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class OrderBody(BaseModel):
    symbol: str
    side: str = "buy"
    qty: float = Field(gt=0)
    order_type: str = "market"
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None  # protective stop / stop entry
    take_profit: Optional[float] = None
    user: str = "default"


class WatchBody(BaseModel):
    symbol: str
    note: str = ""


class AutoTrackBody(BaseModel):
    enabled: Optional[bool] = None
    min_change_pct: Optional[float] = None
    exchanges: Optional[Any] = None
    asset_classes: Optional[Any] = None
    max_adds_per_scan: Optional[int] = None
    poll_sec: Optional[int] = None
    include_etf: Optional[bool] = None


class SettingsBody(BaseModel):
    broker: Optional[str] = None
    data_provider: Optional[str] = None
    starting_cash: Optional[float] = None
    alpaca_paper: Optional[bool] = None
    tradier_sandbox: Optional[bool] = None
    alpaca_api_key: Optional[str] = None
    alpaca_api_secret: Optional[str] = None
    public_personal_secret: Optional[str] = None
    public_account_id: Optional[str] = None
    tradier_access_token: Optional[str] = None
    tradier_account_id: Optional[str] = None
    finnhub_api_key: Optional[str] = None
    alphavantage_api_key: Optional[str] = None


class AssistantChatBody(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    image_b64: Optional[str] = None  # raw base64, no data: prefix required
    history: Optional[list[dict[str, str]]] = None
    ui_context: Optional[dict[str, Any]] = None


class AssistantHuntBody(BaseModel):
    ui_context: Optional[dict[str, Any]] = None


class ToolCallBody(BaseModel):
    tool: str
    args: dict[str, Any] = Field(default_factory=dict)


class OllamaControlBody(BaseModel):
    action: str = "status"


class StrategyBacktestBody(BaseModel):
    strategy: str = "sma_crossover"
    symbol: str
    start: str
    end: str
    starting_cash: float = 10_000.0


class ChartPackBody(BaseModel):
    symbol: str
    start: str
    end: str


def _is_live() -> bool:
    settings = get_settings()
    if settings.broker == "paper":
        return False
    if settings.broker == "alpaca" and settings.alpaca_paper:
        return False
    if settings.broker == "tradier" and settings.tradier_sandbox:
        return False
    return True


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
async def health():
    settings = get_settings()
    ollama, mcp = await asyncio.gather(
        asyncio.to_thread(ollama_healthy),
        asyncio.to_thread(mcp_status),
    )
    stack = {}
    try:
        import pandas as pd
        import talib
        import yfinance as yf

        stack = {
            "yfinance": getattr(yf, "__version__", "ok"),
            "pandas": pd.__version__,
            "TA-Lib": getattr(talib, "__version__", "ok"),
        }
    except Exception as exc:  # noqa: BLE001
        stack = {"error": str(exc)}
    return {
        "ok": True,
        "broker": settings.broker,
        "data": settings.data_provider,
        "live": _is_live(),
        "version": "0.8.0",
        "market_stack": stack,
        "providers": provider_status(),
        "ollama": ollama,
        "mcp": mcp,
    }


@app.get("/api/key-links")
def key_links():
    return {"providers": KEY_LINKS}


@app.get("/api/services/mcp")
def services_mcp_get():
    return mcp_status()


@app.post("/api/services/mcp/{action}")
def services_mcp_post(action: str):
    act = action.strip().lower()
    if act == "start":
        return mcp_start()
    if act == "stop":
        return mcp_stop()
    if act == "restart":
        return mcp_restart()
    if act == "status":
        return mcp_status()
    raise HTTPException(400, f"Unknown MCP action: {action}")


@app.post("/api/services/ollama")
def services_ollama(body: OllamaControlBody):
    return ollama_control(body.action)


@app.get("/api/strategies")
def strategies_list():
    return {"strategies": list_strategies(), "engine": "yfinance (free, no signup)"}


@app.post("/api/strategies/backtest")
async def strategies_backtest(body: StrategyBacktestBody):
    try:
        sym = validate_symbol(body.symbol)
        return await asyncio.to_thread(
            run_strategy_backtest,
            body.strategy,
            sym,
            body.start,
            body.end,
            body.starting_cash,
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/charts/pack")
async def charts_pack(body: ChartPackBody):
    try:
        sym = validate_symbol(body.symbol)
        return await asyncio.to_thread(build_chart_pack, sym, body.start, body.end)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


class AnalyzeBody(BaseModel):
    symbol: str
    start: Optional[str] = None
    end: Optional[str] = None
    period: str = "1y"


@app.post("/api/analyze")
async def analyze(body: AnalyzeBody):
    """yfinance download → Pandas frame → TA-Lib indicators."""
    try:
        sym = validate_symbol(body.symbol)
        if body.start and body.end:
            return await asyncio.to_thread(
                analyze_symbol, sym, start=body.start, end=body.end
            )
        return await asyncio.to_thread(analyze_symbol, sym, period=body.period)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/assistant/actions")
def assistant_actions(limit: int = 40):
    return {"actions": list_actions(limit)}


@app.post("/api/assistant/chat")
async def assistant_chat(body: AssistantChatBody):
    """Run Grapevine off the event loop so live board / clocks stay responsive."""
    try:
        return await asyncio.to_thread(
            run_assistant,
            body.message.strip(),
            image_b64=body.image_b64,
            history=body.history,
            ui_context=body.ui_context,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Assistant failed: {exc}") from exc


@app.post("/api/assistant/hunt")
async def assistant_hunt(body: Optional[AssistantHuntBody] = None):
    try:
        ctx = body.ui_context if body else None
        return await asyncio.to_thread(hunt_once, ctx)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Hunt failed: {exc}") from exc

@app.post("/api/assistant/tool")
def assistant_tool(body: ToolCallBody):
    from dataclasses import asdict

    event = execute_tool(body.tool, body.args or {})
    payload = asdict(event)
    if not event.ok:
        raise HTTPException(400, detail=payload)
    return payload


@app.get("/api/brokers")
def brokers():
    return [
        {
            "id": p.id,
            "name": p.name,
            "rank": p.rank,
            "speed": p.speed_score,
            "reliability": p.reliability_score,
            "cost": p.cost_note,
            "notes": p.notes,
        }
        for p in ranked_free_brokers()
    ]


@app.get("/api/settings")
def settings_get(request: Request):
    _require_localhost(request)
    return get_public_settings()


@app.put("/api/settings")
def settings_put(request: Request, body: SettingsBody):
    _require_localhost(request)
    try:
        return update_settings(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Failed to save settings: {exc}") from exc


@app.get("/api/docs")
def api_docs_list():
    """Project documentation catalog for Settings → Docs."""
    from infobroker.docs_catalog import list_docs

    return {"docs": list_docs()}


@app.get("/api/docs/{doc_id}")
def api_docs_get(doc_id: str):
    from infobroker.docs_catalog import get_doc

    doc = get_doc(doc_id)
    if not doc:
        raise HTTPException(404, f"Unknown doc: {doc_id}")
    return doc


@app.get("/api/watchlist")
def watchlist_get():
    return get_watchlist()


@app.post("/api/watchlist")
def watchlist_add(body: WatchBody):
    try:
        symbols = add_symbol(body.symbol, body.note)
        return {"symbols": symbols}
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc


@app.delete("/api/watchlist/{symbol}")
def watchlist_remove(symbol: str):
    return {"symbols": remove_symbol(symbol)}


@app.get("/api/tracked")
async def tracked():
    try:
        items = await asyncio.to_thread(get_tracked_quotes)
        return {"items": items}
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Failed to load tracked quotes: {exc}") from exc


@app.get("/api/highlights")
async def highlights():
    try:
        return await asyncio.to_thread(get_market_highlights)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Failed to load highlights: {exc}") from exc


@app.get("/api/markets/clocks")
def api_market_clocks():
    """World market clocks + open/closed (local session rules, no API key)."""
    data = market_clocks()
    data["focuses"] = list_market_focuses()
    return data


@app.get("/api/markets/board")
def api_markets_board(
    focus: str = Query("us", description="us|nasdaq|nyse|arca|amex|london|frankfurt|tokyo|hongkong|sydney"),
    limit: int = Query(180, ge=10, le=2000),
    sort: str = Query("volume"),
):
    """Switchable Live board: US venue filter or foreign session proxy list."""
    try:
        return build_market_board(focus=focus, limit=limit, sort=sort)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Market board failed: {exc}") from exc


@app.get("/api/tick/{symbol}")
def api_tick(symbol: str, force: bool = False):
    """Lightweight last-price tick (throttled server-side ~1s when US open)."""
    try:
        sym = validate_symbol(symbol)
        return fetch_live_tick(sym, force=force)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Tick failed: {exc}") from exc


@app.get("/api/ohlc/{symbol}/intraday")
def api_ohlc_intraday(
    symbol: str,
    interval: str = Query("1m", description="1m|5m|15m|30m|60m"),
    range: str = Query("1d", description="1d|5d|1mo", alias="range"),
):
    """Intraday bars for near-realtime Live charting."""
    try:
        sym = validate_symbol(symbol)
        return fetch_intraday_bars(sym, interval=interval, range_=range)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Intraday failed: {exc}") from exc


@app.get("/api/stream/tick/{symbol}")
async def api_stream_tick(symbol: str):
    """SSE tick stream for one focused symbol — server caches so clients share load."""
    try:
        sym = validate_symbol(symbol)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc

    async def events():
        # Cap stream lifetime so abandoned tabs don't run forever
        for _ in range(900):  # ~15–30 min depending on poll
            try:
                tick = await asyncio.to_thread(fetch_live_tick, sym, False)
            except Exception as exc:  # noqa: BLE001
                tick = {"ok": False, "symbol": sym, "error": str(exc)[:160]}
            yield f"data: {json.dumps(tick)}\n\n"
            wait = float(tick.get("poll_sec") or 1.0) if isinstance(tick, dict) else 1.0
            wait = max(0.75, min(wait, 20.0))
            await asyncio.sleep(wait)

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/quote/{symbol}")
def quote(symbol: str):
    try:
        sym = validate_symbol(symbol)
        data = get_stock_quote(sym)
        data["symbol"] = sym
        try:
            data["sparkline"] = sparkline_closes(sym, 30)
        except Exception:
            data["sparkline"] = []
        return data
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/fundamentals/{symbol}")
def fundamentals(symbol: str):
    try:
        sym = validate_symbol(symbol)
        return get_fundamentals(sym)
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/account")
def account(user: str = "default"):
    try:
        broker = create_broker(user=user)
        acct = broker.get_account()
        positions = broker.list_positions()
        return {
            "broker": broker.profile.id,
            "broker_name": broker.profile.name,
            "cash": acct.cash,
            "equity": acct.equity,
            "buying_power": acct.buying_power,
            "live": _is_live(),
            "supports_stop_processing": isinstance(broker, PaperBroker),
            "positions": [
                {
                    "symbol": p.symbol,
                    "qty": p.qty,
                    "avg_entry": p.avg_entry,
                    "market_value": p.market_value,
                    "unrealized_pl": p.unrealized_pl,
                }
                for p in positions
            ],
        }
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/portfolio")
def api_portfolio(user: str = "default", order_limit: int = Query(80, ge=10, le=200)):
    try:
        return build_portfolio(user=user, order_limit=order_limit)
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, f"Portfolio failed: {exc}") from exc


@app.get("/api/trading/board")
def api_trading_board(
    scope: str = Query("both", description="watchlist|live|both"),
    limit: int = Query(120, ge=10, le=400),
    user: str = "default",
):
    """Trading desk: bid/ask/last for watchlist + live universe with position qty."""
    try:
        return build_trading_board(scope=scope, limit=limit, user=user)
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Trading board failed: {exc}") from exc


@app.get("/api/auto-track")
def api_auto_track_get():
    return get_auto_track_settings()


@app.put("/api/auto-track")
def api_auto_track_put(body: AutoTrackBody):
    try:
        return update_auto_track_settings(body.model_dump(exclude_unset=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/auto-track/scan")
async def api_auto_track_scan(force: bool = True):
    try:
        return await asyncio.to_thread(scan_and_track, force)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Auto-track scan failed: {exc}") from exc


@app.get("/api/orders")
def orders(user: str = "default", status: Optional[str] = None, limit: int = 40):
    try:
        broker = create_broker(user=user)
        rows = broker.list_orders(status=status)
        # Newest first when timestamps exist
        rows = list(reversed(rows))[: max(1, min(limit, 200))]
        return {
            "orders": [
                {
                    "id": o.id,
                    "symbol": o.symbol,
                    "side": o.side.value,
                    "qty": o.qty,
                    "order_type": o.order_type.value,
                    "status": o.status.value,
                    "filled_qty": o.filled_qty,
                    "filled_avg_price": o.filled_avg_price,
                    "limit_price": o.limit_price,
                    "stop_price": o.stop_price,
                    "submitted_at": o.submitted_at,
                }
                for o in rows
            ]
        }
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.delete("/api/orders/{order_id}")
def cancel_order(order_id: str, user: str = "default"):
    try:
        broker = create_broker(user=user)
        order = broker.cancel_order(order_id)
        return {"id": order.id, "status": order.status.value}
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/orders/process-stops")
def process_stops(user: str = "default"):
    try:
        broker = create_broker(user=user)
        if not isinstance(broker, PaperBroker):
            raise HTTPException(
                400,
                "Stop processing endpoint is for the local paper broker. "
                "Live brokers manage stops server-side.",
            )
        filled = broker.process_open_stops()
        return {
            "triggered": len(filled),
            "orders": [
                {
                    "id": o.id,
                    "symbol": o.symbol,
                    "side": o.side.value,
                    "status": o.status.value,
                    "filled_avg_price": o.filled_avg_price,
                }
                for o in filled
            ],
        }
    except HTTPException:
        raise
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/scan")
def scan(
    scope: str = Query("universe", description="universe | watchlist"),
    limit: int = Query(120, ge=10, le=300),
):
    try:
        scope_n = (scope or "universe").strip().lower()
        if scope_n == "watchlist":
            return scan_watchlist()
        syms = liquid_scan_symbols(limit)
        result = scan_watchlist(symbols=syms)
        result["scope"] = "universe"
        result["universe_pool"] = len(syms)
        return result
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Scan failed: {exc}") from exc


@app.get("/api/universe/status")
def api_universe_status():
    try:
        return universe_status()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/universe")
def api_universe(
    q: str = "",
    exchange: str = "",
    asset_class: str = "",
    etf: Optional[bool] = None,
    has_quote: Optional[bool] = None,
    limit: int = Query(80, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        return list_universe(
            q=q,
            exchange=exchange,
            asset_class=asset_class,
            etf=etf,
            has_quote=has_quote,
            limit=limit,
            offset=offset,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.get("/api/universe/movers")
def api_universe_movers(limit: int = Query(15, ge=3, le=50)):
    try:
        return universe_movers(limit=limit)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, str(exc)) from exc


@app.get("/api/universe/{symbol}")
def api_universe_symbol(symbol: str):
    try:
        row = universe_get_symbol(symbol)
        if not row:
            raise HTTPException(404, f"Symbol not in universe: {symbol}")
        return row
    except HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(500, str(exc)) from exc


@app.post("/api/universe/refresh-listings")
async def api_universe_refresh_listings(force: bool = True):
    try:
        return await asyncio.to_thread(refresh_listings, force)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Listings refresh failed: {exc}") from exc


@app.post("/api/universe/refresh-quotes")
async def api_universe_refresh_quotes(batch: int = Query(160, ge=10, le=400)):
    try:
        return await asyncio.to_thread(refresh_quotes, batch)
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Quote refresh failed: {exc}") from exc


@app.get("/api/live")
async def api_live(
    mode: str = Query("universe"),
    asset_class: str = "",
    limit: int = Query(0, ge=0, le=20000, description="0 = all quoted symbols"),
    enrich: bool = Query(True),
    sort: str = Query("abs_change", description="abs_change|change_desc|change_asc|volume|rel_volume|price|symbol|week"),
    exchange: str = Query("", description="Filter by exchange substring, e.g. NASDAQ"),
):
    """Finviz-style live board with multi-source enrich + Finnhub news when keyed."""
    try:
        return await asyncio.to_thread(
            build_live_board, mode, asset_class, limit, enrich, sort, exchange
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(502, f"Live board failed: {exc}") from exc


@app.get("/api/providers")
def api_providers():
    """Configured data sources (booleans only — no secret values)."""
    return {"providers": provider_status()}


@app.get("/api/ohlc/{symbol}")
def ohlc(symbol: str, days: int = 90):
    try:
        from datetime import datetime, timedelta

        sym = validate_symbol(symbol)
        days = max(10, min(int(days), 400))
        end = datetime.utcnow().date()
        start = end - timedelta(days=days + 20)
        df = fetch_ohlcv(sym, start.isoformat(), end.isoformat())
        if df is None or df.empty:
            raise HTTPException(404, f"No OHLC data for {sym}")

        rename = {c: str(c).lower() for c in df.columns}
        frame = df.rename(columns=rename)
        for needed in ("open", "high", "low", "close"):
            if needed not in frame.columns:
                raise HTTPException(502, f"OHLC missing column: {needed}")

        out: list[dict[str, Any]] = []
        for ts, row in frame.tail(days).iterrows():
            try:
                out.append(
                    {
                        "t": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                        "o": float(row["open"]),
                        "h": float(row["high"]),
                        "l": float(row["low"]),
                        "c": float(row["close"]),
                        "v": float(row["volume"]) if "volume" in frame.columns else 0.0,
                    }
                )
            except Exception:
                continue
        return {"symbol": sym, "bars": out}
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/lessons")
def lessons():
    rows = list_lessons()
    tutor = list_tutor_summary()
    return {"lessons": rows, "tutor": tutor}


@app.get("/api/lessons/{lesson_id}")
def lesson_detail(lesson_id: str):
    lesson = get_lesson(lesson_id)
    if not lesson:
        raise HTTPException(404, f"Unknown lesson: {lesson_id}")
    return lesson


@app.get("/api/learn/tutor")
def learn_tutor():
    return get_tutor()


@app.get("/api/learn/trade-stories")
def learn_trade_stories(limit: int = 40, include_demo: bool = True):
    data = build_trade_stories(limit=limit)
    if not data["stories"] and include_demo:
        data["stories"] = sample_demo_stories()
        data["summary"]["demo"] = True
        data["summary"]["message"] = (
            "No real orders yet — showing annotated demo trades. "
            "Place a paper order to replace these with your history."
        )
    return data


@app.get("/api/backtest/{symbol}")
async def backtest(symbol: str, start: str, end: str, strategy: str = "sma_crossover"):
    try:
        sym = validate_symbol(symbol)
        return await asyncio.to_thread(
            run_strategy_backtest, strategy, sym, start, end, 10_000.0
        )
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


def _parse_order_type(raw: str) -> OrderType:
    key = (raw or "market").strip().lower().replace("-", "_")
    mapping = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
        "stop_limit": OrderType.STOP_LIMIT,
        "stoplimit": OrderType.STOP_LIMIT,
    }
    if key not in mapping:
        raise HTTPException(400, f"Unsupported order_type: {raw}")
    return mapping[key]


@app.post("/api/orders/preview")
def preview_order(body: OrderBody):
    try:
        sym = validate_symbol(body.symbol)
        if body.qty <= 0:
            raise HTTPException(400, "Quantity must be positive")
        broker = create_broker(user=body.user)
        side = OrderSide.BUY if body.side.lower().startswith("b") else OrderSide.SELL
        otype = _parse_order_type(body.order_type)
        if otype == OrderType.LIMIT and body.limit_price is None:
            raise HTTPException(400, "limit_price required for limit orders")
        if otype in {OrderType.STOP, OrderType.STOP_LIMIT} and body.stop_price is None:
            raise HTTPException(400, "stop_price required for stop orders")
        q = broker.get_quote(sym)
        # Protective stop for risk (bracket) vs stop entry price
        protective = body.stop_price if otype == OrderType.MARKET else None
        req = OrderRequest(
            symbol=sym,
            side=side,
            qty=body.qty,
            order_type=otype,
            limit_price=body.limit_price,
            stop_price=body.stop_price,
        )
        verdict = evaluate_order(
            req,
            broker.get_account(),
            broker.list_positions(),
            q.last,
            stop_price=protective or body.stop_price,
            is_live=_is_live(),
        )
        return {
            "allowed": verdict.allowed,
            "warnings": verdict.warnings,
            "blockers": verdict.blockers,
            "checklist": teaching_checklist(sym, body.side),
            "last": q.last,
            "live": _is_live(),
            "order_type": otype.value,
        }
    except HTTPException:
        raise
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/orders")
def place_order(body: OrderBody):
    preview = preview_order(body)
    if not preview["allowed"]:
        raise HTTPException(400, detail=preview)
    try:
        sym = validate_symbol(body.symbol)
        broker = create_broker(user=body.user)
        side = OrderSide.BUY if body.side.lower().startswith("b") else OrderSide.SELL
        otype = _parse_order_type(body.order_type)
        # Market + protective stop/TP → bracket
        if otype == OrderType.MARKET and (body.stop_price or body.take_profit):
            orders = broker.place_bracket(
                sym,
                side,
                body.qty,
                take_profit=body.take_profit,
                stop_loss=body.stop_price,
            )
            return [
                {
                    "id": o.id,
                    "status": o.status.value,
                    "side": o.side.value,
                    "type": o.order_type.value,
                }
                for o in orders
            ]
        order = broker.place_order(
            OrderRequest(
                symbol=sym,
                side=side,
                qty=body.qty,
                order_type=otype,
                limit_price=body.limit_price,
                stop_price=body.stop_price,
            )
        )
        return {
            "id": order.id,
            "status": order.status.value,
            "fill": order.filled_avg_price,
            "side": order.side.value,
            "type": order.order_type.value,
        }
    except HTTPException:
        raise
    except BrokerError as exc:
        raise HTTPException(400, str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(400, str(exc)) from exc


# Backward-compatible aliases used by older stubs
@app.get("/health")
def health_legacy():
    return health()


@app.get("/brokers")
def brokers_legacy():
    return brokers()


def run() -> None:
    import uvicorn

    settings = get_settings()
    # Ensure default watchlist exists
    list_symbols()
    uvicorn.run(
        "infobroker.web.app:app",
        host=settings.web_host,
        port=settings.web_port,
        reload=False,
    )


if __name__ == "__main__":
    run()

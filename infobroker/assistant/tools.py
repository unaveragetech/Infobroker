"""Programmatic dashboard tools — shared by Grapevine agent and MCP server."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional
from uuid import uuid4

from infobroker.brokers import OrderRequest, OrderSide, OrderType, create_broker
from infobroker.brokers.base import BrokerError
from infobroker.brokers.paper import PaperBroker
from infobroker.config import get_settings
from infobroker.data.highlights import get_market_highlights, get_tracked_quotes
from infobroker.risk import evaluate_order
from infobroker.settings_store import get_public_settings
from infobroker.data.chartpack import build_chart_pack
from infobroker.data.market import get_fundamentals, get_stock_quote
from infobroker.data.yf_pipeline import analyze_symbol
from infobroker.services.process_control import (
    mcp_restart,
    mcp_start,
    mcp_status,
    mcp_stop,
    ollama_control,
)
from infobroker.strategies import list_strategies, run_backtest, run_strategy_backtest, scan_watchlist
from infobroker.watchlist import add_symbol, get_watchlist, list_symbols, remove_symbol, validate_symbol

KEY_LINKS = {
    "alpaca": {
        "label": "Alpaca",
        "signup": "https://app.alpaca.markets/signup",
        "keys": "https://app.alpaca.markets/paper/dashboard/overview",
        "docs": "https://docs.alpaca.markets/",
    },
    "public": {
        "label": "Public",
        "signup": "https://public.com/",
        "keys": "https://public.com/settings",
        "docs": "https://public.com/api/docs",
    },
    "tradier": {
        "label": "Tradier",
        "signup": "https://developer.tradier.com/",
        "keys": "https://developer.tradier.com/user/sign_up",
        "docs": "https://documentation.tradier.com/",
    },
    "finnhub": {
        "label": "Finnhub",
        "signup": "https://finnhub.io/register",
        "keys": "https://finnhub.io/dashboard",
        "docs": "https://finnhub.io/docs/api",
    },
    "alphavantage": {
        "label": "Alpha Vantage",
        "signup": "https://www.alphavantage.co/support/#api-key",
        "keys": "https://www.alphavantage.co/support/#api-key",
        "docs": "https://www.alphavantage.co/documentation/",
    },
}


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict[str, Any]
    handler: Callable[..., Any]
    mutates: bool = False


@dataclass
class ActionEvent:
    id: str
    tool: str
    args: dict[str, Any]
    ok: bool
    summary: str
    result: Any = None
    error: Optional[str] = None
    at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


_ACTION_LOG: list[ActionEvent] = []
_MAX_LOG = 80
_IDEAS_CACHE: dict[str, Any] = {"at": 0.0, "data": None}
_IDEAS_TTL = 180.0  # seconds


def list_actions(limit: int = 40) -> list[dict[str, Any]]:
    rows = list(reversed(_ACTION_LOG))[: max(1, min(limit, _MAX_LOG))]
    return [asdict(r) for r in rows]


def _log(event: ActionEvent) -> ActionEvent:
    _ACTION_LOG.append(event)
    if len(_ACTION_LOG) > _MAX_LOG:
        del _ACTION_LOG[: len(_ACTION_LOG) - _MAX_LOG]
    return event


def _is_live() -> bool:
    s = get_settings()
    if s.broker == "paper":
        return False
    if s.broker == "alpaca" and s.alpaca_paper:
        return False
    if s.broker == "tradier" and s.tradier_sandbox:
        return False
    return True


def tool_get_desk_state() -> dict[str, Any]:
    settings = get_settings()
    pub = get_public_settings()
    missing = []
    optional = []
    secrets = pub.get("secrets") or {}
    if settings.broker == "alpaca" and not secrets.get("ALPACA_API_KEY", {}).get("configured"):
        missing.append({"provider": "alpaca", **KEY_LINKS["alpaca"]})
    if settings.broker == "public" and not secrets.get("PUBLIC_PERSONAL_SECRET", {}).get("configured"):
        missing.append({"provider": "public", **KEY_LINKS["public"]})
    if settings.broker == "tradier" and not secrets.get("TRADIER_ACCESS_TOKEN", {}).get("configured"):
        missing.append({"provider": "tradier", **KEY_LINKS["tradier"]})
    if not secrets.get("FINNHUB_API_KEY", {}).get("configured"):
        entry = {"provider": "finnhub", **KEY_LINKS["finnhub"]}
        if settings.data_provider == "finnhub":
            missing.append(entry)
        else:
            optional.append({**entry, "why": "Backup quotes when Yahoo rate-limits"})
    if not secrets.get("ALPHAVANTAGE_API_KEY", {}).get("configured"):
        entry = {"provider": "alphavantage", **KEY_LINKS["alphavantage"]}
        if settings.data_provider == "alphavantage":
            missing.append(entry)
        else:
            optional.append({**entry, "why": "Backup history / quote cascade"})

    broker = create_broker(user="default")
    acct = broker.get_account()
    return {
        "broker": settings.broker,
        "data_provider": settings.data_provider,
        "live": _is_live(),
        "cash": acct.cash,
        "equity": acct.equity,
        "buying_power": acct.buying_power,
        "positions": [
            {
                "symbol": p.symbol,
                "qty": p.qty,
                "avg_entry": p.avg_entry,
                "unrealized_pl": p.unrealized_pl,
            }
            for p in broker.list_positions()
        ],
        "watchlist": list_symbols(),
        "missing_keys": missing,
        "optional_keys": optional,
        "key_links": KEY_LINKS,
    }


def tool_get_highlights() -> dict[str, Any]:
    """Movers from universe cache only (fast). Full Yahoo fan-out avoided."""
    from infobroker.assistant.desk_context import build_desk_snapshot

    snap = build_desk_snapshot()
    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "stocks_of_day": {"gainers": snap.get("gainers"), "losers": snap.get("losers")},
        "volume_leaders": snap.get("volume_leaders"),
        "universe_quoted": snap.get("universe_quoted"),
        "us_open": snap.get("us_open"),
        "note": "Lightweight cache. Call get_market_deep only if you truly need Yahoo refresh.",
    }


def tool_get_market_deep() -> dict[str, Any]:
    """Expensive highlights refresh — use rarely."""
    return get_market_highlights()


def tool_get_tracked() -> dict[str, Any]:
    return {"items": get_tracked_quotes()}


def _parse_symbols_arg(symbols: Any = None, symbol: Any = None) -> list[str]:
    """Accept 'AAPL', 'AAPL,MSFT', or ['AAPL','MSFT']."""
    raw: list[str] = []
    if symbols is None and symbol is not None:
        symbols = symbol
    if symbols is None:
        return []
    if isinstance(symbols, str):
        parts = re.split(r"[\s,;|]+", symbols.strip())
        raw.extend(parts)
    elif isinstance(symbols, (list, tuple)):
        for item in symbols:
            if isinstance(item, str) and ("," in item or " " in item.strip()):
                raw.extend(re.split(r"[\s,;|]+", item.strip()))
            else:
                raw.append(str(item))
    else:
        raw.append(str(symbols))
    out: list[str] = []
    seen: set[str] = set()
    for s in raw:
        s = (s or "").strip().upper().replace(".", "-")
        if not s or s in seen:
            continue
        seen.add(s)
        out.append(s)
    return out[:40]


def _compact_universe_row(sym: str, meta: dict[str, Any]) -> dict[str, Any]:
    q = meta.get("quote") if isinstance(meta.get("quote"), dict) else {}
    return {
        "symbol": sym,
        "name": meta.get("name") or sym,
        "exchange": meta.get("exchange"),
        "asset_class": meta.get("asset_class"),
        "etf": bool(meta.get("etf")),
        "price": q.get("price"),
        "change_abs_day": q.get("change_abs_day"),
        "change_pct_day": q.get("change_pct_day"),
        "change_pct_week": q.get("change_pct_week"),
        "volume": q.get("volume"),
        "rel_volume": q.get("rel_volume"),
        "high": q.get("high"),
        "low": q.get("low"),
        "as_of": q.get("as_of"),
        "source": q.get("source") or meta.get("source") or "universe",
        "in_universe": True,
        "has_quote": q.get("price") is not None,
    }


def tool_get_prices(
    symbols: Any = None,
    symbol: Any = None,
    refresh_missing: bool = False,
) -> dict[str, Any]:
    """Last prices from the desk universe cache (works when US cash is closed).

    Pass one ticker or many (comma-separated / list). Set refresh_missing=true
    only when a symbol has no cached quote and you need a live Yahoo pull.
    """
    from infobroker.markets.sessions import market_clocks
    from infobroker.universe import get_symbol

    syms = _parse_symbols_arg(symbols, symbol)
    if not syms:
        return {"ok": False, "error": "Provide symbols (e.g. AAPL or AAPL,MSFT,SPY)."}

    clocks = market_clocks()
    items: list[dict[str, Any]] = []
    missing: list[str] = []
    for sym in syms:
        meta = get_symbol(sym)
        if meta and (meta.get("quote") or {}).get("price") is not None:
            items.append(_compact_universe_row(sym, meta))
            continue
        if meta:
            row = _compact_universe_row(sym, meta)
            row["note"] = "Listed in universe but no quote cached yet"
            if refresh_missing:
                try:
                    q = get_stock_quote(sym)
                    row["price"] = q.get("Price") or q.get("price") or q.get("last")
                    row["change_pct_day"] = q.get("Change %") or q.get("change_pct_day")
                    row["source"] = q.get("provider") or q.get("source") or "live"
                    row["has_quote"] = row["price"] is not None
                    row["as_of"] = datetime.now(timezone.utc).isoformat()
                    row.pop("note", None)
                except Exception as exc:  # noqa: BLE001
                    row["fetch_error"] = str(exc)[:160]
                    missing.append(sym)
            else:
                missing.append(sym)
            items.append(row)
            continue
        # Not in universe listings
        row: dict[str, Any] = {
            "symbol": sym,
            "in_universe": False,
            "has_quote": False,
            "price": None,
        }
        if refresh_missing:
            try:
                q = get_stock_quote(sym)
                row["price"] = q.get("Price") or q.get("price") or q.get("last")
                row["change_pct_day"] = q.get("Change %") or q.get("change_pct_day")
                row["name"] = q.get("Name") or q.get("name") or sym
                row["source"] = q.get("provider") or q.get("source") or "live"
                row["has_quote"] = row["price"] is not None
                row["as_of"] = datetime.now(timezone.utc).isoformat()
            except Exception as exc:  # noqa: BLE001
                row["fetch_error"] = str(exc)[:160]
                missing.append(sym)
        else:
            missing.append(sym)
        items.append(row)

    return {
        "ok": True,
        "us_open": clocks.get("us_open"),
        "note": (
            "These are last cached (or freshly fetched) prices. "
            "US cash closed does NOT mean prices are unavailable — "
            "they are the last session / delayed quotes on the desk."
        ),
        "count": len(items),
        "missing_quotes": missing,
        "items": items,
    }


def tool_get_watchlist_quotes(refresh_missing: bool = False) -> dict[str, Any]:
    """Full watchlist with last prices from the universe cache (closed-market safe)."""
    wl = list_symbols()
    if not wl:
        return {
            "ok": True,
            "watchlist": [],
            "items": [],
            "note": "Watchlist is empty — add tickers from Markets or the left rail.",
        }
    payload = tool_get_prices(symbols=wl, refresh_missing=bool(refresh_missing))
    return {
        "ok": True,
        "watchlist": wl,
        "us_open": payload.get("us_open"),
        "count": payload.get("count"),
        "missing_quotes": payload.get("missing_quotes") or [],
        "items": payload.get("items") or [],
        "note": payload.get("note"),
    }


def tool_scan_signals() -> dict[str, Any]:
    """Scan watchlist + a small liquid set (keeps desk responsive)."""
    from infobroker.universe import liquid_scan_symbols

    wl = list_symbols()
    liquid = liquid_scan_symbols(24)
    syms = list(dict.fromkeys(wl + liquid))[:36]
    return scan_watchlist(symbols=syms)


def tool_find_opportunities(max_ideas: int = 5) -> dict[str, Any]:
    """Rank candidates from watchlist + cached movers (cached ~3 min)."""
    import time

    from infobroker.assistant.desk_context import build_desk_snapshot
    from infobroker.universe import liquid_scan_symbols

    max_ideas = max(1, min(int(max_ideas), 5))
    now = time.monotonic()
    if _IDEAS_CACHE["data"] is not None and (now - float(_IDEAS_CACHE["at"])) < _IDEAS_TTL:
        cached = dict(_IDEAS_CACHE["data"])
        cached["ideas"] = (cached.get("ideas") or [])[:max_ideas]
        cached["cached"] = True
        return cached

    snap = build_desk_snapshot()
    desk = tool_get_desk_state()
    seed = list(
        dict.fromkeys(
            list_symbols()
            + [r.get("symbol") for r in (snap.get("gainers") or []) if r.get("symbol")]
            + [r.get("symbol") for r in (snap.get("losers") or []) if r.get("symbol")]
            + [r.get("symbol") for r in (snap.get("volume_leaders") or []) if r.get("symbol")]
            + liquid_scan_symbols(20)
        )
    )[:28]

    scan = scan_watchlist(symbols=seed) if seed else {"items": []}
    ideas: list[dict[str, Any]] = []
    for hit in scan.get("items") or []:
        sig = " ".join(hit.get("signals") or []).lower()
        bullish = any(k in sig for k in ("oversold", "uptrend", "reclaimed", "bullish"))
        bearish = any(k in sig for k in ("overbought", "downtrend", "lost ma", "bearish"))
        side = "buy" if bullish and not bearish else ("sell" if bearish and not bullish else "watch")
        score = float(hit.get("severity") or 0) + abs(float(hit.get("change_pct_day") or 0)) * 0.15
        ideas.append(
            {
                "symbol": hit["symbol"],
                "side": side,
                "score": round(score, 2),
                "price": hit.get("price"),
                "signals": hit.get("signals"),
                "tip": hit.get("tip"),
                "reason": "scanner",
            }
        )

    for row in (snap.get("volume_leaders") or [])[:3]:
        ideas.append(
            {
                "symbol": row["symbol"],
                "side": "watch",
                "score": float(row.get("rel_volume") or row.get("volume") or 0) or 1.0,
                "price": row.get("price"),
                "signals": ["Volume leader (cached)"],
                "tip": "High volume — wait for a clean level, don't chase.",
                "reason": "volume",
            }
        )

    best: dict[str, dict[str, Any]] = {}
    for idea in ideas:
        sym = idea["symbol"]
        if sym not in best or idea["score"] > best[sym]["score"]:
            best[sym] = idea
    ranked = sorted(best.values(), key=lambda x: x["score"], reverse=True)[:max_ideas]
    payload = {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "cash": desk["cash"],
        "live": desk["live"],
        "ideas": ranked,
        "scanned": len(seed),
        "cached": False,
        "note": "Educational candidates — always preview risk before any order.",
    }
    _IDEAS_CACHE["at"] = now
    _IDEAS_CACHE["data"] = payload
    return payload


def tool_explain_desk(topic: str = "overview") -> dict[str, Any]:
    """Explain desk areas: overview|markets|trading|portfolio|order|how_to_trade."""
    from infobroker.assistant.desk_context import DESK_GUIDE

    key = str(topic or "overview").strip().lower().replace(" ", "_")
    aliases = {
        "ticket": "order",
        "orders": "order",
        "trade": "how_to_trade",
        "howto": "how_to_trade",
        "how_to": "how_to_trade",
        "ui": "overview",
        "help": "overview",
    }
    key = aliases.get(key, key)
    if key not in DESK_GUIDE:
        key = "overview"
    return {"topic": key, "guide": DESK_GUIDE[key], "topics": list(DESK_GUIDE.keys())}


def tool_get_portfolio() -> dict[str, Any]:
    from infobroker.portfolio import build_portfolio

    return build_portfolio(user="default", order_limit=40)


def tool_get_auto_track() -> dict[str, Any]:
    from infobroker.auto_track import get_auto_track_settings

    return get_auto_track_settings()


def tool_get_clocks() -> dict[str, Any]:
    from infobroker.markets.sessions import market_clocks

    return market_clocks()


def tool_get_trading_board(limit: int = 24) -> dict[str, Any]:
    from infobroker.trading_board import build_trading_board

    return build_trading_board(scope="watchlist", limit=max(8, min(int(limit), 40)))


def tool_list_lessons() -> dict[str, Any]:
    from infobroker.education import list_lessons

    rows = list_lessons()
    return {
        "count": len(rows),
        "lessons": [
            {"id": r.get("id"), "title": r.get("title"), "level": r.get("level")}
            for r in rows[:40]
        ],
    }


def tool_preview_order(
    symbol: str,
    side: str = "buy",
    qty: float = 1.0,
    stop_price: Optional[float] = None,
) -> dict[str, Any]:
    sym = validate_symbol(symbol)
    broker = create_broker(user="default")
    order_side = OrderSide.BUY if str(side).lower().startswith("b") else OrderSide.SELL
    quote = broker.get_quote(sym)
    req = OrderRequest(
        symbol=sym,
        side=order_side,
        qty=float(qty),
        order_type=OrderType.MARKET,
        stop_price=stop_price,
    )
    verdict = evaluate_order(
        req,
        broker.get_account(),
        broker.list_positions(),
        quote.last,
        stop_price=stop_price,
        is_live=_is_live(),
    )
    return {
        "allowed": verdict.allowed,
        "warnings": verdict.warnings,
        "blockers": verdict.blockers,
        "last": quote.last,
        "live": _is_live(),
        "symbol": sym,
        "side": order_side.value,
        "qty": float(qty),
        "stop_price": stop_price,
    }


def tool_place_paper_order(
    symbol: str,
    side: str = "buy",
    qty: float = 1.0,
    stop_price: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> dict[str, Any]:
    """Place order only when not live (paper / alpaca paper / tradier sandbox)."""
    if _is_live():
        raise BrokerError(
            "Refusing live order from assistant. Switch to paper/sim or place manually."
        )
    preview = tool_preview_order(symbol, side, qty, stop_price)
    if not preview["allowed"]:
        return {"placed": False, "preview": preview}
    broker = create_broker(user="default")
    order_side = OrderSide.BUY if str(side).lower().startswith("b") else OrderSide.SELL
    sym = validate_symbol(symbol)
    if stop_price or take_profit:
        orders = broker.place_bracket(
            sym, order_side, float(qty), take_profit=take_profit, stop_loss=stop_price
        )
        return {
            "placed": True,
            "orders": [
                {"id": o.id, "status": o.status.value, "side": o.side.value} for o in orders
            ],
        }
    order = broker.place_order(
        OrderRequest(
            symbol=sym,
            side=order_side,
            qty=float(qty),
            order_type=OrderType.MARKET,
            stop_price=stop_price,
        )
    )
    return {
        "placed": True,
        "orders": [
            {
                "id": order.id,
                "status": order.status.value,
                "side": order.side.value,
                "fill": order.filled_avg_price,
            }
        ],
    }


def tool_add_watch(symbol: str) -> dict[str, Any]:
    return {"symbols": add_symbol(symbol)}


def tool_remove_watch(symbol: str) -> dict[str, Any]:
    return {"symbols": remove_symbol(symbol)}


def tool_backtest(symbol: str, start: str, end: str, strategy: str = "sma_crossover") -> dict[str, Any]:
    return run_strategy_backtest(strategy, validate_symbol(symbol), start, end)


def tool_list_strategies() -> dict[str, Any]:
    return {"strategies": list_strategies(), "engine": "yfinance (free)"}


def tool_get_quote(symbol: str) -> dict[str, Any]:
    """Prefer universe last price (works when closed); fall back to live fetch."""
    payload = tool_get_prices(symbol=symbol, refresh_missing=True)
    items = payload.get("items") or []
    if items:
        row = items[0]
        return {
            "symbol": row.get("symbol"),
            "Price": row.get("price"),
            "price": row.get("price"),
            "Change %": row.get("change_pct_day"),
            "change_pct_day": row.get("change_pct_day"),
            "change_pct_week": row.get("change_pct_week"),
            "volume": row.get("volume"),
            "name": row.get("name"),
            "exchange": row.get("exchange"),
            "as_of": row.get("as_of"),
            "provider": row.get("source"),
            "us_open": payload.get("us_open"),
            "from_universe": bool(row.get("in_universe")),
            "note": payload.get("note"),
        }
    sym = validate_symbol(symbol)
    q = get_stock_quote(sym)
    q["symbol"] = sym
    return q


def tool_get_fundamentals(symbol: str) -> dict[str, Any]:
    return get_fundamentals(validate_symbol(symbol))


def tool_get_chart_pack(symbol: str, start: str, end: str) -> dict[str, Any]:
    pack = build_chart_pack(validate_symbol(symbol), start, end)
    # Trim bars for LLM context
    bars = pack.get("bars") or []
    if len(bars) > 40:
        step = max(1, len(bars) // 40)
        pack = {**pack, "bars": bars[::step][:40], "bars_trimmed": True, "bars_full": len(bars)}
    return pack


def tool_analyze(
    symbol: str,
    start: Optional[str] = None,
    end: Optional[str] = None,
    period: str = "1y",
) -> dict[str, Any]:
    """yfinance → pandas → TA-Lib snapshot (required stack)."""
    sym = validate_symbol(symbol)
    if start and end:
        result = analyze_symbol(sym, start=start, end=end)
    else:
        result = analyze_symbol(sym, period=period or "1y")
    # Keep payload small for the agent
    bars = result.get("bars") or []
    if len(bars) > 30:
        step = max(1, len(bars) // 30)
        result = {**result, "bars": bars[::step][:30], "bars_trimmed": True}
    return result


def tool_cancel_order(order_id: str) -> dict[str, Any]:
    broker = create_broker(user="default")
    order = broker.cancel_order(order_id)
    return {"id": order.id, "status": order.status.value}


def tool_list_orders(limit: int = 20) -> dict[str, Any]:
    broker = create_broker(user="default")
    orders = broker.list_orders()[: max(1, min(int(limit), 100))]
    return {
        "orders": [
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": o.side.value,
                "qty": o.qty,
                "type": o.order_type.value,
                "status": o.status.value,
                "stop": o.stop_price,
                "limit": o.limit_price,
                "fill": o.filled_avg_price,
            }
            for o in orders
        ]
    }


def tool_place_order(
    symbol: str,
    side: str = "buy",
    qty: float = 1.0,
    order_type: str = "market",
    limit_price: Optional[float] = None,
    stop_price: Optional[float] = None,
    take_profit: Optional[float] = None,
) -> dict[str, Any]:
    """Full ticket: market/limit/stop + optional bracket exits. Paper/sim only."""
    if _is_live():
        raise BrokerError("Refusing live order from assistant.")
    otype_key = (order_type or "market").lower().replace("-", "_")
    otype = {
        "market": OrderType.MARKET,
        "limit": OrderType.LIMIT,
        "stop": OrderType.STOP,
        "stop_limit": OrderType.STOP_LIMIT,
    }.get(otype_key)
    if not otype:
        raise BrokerError(f"Bad order_type: {order_type}")
    # Reuse paper place with richer types
    if otype == OrderType.MARKET and (stop_price or take_profit):
        return tool_place_paper_order(symbol, side, qty, stop_price, take_profit)
    preview = tool_preview_order(symbol, side, qty, stop_price if otype == OrderType.MARKET else None)
    if not preview["allowed"] and otype == OrderType.MARKET:
        return {"placed": False, "preview": preview}
    broker = create_broker(user="default")
    order_side = OrderSide.BUY if str(side).lower().startswith("b") else OrderSide.SELL
    sym = validate_symbol(symbol)
    order = broker.place_order(
        OrderRequest(
            symbol=sym,
            side=order_side,
            qty=float(qty),
            order_type=otype,
            limit_price=limit_price,
            stop_price=stop_price,
        )
    )
    return {
        "placed": True,
        "orders": [
            {
                "id": order.id,
                "status": order.status.value,
                "side": order.side.value,
                "type": order.order_type.value,
                "fill": order.filled_avg_price,
            }
        ],
    }


def tool_mcp_control(action: str = "status") -> dict[str, Any]:
    act = (action or "status").lower()
    if act == "start":
        return mcp_start()
    if act == "stop":
        return mcp_stop()
    if act == "restart":
        return mcp_restart()
    return mcp_status()


def tool_ollama_control(action: str = "status") -> dict[str, Any]:
    return ollama_control(action)


def tool_process_stops() -> dict[str, Any]:
    broker = create_broker(user="default")
    if not isinstance(broker, PaperBroker):
        raise BrokerError("process_stops only works on the local paper broker")
    filled = broker.process_open_stops()
    return {
        "triggered": len(filled),
        "orders": [
            {"id": o.id, "symbol": o.symbol, "status": o.status.value} for o in filled
        ],
    }


def tool_key_links() -> dict[str, Any]:
    pub = get_public_settings()
    status = {
        name: {
            **meta,
            "configured": bool(
                (pub.get("secrets") or {}).get(
                    {
                        "alpaca": "ALPACA_API_KEY",
                        "public": "PUBLIC_PERSONAL_SECRET",
                        "tradier": "TRADIER_ACCESS_TOKEN",
                        "finnhub": "FINNHUB_API_KEY",
                        "alphavantage": "ALPHAVANTAGE_API_KEY",
                    }[name],
                    {},
                ).get("configured")
            ),
        }
        for name, meta in KEY_LINKS.items()
    }
    return {"providers": status}


TOOLS: dict[str, ToolSpec] = {
    "get_desk_state": ToolSpec(
        "get_desk_state",
        "Read account, watchlist, broker mode, and missing API keys with signup links.",
        {"type": "object", "properties": {}},
        tool_get_desk_state,
    ),
    "get_highlights": ToolSpec(
        "get_highlights",
        "Fast movers from desk cache: gainers, losers, volume leaders, US open.",
        {"type": "object", "properties": {}},
        tool_get_highlights,
    ),
    "get_market_deep": ToolSpec(
        "get_market_deep",
        "Expensive Yahoo highlights refresh — use only when cache looks empty.",
        {"type": "object", "properties": {}},
        tool_get_market_deep,
    ),
    "explain_desk": ToolSpec(
        "explain_desk",
        "Explain desk UI: overview|markets|trading|portfolio|order|how_to_trade.",
        {
            "type": "object",
            "properties": {"topic": {"type": "string", "default": "overview"}},
        },
        tool_explain_desk,
    ),
    "get_portfolio": ToolSpec(
        "get_portfolio",
        "Full portfolio: cash, equity, positions, P&L, recent orders.",
        {"type": "object", "properties": {}},
        tool_get_portfolio,
    ),
    "get_auto_track": ToolSpec(
        "get_auto_track",
        "Auto-track gainer rules/settings for the Portfolio tab.",
        {"type": "object", "properties": {}},
        tool_get_auto_track,
    ),
    "get_clocks": ToolSpec(
        "get_clocks",
        "World market clocks (NY/LDN/FRA/TYO/HK/SYD) open/closed status.",
        {"type": "object", "properties": {}},
        tool_get_clocks,
    ),
    "get_trading_board": ToolSpec(
        "get_trading_board",
        "Trading tab board: bid/ask/last + position qty for watchlist names.",
        {
            "type": "object",
            "properties": {"limit": {"type": "integer", "default": 24}},
        },
        tool_get_trading_board,
    ),
    "list_lessons": ToolSpec(
        "list_lessons",
        "Learning tab lesson catalog (id, title, level).",
        {"type": "object", "properties": {}},
        tool_list_lessons,
    ),
    "get_tracked": ToolSpec(
        "get_tracked",
        "Quotes for every tracked/watchlist ticker (live Yahoo batch — heavier).",
        {"type": "object", "properties": {}},
        tool_get_tracked,
    ),
    "get_prices": ToolSpec(
        "get_prices",
        "Last prices + day% from universe cache for one or many tickers (works when market closed). "
        "args.symbols: 'AAPL' or 'AAPL,MSFT,SPY'. refresh_missing=true only if cache empty.",
        {
            "type": "object",
            "properties": {
                "symbols": {"type": "string", "description": "Ticker or comma-separated list"},
                "symbol": {"type": "string", "description": "Single ticker alias"},
                "refresh_missing": {"type": "boolean", "default": False},
            },
        },
        tool_get_prices,
    ),
    "get_watchlist_quotes": ToolSpec(
        "get_watchlist_quotes",
        "Full watchlist with last prices from universe cache (closed-market safe).",
        {
            "type": "object",
            "properties": {
                "refresh_missing": {"type": "boolean", "default": False},
            },
        },
        tool_get_watchlist_quotes,
    ),
    "scan_signals": ToolSpec(
        "scan_signals",
        "Technical scanner over watchlist + small liquid set (keeps desk light).",
        {"type": "object", "properties": {}},
        tool_scan_signals,
    ),
    "find_opportunities": ToolSpec(
        "find_opportunities",
        "Rank careful trade candidates (cached ~3 min; small scan set).",
        {
            "type": "object",
            "properties": {
                "max_ideas": {"type": "integer", "description": "1-5 ideas", "default": 3}
            },
        },
        tool_find_opportunities,
    ),
    "preview_order": ToolSpec(
        "preview_order",
        "Risk-check a buy/sell without placing it.",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "qty": {"type": "number"},
                "stop_price": {"type": "number"},
            },
            "required": ["symbol"],
        },
        tool_preview_order,
    ),
    "place_paper_order": ToolSpec(
        "place_paper_order",
        "Place a paper/sim order only (never live). Prefer preview_order first.",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["buy", "sell"]},
                "qty": {"type": "number"},
                "stop_price": {"type": "number"},
                "take_profit": {"type": "number"},
            },
            "required": ["symbol"],
        },
        tool_place_paper_order,
        mutates=True,
    ),
    "add_watch": ToolSpec(
        "add_watch",
        "Add a ticker to the watchlist.",
        {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        tool_add_watch,
        mutates=True,
    ),
    "remove_watch": ToolSpec(
        "remove_watch",
        "Remove a ticker from the watchlist.",
        {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        tool_remove_watch,
        mutates=True,
    ),
    "backtest": ToolSpec(
        "backtest",
        "Free yfinance backtest. strategy: sma_crossover|rsi_mean_reversion|macd_cross|buy_hold|breakout_20d",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "strategy": {"type": "string", "default": "sma_crossover"},
            },
            "required": ["symbol", "start", "end"],
        },
        tool_backtest,
    ),
    "list_strategies": ToolSpec(
        "list_strategies",
        "List free base strategies available for backtesting.",
        {"type": "object", "properties": {}},
        tool_list_strategies,
    ),
    "get_quote": ToolSpec(
        "get_quote",
        "Price for one symbol — universe last quote first (works when closed), live fetch if needed.",
        {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        tool_get_quote,
    ),
    "get_fundamentals": ToolSpec(
        "get_fundamentals",
        "Fundamentals snapshot for a symbol.",
        {"type": "object", "properties": {"symbol": {"type": "string"}}, "required": ["symbol"]},
        tool_get_fundamentals,
    ),
    "get_chart_pack": ToolSpec(
        "get_chart_pack",
        "OHLC + SMA/RSI/MACD/volume for symbol between start/end (YYYY-MM-DD). Uses yfinance+pandas+TA-Lib.",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
            },
            "required": ["symbol", "start", "end"],
        },
        tool_get_chart_pack,
    ),
    "analyze": ToolSpec(
        "analyze",
        "Full analysis: yfinance download, Pandas OHLCV, TA-Lib RSI/MACD/SMA/ATR/Bollinger.",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "start": {"type": "string"},
                "end": {"type": "string"},
                "period": {"type": "string", "default": "1y"},
            },
            "required": ["symbol"],
        },
        tool_analyze,
    ),
    "list_orders": ToolSpec(
        "list_orders",
        "Show recent orders / blotter.",
        {"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
        tool_list_orders,
    ),
    "cancel_order": ToolSpec(
        "cancel_order",
        "Cancel an open order by id.",
        {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
        tool_cancel_order,
        mutates=True,
    ),
    "place_order": ToolSpec(
        "place_order",
        "Place paper order: market|limit|stop with optional stop_price/limit_price/take_profit.",
        {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string"},
                "qty": {"type": "number"},
                "order_type": {"type": "string"},
                "limit_price": {"type": "number"},
                "stop_price": {"type": "number"},
                "take_profit": {"type": "number"},
            },
            "required": ["symbol"],
        },
        tool_place_order,
        mutates=True,
    ),
    "process_stops": ToolSpec(
        "process_stops",
        "Trigger paper stop orders against latest quotes.",
        {"type": "object", "properties": {}},
        tool_process_stops,
        mutates=True,
    ),
    "key_links": ToolSpec(
        "key_links",
        "Return signup/dashboard links for brokers and market-data keys.",
        {"type": "object", "properties": {}},
        tool_key_links,
    ),
    "mcp_control": ToolSpec(
        "mcp_control",
        "Start/stop/restart/status the Infobroker MCP server process.",
        {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "description": "start|stop|restart|status",
                    "default": "status",
                }
            },
        },
        tool_mcp_control,
        mutates=True,
    ),
    "ollama_control": ToolSpec(
        "ollama_control",
        "Control Grapevine/Ollama: status|ping|warm|unload|list_models.",
        {
            "type": "object",
            "properties": {"action": {"type": "string", "default": "status"}},
        },
        tool_ollama_control,
        mutates=True,
    ),
}


def tool_schemas_for_prompt() -> str:
    lines = []
    for spec in TOOLS.values():
        lines.append(f"- {spec.name}: {spec.description}")
        if spec.parameters.get("properties"):
            lines.append(f"  args: {json.dumps(spec.parameters.get('properties', {}))}")
    return "\n".join(lines)


def normalize_tool_args(name: str, args: Optional[dict[str, Any]] = None, raw: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """Coerce LLM quirks: ticker→symbol, top-level fields into args, drop unknowns."""
    import inspect

    out = dict(args or {})
    raw = raw or {}
    aliases = {
        "ticker": "symbol",
        "sym": "symbol",
        "stop": "stop_price",
        "stopLoss": "stop_price",
        "takeProfit": "take_profit",
        "tp": "take_profit",
    }
    for src, dest in aliases.items():
        if src in out and dest not in out:
            out[dest] = out.pop(src)
        if src in raw and dest not in out:
            out[dest] = raw[src]
    if "orderId" in raw and "order_id" not in out:
        out["order_id"] = raw["orderId"]
    for k in (
        "symbol",
        "side",
        "qty",
        "stop_price",
        "take_profit",
        "max_ideas",
        "start",
        "end",
        "strategy",
        "order_type",
        "limit_price",
        "order_id",
        "action",
        "topic",
        "limit",
        "symbols",
        "refresh_missing",
    ):
        if k in raw and k not in out:
            out[k] = raw[k]

    spec = TOOLS.get(name)
    if not spec:
        return out
    try:
        params = set(inspect.signature(spec.handler).parameters)
    except (TypeError, ValueError):
        return out
    return {k: v for k, v in out.items() if k in params}


def execute_tool(
    name: str,
    args: Optional[dict[str, Any]] = None,
    *,
    raw: Optional[dict[str, Any]] = None,
) -> ActionEvent:
    args = normalize_tool_args(name, args, raw)
    spec = TOOLS.get(name)
    if not spec:
        return _log(
            ActionEvent(
                id=uuid4().hex,
                tool=name,
                args=args,
                ok=False,
                summary=f"Unknown tool: {name}",
                error="unknown_tool",
            )
        )
    try:
        # Validate required params with a clear error for the agent
        required = (spec.parameters or {}).get("required") or []
        missing = [k for k in required if args.get(k) in (None, "")]
        if missing:
            raise TypeError(f"Missing required arg(s): {', '.join(missing)}")
        result = spec.handler(**args) if args else spec.handler()
        summary = f"{name} ok"
        if isinstance(result, dict):
            if "ideas" in result:
                summary = f"Found {len(result.get('ideas') or [])} opportunities"
            elif "hits" in result:
                summary = f"Scan hits: {result.get('hits')}"
            elif "placed" in result:
                summary = "Order placed" if result.get("placed") else "Order blocked"
            elif "allowed" in result:
                summary = "Risk OK" if result.get("allowed") else "Risk blocked"
            elif "missing_keys" in result and result["missing_keys"]:
                summary = f"{len(result['missing_keys'])} missing key(s)"
        return _log(
            ActionEvent(
                id=uuid4().hex,
                tool=name,
                args=args,
                ok=True,
                summary=summary,
                result=result,
            )
        )
    except Exception as exc:  # noqa: BLE001
        return _log(
            ActionEvent(
                id=uuid4().hex,
                tool=name,
                args=args,
                ok=False,
                summary=str(exc)[:200],
                error=str(exc),
            )
        )

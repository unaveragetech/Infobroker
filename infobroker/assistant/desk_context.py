"""Compact live desk snapshot for Grapevine — cached & lightweight (no Yahoo fan-out)."""

from __future__ import annotations

import time
from typing import Any, Optional

_CACHE: dict[str, Any] = {"at": 0.0, "key": "", "data": None}
_TTL_SEC = 45.0


def _short_rows(rows: list, n: int = 5) -> list[dict[str, Any]]:
    out = []
    for r in rows[:n]:
        if not isinstance(r, dict):
            continue
        out.append(
            {
                "symbol": r.get("symbol"),
                "change_pct_day": r.get("change_pct_day"),
                "price": r.get("price") or r.get("last"),
                "volume": r.get("volume"),
            }
        )
    return out


def _movers_light() -> dict[str, Any]:
    """Universe cache only — never triggers batch Yahoo snapshots."""
    try:
        from infobroker.universe import movers as universe_movers

        mv = universe_movers(limit=6)
        day = mv.get("stocks_of_day") or {}
        return {
            "gainers": _short_rows(day.get("gainers") or [], 5),
            "losers": _short_rows(day.get("losers") or [], 5),
            "volume_leaders": _short_rows(mv.get("volume_leaders") or [], 4),
            "universe_quoted": int(mv.get("quoted") or 0),
        }
    except Exception as exc:  # noqa: BLE001
        return {
            "gainers": [],
            "losers": [],
            "volume_leaders": [],
            "universe_quoted": 0,
            "error": str(exc)[:120],
        }


def build_desk_snapshot(
    ui_context: Optional[dict[str, Any]] = None,
    *,
    force: bool = False,
) -> dict[str, Any]:
    """Markets open/closed, movers, desk money, UI focus — kept small for the LLM."""
    ui = ui_context or {}
    key = f"{ui.get('active_tab')}|{ui.get('markets_sub')}|{ui.get('selected_symbol')}"
    now = time.monotonic()
    if (
        not force
        and _CACHE["data"] is not None
        and _CACHE["key"] == key
        and (now - float(_CACHE["at"])) < _TTL_SEC
    ):
        cached = dict(_CACHE["data"])
        cached["ui"] = ui
        cached["cached"] = True
        return cached

    from infobroker.assistant.tools import tool_get_desk_state
    from infobroker.markets.sessions import market_clocks

    desk = tool_get_desk_state()
    clocks = market_clocks()
    movers = _movers_light()

    venues = []
    for m in (clocks.get("markets") or [])[:8]:
        venues.append(
            {
                "id": m.get("id"),
                "short": m.get("short"),
                "is_open": m.get("is_open"),
                "hint": m.get("hint") or m.get("next_open_label"),
            }
        )

    data = {
        "us_open": clocks.get("us_open"),
        "us_hint": clocks.get("us_next_open_label") or clocks.get("us_hint"),
        "any_market_open": clocks.get("any_open"),
        "venues": venues,
        "broker": desk.get("broker"),
        "live_trading": desk.get("live"),
        "cash": desk.get("cash"),
        "equity": desk.get("equity"),
        "buying_power": desk.get("buying_power"),
        "positions": (desk.get("positions") or [])[:12],
        "watchlist": (desk.get("watchlist") or [])[:16],
        "gainers": movers.get("gainers") or [],
        "losers": movers.get("losers") or [],
        "volume_leaders": movers.get("volume_leaders") or [],
        "universe_quoted": movers.get("universe_quoted"),
        "missing_keys": desk.get("missing_keys") or [],
        "ui": ui,
        "prices_note": (
            "Last quotes remain available when US cash is closed — "
            "use get_prices / get_watchlist_quotes; do not claim you cannot see prices."
        ),
        "cached": False,
    }
    _CACHE["at"] = now
    _CACHE["key"] = key
    _CACHE["data"] = data
    return dict(data)


# Static map — kept out of every LLM prompt body (referenced by name in SYSTEM)
COACH_TARGETS = (
    "brand markets-live markets-movers markets-scanner markets-symbol "
    "trading portfolio order-ticket order-blotter watchlist account "
    "assistant desk-tabs top-actions learn-rail charts auto-track settings"
)

DESK_GUIDE = {
    "overview": (
        "Infobroker desk tabs: Markets (live board, movers, scanner, symbol), "
        "Trading (bid/ask board + quick buy/sell), Portfolio (equity/P&L/positions), "
        "Learning (tutor/journal/lessons), Strategies, Charts, Services (Ollama/MCP/keys), "
        "Settings (project docs — data pipeline, brokers, architecture). "
        "Right rail: order ticket + blotter. Far right: Grapevine coach."
    ),
    "markets": (
        "Markets → Live = heat/volume board. Movers = gainers/losers. "
        "Scanner = signal scan. Symbol = detail + chart. Click a ticker to select it."
    ),
    "trading": (
        "Trading tab shows watchlist + liquid names with bid/ask/last and position qty. "
        "Use Buy/Sell there or the order ticket. Prefer paper until ready."
    ),
    "portfolio": (
        "Portfolio shows cash, equity, buying power, unrealized P&L, positions, orders, "
        "and auto-track rules that can add gainer names to the watchlist."
    ),
    "order": (
        "Order ticket: set symbol, side, qty, optional stop → Preview (risk check) → Submit. "
        "Grapevine only places paper/sim after a clean preview."
    ),
    "how_to_trade": (
        "1) Check US open (clocks under logo). 2) Markets→Movers for gainers/losers. "
        "3) Click a symbol, read chart. 4) Size risk on order ticket + Preview. "
        "5) Paper Submit. Never chase; use a stop; small size first."
    ),
}

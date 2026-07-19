"""Trading desk board: watchlist + live universe quotes with bid/ask and positions."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from infobroker.brokers import create_broker
from infobroker.data.highlights import fetch_yahoo_quotes_bulk
from infobroker.universe.engine import quoted_rows
from infobroker.watchlist import list_symbols


def _estimate_book(price: float | None, bid: float | None, ask: float | None) -> tuple[float | None, float | None]:
    if price is None:
        return bid, ask
    if bid is None:
        bid = round(float(price) * 0.9995, 4)
    if ask is None:
        ask = round(float(price) * 1.0005, 4)
    return bid, ask


def build_trading_board(
    scope: str = "both",
    limit: int = 120,
    user: str = "default",
) -> dict[str, Any]:
    """Rows ready for one-click buy/sell with last/bid/ask and position qty."""
    scope_n = (scope or "both").strip().lower()
    limit_n = max(10, min(int(limit), 400))

    watched = set(list_symbols())
    rows_src: list[dict[str, Any]] = []

    if scope_n in {"watchlist", "both", "watch"}:
        for sym in sorted(watched):
            rows_src.append({"symbol": sym, "lists": ["watchlist"]})

    if scope_n in {"live", "universe", "both"}:
        live = quoted_rows()
        live.sort(key=lambda r: abs(r.get("change_pct_day") or 0), reverse=True)
        for r in live[: max(limit_n, 80)]:
            rows_src.append({"symbol": r["symbol"], "lists": ["live"], "cached": r})

    # Dedupe — prefer merging list tags
    merged: dict[str, dict[str, Any]] = {}
    for row in rows_src:
        sym = row["symbol"]
        if sym not in merged:
            merged[sym] = {
                "symbol": sym,
                "lists": list(row.get("lists") or []),
                "cached": row.get("cached"),
            }
        else:
            for tag in row.get("lists") or []:
                if tag not in merged[sym]["lists"]:
                    merged[sym]["lists"].append(tag)
            if row.get("cached") and not merged[sym].get("cached"):
                merged[sym]["cached"] = row["cached"]

    symbols = list(merged.keys())[:limit_n]
    # Always include full watchlist even if over limit
    for sym in watched:
        if sym not in symbols:
            symbols.append(sym)
            if sym not in merged:
                merged[sym] = {"symbol": sym, "lists": ["watchlist"], "cached": None}

    bulk = fetch_yahoo_quotes_bulk(symbols)

    broker = create_broker(user=user)
    acct = broker.get_account()
    positions = {p.symbol: p for p in broker.list_positions()}

    items: list[dict[str, Any]] = []
    for sym in symbols:
        meta = merged.get(sym) or {"lists": [], "cached": None}
        cached = meta.get("cached") or {}
        snap = bulk.get(sym) or {}
        price = snap.get("price")
        if price is None:
            price = cached.get("price")
        bid = snap.get("bid")
        ask = snap.get("ask")
        bid, ask = _estimate_book(
            float(price) if price is not None else None,
            float(bid) if bid is not None else None,
            float(ask) if ask is not None else None,
        )
        pos = positions.get(sym)
        lists = list(meta.get("lists") or [])
        if pos and "portfolio" not in lists:
            lists.append("portfolio")
        items.append(
            {
                "symbol": sym,
                "name": snap.get("name") or cached.get("name") or sym,
                "price": price,
                "bid": bid,
                "ask": ask,
                "spread": round(float(ask) - float(bid), 4) if bid is not None and ask is not None else None,
                "change_pct_day": snap.get("change_pct_day")
                if snap.get("change_pct_day") is not None
                else cached.get("change_pct_day"),
                "change_abs_day": snap.get("change_abs_day")
                if snap.get("change_abs_day") is not None
                else cached.get("change_abs_day"),
                "volume": snap.get("volume") if snap.get("volume") is not None else cached.get("volume"),
                "exchange": cached.get("exchange"),
                "lists": lists,
                "in_watchlist": sym in watched,
                "position_qty": float(pos.qty) if pos else 0.0,
                "avg_entry": float(pos.avg_entry) if pos else None,
                "market_value": float(pos.market_value) if pos else 0.0,
                "unrealized_pl": float(pos.unrealized_pl) if pos else 0.0,
                "source": snap.get("source") or cached.get("source") or "cache",
            }
        )

    # Watchlist + positions first, then by |day move|
    items.sort(
        key=lambda r: (
            0 if r.get("in_watchlist") else 1,
            0 if (r.get("position_qty") or 0) else 1,
            -(abs(r.get("change_pct_day") or 0)),
            r["symbol"],
        )
    )

    return {
        "as_of": datetime.now(timezone.utc).isoformat(),
        "scope": scope_n,
        "count": len(items),
        "cash": float(acct.cash or 0),
        "equity": float(acct.equity or 0),
        "buying_power": float(acct.buying_power or 0),
        "broker": broker.profile.id,
        "broker_name": broker.profile.name,
        "watchlist_count": len(watched),
        "position_count": len(positions),
        "items": items,
    }

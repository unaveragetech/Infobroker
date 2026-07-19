"""Turn real blotter orders into teachable trade stories."""

from __future__ import annotations

from typing import Any, Optional

from infobroker.brokers import create_broker
from infobroker.brokers.base import Order, OrderSide, OrderStatus, OrderType


def _idea_for_order(order: Order, positions: dict[str, float]) -> dict[str, str]:
    side = order.side.value if hasattr(order.side, "value") else str(order.side)
    otype = order.order_type.value if hasattr(order.order_type, "value") else str(order.order_type)
    status = order.status.value if hasattr(order.status, "value") else str(order.status)
    sym = order.symbol
    qty = order.qty
    fill = order.filled_avg_price
    stop = order.stop_price
    limit = order.limit_price

    title = f"{side.upper()} {qty:g} {sym}"
    style = "Undefined style"
    idea = ""
    lesson_hint = "playbook"
    risk_note = ""

    if otype == OrderType.MARKET.value or otype == "market":
        if stop and (status in {OrderStatus.FILLED.value, "filled"} or fill):
            style = "Bracket / protected market"
            idea = (
                f"You used a market order on {sym} and defined invalidation"
                + (f" near {stop:g}" if stop else "")
                + ". That is the tutor’s preferred beginner pattern: participate, but pre-commit risk."
            )
            lesson_hint = "stops"
            risk_note = "Market entry accepts spread; the stop is the real skill."
        else:
            style = "Market participation"
            idea = (
                f"A market {side} on {sym} prioritizes fill certainty over price. "
                "Ask: was this a planned level or a chase?"
            )
            lesson_hint = "chase"
            risk_note = "If there was no stop plan, reopen the Risk lesson before the next ticket."

    elif otype in {OrderType.LIMIT.value, "limit"}:
        style = "Patient limit"
        idea = (
            f"Limit {side} on {sym}"
            + (f" @ {limit:g}" if limit else "")
            + " means you refused to chase. If it never filled, the setup may simply not have arrived — that is discipline, not failure."
        )
        lesson_hint = "support_resistance"
        risk_note = "After a limit fills, still need an invalidation stop."

    elif otype in {OrderType.STOP.value, OrderType.STOP_LIMIT.value, "stop", "stop_limit"}:
        style = "Stop entry (breakout style)"
        idea = (
            f"Stop entry on {sym}"
            + (f" @ {stop:g}" if stop else "")
            + " is a ‘prove it’ order — you only participate after price crosses your line. "
            "Confirm you were not placing the stop in the middle of an already-extended spike."
        )
        lesson_hint = "chase"
        risk_note = "Stop-limit may not fill in a runaway move; know which variant you used."

    else:
        style = otype
        idea = f"Order {otype} {side} {sym}. Map it back to a named playbook setup."
        lesson_hint = "playbook"

    if status in {OrderStatus.CANCELED.value, "canceled"}:
        idea += " This order was canceled — canceling a bad idea is a winning habit."
    elif status in {OrderStatus.REJECTED.value, "rejected"}:
        idea += " Rejected (often buying power or short rules). Read the blocker; do not force size."
    elif status in {OrderStatus.OPEN.value, "open"}:
        idea += " Still open — decide now what will cancel it if the thesis goes stale."

    pos_qty = positions.get(sym.upper(), 0.0)
    if side == "sell" and pos_qty >= 0:
        style = "Exit / reduce long" if "Bracket" not in style else style
        if "Exit" in style or pos_qty == 0:
            idea = (
                f"Sell on {sym} reduces or closes risk. Exits deserve as much planning as entries — "
                "was this thesis done, stop, or target?"
            )
            lesson_hint = "risk"

    return {
        "title": title,
        "style": style,
        "idea": idea,
        "risk_note": risk_note,
        "lesson_id": lesson_hint,
        "tutor_tip": _tutor_tip(otype, side),
    }


def _tutor_tip(otype: str, side: str) -> str:
    if otype in {"market", OrderType.MARKET.value}:
        return "Tutor: market is fine after the level proves itself — narrate your trigger in one sentence."
    if otype in {"limit", OrderType.LIMIT.value}:
        return "Tutor: limits buy patience. Journal whether price ever tagged your level."
    if otype in {"stop", "stop_limit", OrderType.STOP.value, OrderType.STOP_LIMIT.value}:
        return "Tutor: stop entries are breakout tools. If you used one to chase, reopen the Avoid chasing lesson."
    return "Tutor: name the setup before the next order."


def build_trade_stories(user: str = "default", limit: int = 40) -> dict[str, Any]:
    broker = create_broker(user=user)
    orders = broker.list_orders()
    positions = {p.symbol.upper(): float(p.qty) for p in broker.list_positions()}
    stories = []
    for order in orders[: max(1, min(int(limit), 100))]:
        idea = _idea_for_order(order, positions)
        stories.append(
            {
                "id": order.id,
                "symbol": order.symbol,
                "side": order.side.value if hasattr(order.side, "value") else order.side,
                "qty": order.qty,
                "order_type": order.order_type.value
                if hasattr(order.order_type, "value")
                else order.order_type,
                "status": order.status.value if hasattr(order.status, "value") else order.status,
                "fill": order.filled_avg_price,
                "limit_price": order.limit_price,
                "stop_price": order.stop_price,
                "submitted_at": order.submitted_at,
                **idea,
            }
        )

    summary = {
        "count": len(stories),
        "filled": sum(1 for s in stories if s["status"] in {"filled", OrderStatus.FILLED.value}),
        "open": sum(1 for s in stories if s["status"] in {"open", OrderStatus.OPEN.value}),
        "message": (
            "Each card explains the idea behind a real blotter order. "
            "Empty history? Place a small paper trade, then return here."
            if not stories
            else "Read the idea under each trade like a tutor reviewing your homework."
        ),
    }
    return {"stories": stories, "summary": summary}


def sample_demo_stories() -> list[dict[str, Any]]:
    """Shown only when the user has no orders — annotated examples, clearly labeled."""
    return [
        {
            "id": "demo-1",
            "symbol": "AAPL",
            "side": "buy",
            "qty": 1,
            "order_type": "market",
            "status": "filled",
            "fill": 190.0,
            "stop_price": 185.0,
            "limit_price": None,
            "submitted_at": None,
            "demo": True,
            "title": "BUY 1 AAPL (demo)",
            "style": "Bracket / protected market",
            "idea": (
                "Demo: market long after a pullback to rising SMA20, stop under the swing low. "
                "The idea is trend continuation with predefined 1R — not predicting the close."
            ),
            "risk_note": "Demo only — place your own paper trade to replace this card.",
            "lesson_id": "trend",
            "tutor_tip": "Tutor: copy this structure on paper with your own level.",
        },
        {
            "id": "demo-2",
            "symbol": "MSFT",
            "side": "buy",
            "qty": 2,
            "order_type": "limit",
            "status": "canceled",
            "fill": None,
            "stop_price": None,
            "limit_price": 400.0,
            "submitted_at": None,
            "demo": True,
            "title": "BUY 2 MSFT (demo)",
            "style": "Patient limit",
            "idea": (
                "Demo: limit never filled and was canceled. That can be correct — you refused "
                "to chase when price ran away."
            ),
            "risk_note": "Canceling stale limits is part of risk hygiene.",
            "lesson_id": "chase",
            "tutor_tip": "Tutor: missing a fill is often cheaper than chasing.",
        },
    ]

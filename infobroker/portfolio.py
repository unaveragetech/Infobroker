"""Portfolio summary: positions, orders, P&L rollup."""

from __future__ import annotations

from typing import Any

from infobroker.brokers import create_broker
from infobroker.brokers.paper import PaperBroker


def build_portfolio(user: str = "default", order_limit: int = 80) -> dict[str, Any]:
    """Aggregate account, open positions, recent orders, and P&L totals."""
    broker = create_broker(user=user)
    acct = broker.get_account()
    positions = broker.list_positions()
    orders = list(reversed(broker.list_orders(status=None)))[: max(1, min(int(order_limit), 200))]

    pos_rows: list[dict[str, Any]] = []
    total_mv = 0.0
    total_upl = 0.0
    for p in positions:
        mv = float(p.market_value or 0)
        upl = float(p.unrealized_pl or 0)
        total_mv += mv
        total_upl += upl
        cost = float(p.avg_entry or 0) * float(p.qty or 0)
        upl_pct = ((mv / cost) - 1.0) * 100 if cost else None
        pos_rows.append(
            {
                "symbol": p.symbol,
                "qty": p.qty,
                "avg_entry": p.avg_entry,
                "market_value": mv,
                "unrealized_pl": upl,
                "unrealized_pl_pct": round(upl_pct, 2) if upl_pct is not None else None,
            }
        )
    pos_rows.sort(key=lambda r: abs(r.get("unrealized_pl") or 0), reverse=True)

    order_rows: list[dict[str, Any]] = []
    filled_count = 0
    open_count = 0
    realized_est = 0.0
    for o in orders:
        st = o.status.value if hasattr(o.status, "value") else str(o.status)
        side = o.side.value if hasattr(o.side, "value") else str(o.side)
        otype = o.order_type.value if hasattr(o.order_type, "value") else str(o.order_type)
        if st in {"filled", "partial"}:
            filled_count += 1
        if st in {"open", "pending", "partial"}:
            open_count += 1
        order_rows.append(
            {
                "id": o.id,
                "symbol": o.symbol,
                "side": side,
                "qty": o.qty,
                "order_type": otype,
                "status": st,
                "filled_qty": o.filled_qty,
                "filled_avg_price": o.filled_avg_price,
                "limit_price": o.limit_price,
                "stop_price": o.stop_price,
                "submitted_at": o.submitted_at,
            }
        )

    cash = float(acct.cash or 0)
    equity = float(acct.equity or 0)
    return {
        "broker": broker.profile.id,
        "broker_name": broker.profile.name,
        "live": broker.profile.id != "paper",
        "supports_stop_processing": isinstance(broker, PaperBroker),
        "cash": cash,
        "equity": equity,
        "buying_power": float(acct.buying_power or 0),
        "summary": {
            "position_count": len(pos_rows),
            "open_orders": open_count,
            "filled_orders": filled_count,
            "positions_market_value": round(total_mv, 2),
            "unrealized_pl": round(total_upl, 2),
            "unrealized_pl_pct": round((total_upl / (equity - total_upl)) * 100, 2)
            if equity - total_upl
            else None,
            "cash_pct": round((cash / equity) * 100, 1) if equity else None,
        },
        "positions": pos_rows,
        "orders": order_rows,
        "realized_note": "Unrealized P&L from open positions. Filled blotter is trade activity (broker-dependent realized).",
        "realized_est": realized_est,
    }


def portfolio_error_payload(exc: Exception) -> dict[str, Any]:
    return {
        "error": str(exc),
        "broker": None,
        "positions": [],
        "orders": [],
        "summary": {},
    }

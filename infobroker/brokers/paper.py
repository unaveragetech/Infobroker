"""Local paper broker — fills against Yahoo delayed quotes. No API keys."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from uuid import uuid4

from infobroker.brokers.base import (
    Account,
    BrokerAdapter,
    BrokerError,
    BrokerProfile,
    Order,
    OrderRequest,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    Quote,
)
from infobroker.data.market import get_last_price


PAPER_PROFILE = BrokerProfile(
    id="paper",
    name="Infobroker Paper (local)",
    rank=0,
    speed_score=10,
    reliability_score=10,
    cost_note="Free - simulated fills vs yfinance (and other data providers)",
    paper_supported=True,
    requires_local_gateway=False,
    notes="Best for learning and demos. Not exchange-routed.",
)


class PaperBroker(BrokerAdapter):
    profile = PAPER_PROFILE

    def __init__(self, ledger_path: Path, starting_cash: float = 10_000.0, user: str = "default"):
        self.ledger_path = ledger_path
        self.starting_cash = starting_cash
        self.user = user
        self._state = self._load()

    def _load(self) -> dict:
        if self.ledger_path.exists():
            data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
            if self.user in data:
                return data[self.user]
        return {
            "cash": self.starting_cash,
            "positions": {},  # symbol -> {qty, avg_entry}
            "orders": [],
        }

    def _save(self) -> None:
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        all_data: dict = {}
        if self.ledger_path.exists():
            all_data = json.loads(self.ledger_path.read_text(encoding="utf-8"))
        all_data[self.user] = self._state
        self.ledger_path.write_text(json.dumps(all_data, indent=2), encoding="utf-8")

    def get_quote(self, symbol: str) -> Quote:
        last = get_last_price(symbol)
        if last is None:
            raise BrokerError(f"No quote for {symbol}")
        return Quote(symbol=symbol.upper(), bid=last, ask=last, last=last)

    def get_account(self) -> Account:
        equity = self._state["cash"]
        for symbol, pos in self._state["positions"].items():
            try:
                price = get_last_price(symbol) or pos["avg_entry"]
            except Exception:
                price = pos["avg_entry"]
            equity += pos["qty"] * price
        return Account(
            cash=round(self._state["cash"], 2),
            equity=round(equity, 2),
            buying_power=round(self._state["cash"], 2),
            broker=self.profile.id,
        )

    def list_positions(self) -> list[Position]:
        out: list[Position] = []
        for symbol, pos in self._state["positions"].items():
            qty = float(pos["qty"])
            if qty == 0:
                continue
            price = get_last_price(symbol) or float(pos["avg_entry"])
            mv = qty * price
            pl = (price - float(pos["avg_entry"])) * qty
            out.append(
                Position(
                    symbol=symbol,
                    qty=qty,
                    avg_entry=float(pos["avg_entry"]),
                    market_value=round(mv, 2),
                    unrealized_pl=round(pl, 2),
                )
            )
        return out

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        orders = [self._dict_to_order(o) for o in self._state["orders"]]
        if status:
            orders = [o for o in orders if o.status.value == status]
        return orders

    def place_order(self, request: OrderRequest) -> Order:
        symbol = request.symbol.upper()
        qty = float(request.qty)
        if qty <= 0:
            raise BrokerError("Quantity must be positive")

        quote = self.get_quote(symbol)
        fill_price = quote.last

        if request.order_type == OrderType.LIMIT and request.limit_price is not None:
            if request.side == OrderSide.BUY and fill_price > request.limit_price:
                return self._open_order(request, OrderStatus.OPEN)
            if request.side == OrderSide.SELL and fill_price < request.limit_price:
                return self._open_order(request, OrderStatus.OPEN)
            fill_price = request.limit_price

        if request.order_type in {OrderType.STOP, OrderType.STOP_LIMIT}:
            # Keep resting until monitored (manual tick or automation loop)
            return self._open_order(request, OrderStatus.OPEN)

        return self._fill(request, fill_price)

    def cancel_order(self, order_id: str) -> Order:
        for raw in self._state["orders"]:
            if raw["id"] == order_id and raw["status"] in {
                OrderStatus.OPEN.value,
                OrderStatus.PENDING.value,
            }:
                raw["status"] = OrderStatus.CANCELED.value
                self._save()
                return self._dict_to_order(raw)
        raise BrokerError(f"Order not cancelable: {order_id}")

    def process_open_stops(self) -> list[Order]:
        """Check resting stop orders against latest quotes (call from automation)."""
        filled: list[Order] = []
        for raw in list(self._state["orders"]):
            if raw["status"] != OrderStatus.OPEN.value:
                continue
            if raw["order_type"] not in {OrderType.STOP.value, OrderType.STOP_LIMIT.value}:
                continue
            stop = raw.get("stop_price")
            if stop is None:
                continue
            try:
                last = get_last_price(raw["symbol"])
            except Exception:
                continue
            if last is None:
                continue
            side = OrderSide(raw["side"])
            triggered = (side == OrderSide.SELL and last <= stop) or (
                side == OrderSide.BUY and last >= stop
            )
            if not triggered:
                continue
            req = OrderRequest(
                symbol=raw["symbol"],
                side=side,
                qty=float(raw["qty"]),
                order_type=OrderType.MARKET,
                client_order_id=raw.get("client_order_id", uuid4().hex),
            )
            raw["status"] = OrderStatus.CANCELED.value
            order = self._fill(req, last)
            filled.append(order)
        return filled

    def _open_order(self, request: OrderRequest, status: OrderStatus) -> Order:
        order = Order(
            id=uuid4().hex,
            symbol=request.symbol.upper(),
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=status,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )
        self._state["orders"].append(self._order_to_dict(order))
        self._save()
        return order

    def _fill(self, request: OrderRequest, price: float) -> Order:
        symbol = request.symbol.upper()
        qty = float(request.qty)
        cost = qty * price
        positions = self._state["positions"]

        if request.side == OrderSide.BUY:
            if cost > self._state["cash"]:
                order = Order(
                    id=uuid4().hex,
                    symbol=symbol,
                    side=request.side,
                    qty=qty,
                    order_type=request.order_type,
                    status=OrderStatus.REJECTED,
                    limit_price=request.limit_price,
                    stop_price=request.stop_price,
                    raw={"reason": "insufficient_cash"},
                )
                self._state["orders"].append(self._order_to_dict(order))
                self._save()
                return order
            self._state["cash"] -= cost
            prev = positions.get(symbol, {"qty": 0.0, "avg_entry": 0.0})
            new_qty = prev["qty"] + qty
            avg = (
                ((prev["avg_entry"] * prev["qty"]) + cost) / new_qty if new_qty else 0.0
            )
            positions[symbol] = {"qty": new_qty, "avg_entry": avg}
        else:
            held = positions.get(symbol, {"qty": 0.0, "avg_entry": 0.0})
            if held["qty"] < qty:
                order = Order(
                    id=uuid4().hex,
                    symbol=symbol,
                    side=request.side,
                    qty=qty,
                    order_type=request.order_type,
                    status=OrderStatus.REJECTED,
                    raw={"reason": "insufficient_shares"},
                )
                self._state["orders"].append(self._order_to_dict(order))
                self._save()
                return order
            self._state["cash"] += cost
            remaining = held["qty"] - qty
            if remaining <= 1e-9:
                positions.pop(symbol, None)
            else:
                positions[symbol] = {"qty": remaining, "avg_entry": held["avg_entry"]}

        order = Order(
            id=uuid4().hex,
            symbol=symbol,
            side=request.side,
            qty=qty,
            order_type=request.order_type,
            status=OrderStatus.FILLED,
            filled_qty=qty,
            filled_avg_price=round(price, 4),
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )
        self._state["orders"].append(self._order_to_dict(order))
        self._save()
        return order

    @staticmethod
    def _order_to_dict(order: Order) -> dict:
        return {
            "id": order.id,
            "symbol": order.symbol,
            "side": order.side.value,
            "qty": order.qty,
            "order_type": order.order_type.value,
            "status": order.status.value,
            "filled_qty": order.filled_qty,
            "filled_avg_price": order.filled_avg_price,
            "limit_price": order.limit_price,
            "stop_price": order.stop_price,
            "submitted_at": order.submitted_at,
            "raw": order.raw,
        }

    @staticmethod
    def _dict_to_order(raw: dict) -> Order:
        return Order(
            id=raw["id"],
            symbol=raw["symbol"],
            side=OrderSide(raw["side"]),
            qty=float(raw["qty"]),
            order_type=OrderType(raw["order_type"]),
            status=OrderStatus(raw["status"]),
            filled_qty=float(raw.get("filled_qty", 0)),
            filled_avg_price=raw.get("filled_avg_price"),
            limit_price=raw.get("limit_price"),
            stop_price=raw.get("stop_price"),
            submitted_at=raw.get("submitted_at", ""),
            raw=raw.get("raw", {}),
        )

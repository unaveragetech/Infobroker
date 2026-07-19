"""Tradier adapter — free-capable rank #3 (equities + options path)."""

from __future__ import annotations

from typing import Any, Optional

import requests

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
from infobroker.config import Settings

TRADIER_PROFILE = BrokerProfile(
    id="tradier",
    name="Tradier",
    rank=3,
    speed_score=7,
    reliability_score=8,
    cost_note="$0 stocks; options ~$0.35/contract",
    paper_supported=True,
    requires_local_gateway=False,
    notes="Primary free execution #3. Sandbox quotes may be delayed ~15m.",
)


class TradierBroker(BrokerAdapter):
    profile = TRADIER_PROFILE

    def __init__(self, settings: Settings):
        if not settings.tradier_token or not settings.tradier_account:
            raise BrokerError("TRADIER_ACCESS_TOKEN and TRADIER_ACCOUNT_ID are required")
        self.token = settings.tradier_token
        self.account = settings.tradier_account
        self.base = (
            "https://sandbox.tradier.com/v1"
            if settings.tradier_sandbox
            else "https://api.tradier.com/v1"
        )
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
            }
        )

    def _get(self, path: str, **params: Any) -> Any:
        resp = self.session.get(f"{self.base}{path}", params=params, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Tradier GET {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, data: dict) -> Any:
        resp = self.session.post(f"{self.base}{path}", data=data, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Tradier POST {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def get_account(self) -> Account:
        data = self._get(f"/accounts/{self.account}/balances")
        bal = data.get("balances") or data
        cash = float(bal.get("total_cash") or bal.get("cash", 0) or 0)
        equity = float(bal.get("total_equity") or bal.get("equity", cash) or cash)
        bp = float(bal.get("stock_buying_power") or bal.get("buying_power") or cash)
        return Account(cash=cash, equity=equity, buying_power=bp, broker=self.profile.id)

    def get_quote(self, symbol: str) -> Quote:
        data = self._get("/markets/quotes", symbols=symbol.upper())
        q = (data.get("quotes") or {}).get("quote")
        if isinstance(q, list):
            q = q[0] if q else None
        if not q:
            raise BrokerError(f"No Tradier quote for {symbol}")
        last = float(q.get("last") or q.get("close") or 0)
        return Quote(
            symbol=symbol.upper(),
            bid=float(q["bid"]) if q.get("bid") is not None else None,
            ask=float(q["ask"]) if q.get("ask") is not None else None,
            last=last,
        )

    def list_positions(self) -> list[Position]:
        data = self._get(f"/accounts/{self.account}/positions")
        positions = (data.get("positions") or {}).get("position") or []
        if isinstance(positions, dict):
            positions = [positions]
        out: list[Position] = []
        for p in positions:
            qty = float(p.get("quantity") or 0)
            cost = float(p.get("cost_basis") or 0)
            avg = (cost / qty) if qty else 0.0
            out.append(
                Position(
                    symbol=str(p.get("symbol")),
                    qty=qty,
                    avg_entry=avg,
                    market_value=float(p.get("date_acquired") and 0 or 0),
                )
            )
        return out

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        data = self._get(f"/accounts/{self.account}/orders")
        orders = (data.get("orders") or {}).get("order") or []
        if isinstance(orders, dict):
            orders = [orders]
        mapped = [self._map_order(o) for o in orders]
        if status:
            mapped = [o for o in mapped if o.status.value == status]
        return mapped

    def place_order(self, request: OrderRequest) -> Order:
        type_map = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
        }
        payload = {
            "class": "equity",
            "symbol": request.symbol.upper(),
            "side": "buy" if request.side == OrderSide.BUY else "sell",
            "quantity": str(int(request.qty) if request.qty == int(request.qty) else request.qty),
            "type": type_map[request.order_type],
            "duration": request.time_in_force,
        }
        if request.limit_price is not None:
            payload["price"] = str(request.limit_price)
        if request.stop_price is not None:
            payload["stop"] = str(request.stop_price)
        data = self._post(f"/accounts/{self.account}/orders", payload)
        order = (data.get("order") or data)
        return self._map_order(order)

    def cancel_order(self, order_id: str) -> Order:
        resp = self.session.delete(
            f"{self.base}/accounts/{self.account}/orders/{order_id}", timeout=30
        )
        if resp.status_code >= 400:
            raise BrokerError(f"Tradier cancel failed: {resp.status_code} {resp.text}")
        return Order(
            id=order_id,
            symbol="",
            side=OrderSide.BUY,
            qty=0,
            order_type=OrderType.MARKET,
            status=OrderStatus.CANCELED,
        )

    @staticmethod
    def _map_order(raw: dict) -> Order:
        status_raw = str(raw.get("status", "pending")).lower()
        status = {
            "filled": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "open": OrderStatus.OPEN,
            "pending": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
        }.get(status_raw, OrderStatus.PENDING)
        side = OrderSide.BUY if "buy" in str(raw.get("side", "buy")).lower() else OrderSide.SELL
        return Order(
            id=str(raw.get("id")),
            symbol=str(raw.get("symbol", "")),
            side=side,
            qty=float(raw.get("quantity") or 0),
            order_type=OrderType.MARKET,
            status=status,
            filled_qty=float(raw.get("exec_quantity") or 0),
            filled_avg_price=float(raw["avg_fill_price"]) if raw.get("avg_fill_price") else None,
            raw=raw,
        )

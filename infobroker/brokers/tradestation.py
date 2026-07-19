"""TradeStation adapter — rank #5 free retail option."""

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

TRADESTATION_PROFILE = BrokerProfile(
    id="tradestation",
    name="TradeStation",
    rank=92,
    speed_score=6,
    reliability_score=6,
    cost_note="$0 stocks on typical retail plans",
    paper_supported=True,
    requires_local_gateway=False,
    notes="Sim account available. Stricter REST rate windows.",
)


class TradeStationBroker(BrokerAdapter):
    profile = TRADESTATION_PROFILE

    def __init__(self, settings: Settings):
        if not settings.tradestation_token or not settings.tradestation_account:
            raise BrokerError(
                "TRADESTATION_ACCESS_TOKEN and TRADESTATION_ACCOUNT_ID are required"
            )
        self.token = settings.tradestation_token
        self.account = settings.tradestation_account
        self.base = (
            "https://sim-api.tradestation.com/v3"
            if settings.tradestation_sim
            else "https://api.tradestation.com/v3"
        )
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.token}"})

    def _get(self, path: str, **params: Any) -> Any:
        resp = self.session.get(f"{self.base}{path}", params=params, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"TradeStation GET {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, payload: dict) -> Any:
        resp = self.session.post(f"{self.base}{path}", json=payload, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"TradeStation POST {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def get_account(self) -> Account:
        data = self._get(f"/brokerage/accounts/{self.account}/balances")
        bals = data.get("Balances") or data.get("balances") or [data]
        row = bals[0] if isinstance(bals, list) else bals
        cash = float(row.get("CashBalance") or row.get("cash_balance") or 0)
        equity = float(row.get("Equity") or row.get("equity") or cash)
        return Account(cash=cash, equity=equity, buying_power=cash, broker=self.profile.id)

    def get_quote(self, symbol: str) -> Quote:
        data = self._get(f"/marketdata/quotes/{symbol.upper()}")
        quotes = data.get("Quotes") or data.get("quotes") or [data]
        q = quotes[0] if isinstance(quotes, list) else quotes
        last = float(q.get("Last") or q.get("last") or 0)
        return Quote(
            symbol=symbol.upper(),
            bid=float(q["Bid"]) if q.get("Bid") is not None else None,
            ask=float(q["Ask"]) if q.get("Ask") is not None else None,
            last=last,
        )

    def list_positions(self) -> list[Position]:
        data = self._get(f"/brokerage/accounts/{self.account}/positions")
        rows = data.get("Positions") or data.get("positions") or []
        return [
            Position(
                symbol=str(r.get("Symbol") or r.get("symbol")),
                qty=float(r.get("Quantity") or r.get("quantity") or 0),
                avg_entry=float(r.get("AveragePrice") or r.get("average_price") or 0),
                market_value=float(r.get("MarketValue") or r.get("market_value") or 0),
                unrealized_pl=float(r.get("UnrealizedProfitLoss") or 0),
            )
            for r in rows
        ]

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        data = self._get(f"/brokerage/accounts/{self.account}/orders")
        rows = data.get("Orders") or data.get("orders") or []
        return [
            Order(
                id=str(r.get("OrderID") or r.get("order_id")),
                symbol=str(r.get("Symbol") or ""),
                side=OrderSide.BUY
                if str(r.get("TradeAction", r.get("side", ""))).upper().startswith("BUY")
                else OrderSide.SELL,
                qty=float(r.get("Quantity") or 0),
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                raw=r,
            )
            for r in rows
        ]

    def place_order(self, request: OrderRequest) -> Order:
        action = "BUY" if request.side == OrderSide.BUY else "SELL"
        order_type = {
            OrderType.MARKET: "Market",
            OrderType.LIMIT: "Limit",
            OrderType.STOP: "StopMarket",
            OrderType.STOP_LIMIT: "StopLimit",
        }[request.order_type]
        payload: dict[str, Any] = {
            "AccountID": self.account,
            "Symbol": request.symbol.upper(),
            "Quantity": str(request.qty),
            "OrderType": order_type,
            "TradeAction": action,
            "TimeInForce": {"Duration": "DAY"},
            "Route": "Intelligent",
        }
        if request.limit_price is not None:
            payload["LimitPrice"] = str(request.limit_price)
        if request.stop_price is not None:
            payload["StopPrice"] = str(request.stop_price)
        data = self._post(f"/orderexecution/orders", payload)
        return Order(
            id=str(data.get("OrderID") or data.get("order_id") or "submitted"),
            symbol=request.symbol.upper(),
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=OrderStatus.PENDING,
            raw=data,
        )

    def cancel_order(self, order_id: str) -> Order:
        resp = self.session.delete(
            f"{self.base}/orderexecution/orders/{order_id}", timeout=30
        )
        if resp.status_code >= 400:
            raise BrokerError(f"TradeStation cancel failed: {resp.status_code} {resp.text}")
        return Order(
            id=order_id,
            symbol="",
            side=OrderSide.BUY,
            qty=0,
            order_type=OrderType.MARKET,
            status=OrderStatus.CANCELED,
        )

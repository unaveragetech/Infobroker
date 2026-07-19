"""Alpaca Markets adapter — recommended free broker (#1)."""

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

ALPACA_PROFILE = BrokerProfile(
    id="alpaca",
    name="Alpaca",
    rank=1,
    speed_score=8,
    reliability_score=9,
    cost_note="$0 stock commissions; free IEX data tier",
    paper_supported=True,
    requires_local_gateway=False,
    notes="Best default for Infobroker. Same API for paper and live.",
)

_STATUS_MAP = {
    "new": OrderStatus.OPEN,
    "accepted": OrderStatus.OPEN,
    "pending_new": OrderStatus.PENDING,
    "filled": OrderStatus.FILLED,
    "partially_filled": OrderStatus.PARTIALLY_FILLED,
    "canceled": OrderStatus.CANCELED,
    "cancelled": OrderStatus.CANCELED,
    "rejected": OrderStatus.REJECTED,
    "expired": OrderStatus.CANCELED,
}


class AlpacaBroker(BrokerAdapter):
    profile = ALPACA_PROFILE

    def __init__(self, settings: Settings):
        if not settings.alpaca_key or not settings.alpaca_secret:
            raise BrokerError("ALPACA_API_KEY and ALPACA_API_SECRET are required")
        self.key = settings.alpaca_key
        self.secret = settings.alpaca_secret
        self.base = (
            "https://paper-api.alpaca.markets"
            if settings.alpaca_paper
            else "https://api.alpaca.markets"
        )
        self.data_base = "https://data.alpaca.markets"
        self.session = requests.Session()
        self.session.headers.update(
            {
                "APCA-API-KEY-ID": self.key,
                "APCA-API-SECRET-KEY": self.secret,
            }
        )

    def _get(self, path: str, base: Optional[str] = None, **params: Any) -> Any:
        url = f"{base or self.base}{path}"
        resp = self.session.get(url, params=params, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Alpaca GET {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, payload: dict) -> Any:
        resp = self.session.post(f"{self.base}{path}", json=payload, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Alpaca POST {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _delete(self, path: str) -> Any:
        resp = self.session.delete(f"{self.base}{path}", timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Alpaca DELETE {path}: {resp.status_code} {resp.text}")
        if resp.text:
            return resp.json()
        return {}

    def get_account(self) -> Account:
        data = self._get("/v2/account")
        return Account(
            cash=float(data.get("cash", 0)),
            equity=float(data.get("equity", 0)),
            buying_power=float(data.get("buying_power", 0)),
            broker=self.profile.id,
        )

    def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.upper()
        try:
            data = self._get(
                f"/v2/stocks/{symbol}/quotes/latest",
                base=self.data_base,
            )
            q = data.get("quote") or data
            bid = float(q["bp"]) if q.get("bp") is not None else None
            ask = float(q["ap"]) if q.get("ap") is not None else None
            last = ask or bid or 0.0
            return Quote(symbol=symbol, bid=bid, ask=ask, last=last)
        except BrokerError:
            # Fall back to trade endpoint / snapshot-less path
            trade = self._get(
                f"/v2/stocks/{symbol}/trades/latest",
                base=self.data_base,
            )
            t = trade.get("trade") or trade
            last = float(t.get("p") or 0)
            return Quote(symbol=symbol, bid=last, ask=last, last=last)

    def list_positions(self) -> list[Position]:
        rows = self._get("/v2/positions")
        return [
            Position(
                symbol=r["symbol"],
                qty=float(r["qty"]),
                avg_entry=float(r["avg_entry_price"]),
                market_value=float(r.get("market_value") or 0),
                unrealized_pl=float(r.get("unrealized_pl") or 0),
            )
            for r in rows
        ]

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        params: dict[str, Any] = {"limit": 100}
        if status:
            params["status"] = status
        else:
            params["status"] = "all"
        rows = self._get("/v2/orders", **params)
        return [self._map_order(r) for r in rows]

    def place_order(self, request: OrderRequest) -> Order:
        payload: dict[str, Any] = {
            "symbol": request.symbol.upper(),
            "qty": str(request.qty),
            "side": request.side.value,
            "type": request.order_type.value.replace("_", "-")
            if request.order_type != OrderType.STOP_LIMIT
            else "stop_limit",
            "time_in_force": request.time_in_force,
            "client_order_id": request.client_order_id,
        }
        # Alpaca uses stop / stop_limit / limit / market
        type_map = {
            OrderType.MARKET: "market",
            OrderType.LIMIT: "limit",
            OrderType.STOP: "stop",
            OrderType.STOP_LIMIT: "stop_limit",
        }
        payload["type"] = type_map[request.order_type]
        if request.limit_price is not None:
            payload["limit_price"] = str(request.limit_price)
        if request.stop_price is not None:
            payload["stop_price"] = str(request.stop_price)
        data = self._post("/v2/orders", payload)
        return self._map_order(data)

    def cancel_order(self, order_id: str) -> Order:
        self._delete(f"/v2/orders/{order_id}")
        data = self._get(f"/v2/orders/{order_id}")
        return self._map_order(data)

    def place_bracket(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> list[Order]:
        payload: dict[str, Any] = {
            "symbol": symbol.upper(),
            "qty": str(qty),
            "side": side.value,
            "type": "market",
            "time_in_force": "day",
            "order_class": "bracket",
        }
        if take_profit is not None:
            payload["take_profit"] = {"limit_price": str(take_profit)}
        if stop_loss is not None:
            payload["stop_loss"] = {"stop_price": str(stop_loss)}
        data = self._post("/v2/orders", payload)
        # Parent order; legs may appear in nested structure
        orders = [self._map_order(data)]
        for leg in data.get("legs") or []:
            orders.append(self._map_order(leg))
        return orders

    @staticmethod
    def _map_order(raw: dict) -> Order:
        status = _STATUS_MAP.get(str(raw.get("status", "")).lower(), OrderStatus.PENDING)
        otype_raw = str(raw.get("type", "market")).replace("-", "_")
        try:
            otype = OrderType(otype_raw)
        except ValueError:
            otype = OrderType.MARKET
        return Order(
            id=str(raw.get("id")),
            symbol=str(raw.get("symbol")),
            side=OrderSide(str(raw.get("side", "buy")).lower()),
            qty=float(raw.get("qty") or raw.get("filled_qty") or 0),
            order_type=otype,
            status=status,
            filled_qty=float(raw.get("filled_qty") or 0),
            filled_avg_price=float(raw["filled_avg_price"])
            if raw.get("filled_avg_price")
            else None,
            limit_price=float(raw["limit_price"]) if raw.get("limit_price") else None,
            stop_price=float(raw["stop_price"]) if raw.get("stop_price") else None,
            submitted_at=str(raw.get("submitted_at") or ""),
            raw=raw,
        )

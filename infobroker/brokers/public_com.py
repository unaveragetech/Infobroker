"""Public.com Individual Trader API adapter — free execution rank #2."""

from __future__ import annotations

from typing import Any, Optional
from uuid import uuid4

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

PUBLIC_PROFILE = BrokerProfile(
    id="public",
    name="Public",
    rank=2,
    speed_score=8,
    reliability_score=8,
    cost_note="$0 stock/ETF commissions via Individual API",
    paper_supported=False,
    requires_local_gateway=False,
    notes="Personal secret -> bearer token. Live account - use paper broker first.",
)


class PublicBroker(BrokerAdapter):
    profile = PUBLIC_PROFILE

    def __init__(self, settings: Settings):
        if not settings.public_secret:
            raise BrokerError("PUBLIC_PERSONAL_SECRET is required")
        self.base = settings.public_base.rstrip("/")
        self.secret = settings.public_secret
        self.account_id = settings.public_account_id
        self.session = requests.Session()
        self._token: Optional[str] = None
        self._authenticate()
        if not self.account_id:
            self.account_id = self._discover_account()

    def _authenticate(self) -> None:
        resp = requests.post(
            f"{self.base}/userapiauthservice/personal/access-tokens",
            json={"secret": self.secret, "validityInMinutes": 60},
            headers={"Content-Type": "application/json"},
            timeout=30,
        )
        if resp.status_code >= 400:
            raise BrokerError(f"Public auth failed: {resp.status_code} {resp.text}")
        self._token = resp.json().get("accessToken")
        if not self._token:
            raise BrokerError("Public auth returned no accessToken")
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self._token}",
                "Content-Type": "application/json",
            }
        )

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.base}{path}"
        resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code == 401:
            self._authenticate()
            resp = self.session.request(method, url, timeout=30, **kwargs)
        if resp.status_code >= 400:
            raise BrokerError(f"Public {method} {path}: {resp.status_code} {resp.text}")
        if not resp.text:
            return {}
        return resp.json()

    def _discover_account(self) -> str:
        data = self._request("GET", "/userapigateway/trading/account")
        accounts = data.get("accounts") or []
        if not accounts:
            raise BrokerError("No Public brokerage accounts found")
        # Prefer brokerage cash/margin accounts
        for acct in accounts:
            if str(acct.get("accountType", "")).upper() in {"BROKERAGE", ""}:
                return str(acct["accountId"])
        return str(accounts[0]["accountId"])

    def get_account(self) -> Account:
        data = self._request(
            "GET", f"/userapigateway/trading/{self.account_id}/portfolio/v2"
        )
        # Portfolio payloads vary; be defensive
        equity = float(
            data.get("equity")
            or data.get("totalValue")
            or data.get("buyingPower")
            or 0
        )
        cash = float(
            data.get("cash")
            or data.get("buyingPower")
            or data.get("settledCash")
            or 0
        )
        # Alternate nested shape
        if equity == 0 and isinstance(data.get("account"), dict):
            acct = data["account"]
            equity = float(acct.get("equity") or acct.get("totalValue") or 0)
            cash = float(acct.get("cash") or acct.get("buyingPower") or cash)
        return Account(
            cash=cash,
            equity=equity or cash,
            buying_power=cash,
            broker=self.profile.id,
        )

    def get_quote(self, symbol: str) -> Quote:
        symbol = symbol.upper()
        # Public market quotes endpoint (CLI uses similar path)
        try:
            data = self._request(
                "GET",
                "/userapigateway/marketdata/quotes",
                params={"symbols": symbol},
            )
        except BrokerError:
            data = self._request(
                "POST",
                "/userapigateway/marketdata/quotes",
                json={"symbols": [symbol]},
            )
        quotes = data.get("quotes") or data.get("Quotes") or data
        row: dict[str, Any] = {}
        if isinstance(quotes, list) and quotes:
            row = quotes[0]
        elif isinstance(quotes, dict):
            row = quotes.get(symbol) or next(iter(quotes.values()), quotes)
        last = float(
            row.get("last")
            or row.get("lastPrice")
            or row.get("price")
            or row.get("close")
            or 0
        )
        if last <= 0:
            raise BrokerError(f"No Public quote for {symbol}")
        bid = row.get("bid") or row.get("bidPrice")
        ask = row.get("ask") or row.get("askPrice")
        return Quote(
            symbol=symbol,
            bid=float(bid) if bid is not None else None,
            ask=float(ask) if ask is not None else None,
            last=last,
        )

    def list_positions(self) -> list[Position]:
        data = self._request(
            "GET", f"/userapigateway/trading/{self.account_id}/portfolio/v2"
        )
        positions = data.get("positions") or data.get("holdings") or []
        out: list[Position] = []
        for p in positions:
            inst = p.get("instrument") or {}
            symbol = str(
                p.get("symbol") or inst.get("symbol") or inst.get("ticker") or ""
            )
            if not symbol:
                continue
            qty = float(p.get("quantity") or p.get("qty") or 0)
            avg = float(p.get("averagePrice") or p.get("avgPrice") or p.get("costBasis") or 0)
            if qty and avg > 1000 and p.get("costBasis"):
                # costBasis sometimes total; normalize if needed later
                pass
            out.append(
                Position(
                    symbol=symbol,
                    qty=qty,
                    avg_entry=avg,
                    market_value=float(p.get("marketValue") or 0),
                    unrealized_pl=float(p.get("unrealizedProfitLoss") or p.get("gain") or 0),
                )
            )
        return out

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        data = self._request(
            "GET", f"/userapigateway/trading/{self.account_id}/order"
        )
        rows = data.get("orders") or data.get("order") or data
        if isinstance(rows, dict):
            rows = rows.get("orders") or []
        mapped = [self._map_order(o) for o in (rows or [])]
        if status:
            mapped = [o for o in mapped if o.status.value == status]
        return mapped

    def place_order(self, request: OrderRequest) -> Order:
        order_id = str(uuid4())
        type_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP",
            OrderType.STOP_LIMIT: "STOP_LIMIT",
        }
        payload: dict[str, Any] = {
            "orderId": order_id,
            "instrument": {"symbol": request.symbol.upper(), "type": "EQUITY"},
            "orderSide": "BUY" if request.side == OrderSide.BUY else "SELL",
            "orderType": type_map[request.order_type],
            "expiration": {"timeInForce": request.time_in_force.upper()},
            "quantity": str(request.qty),
            "useMargin": False,
        }
        if request.limit_price is not None:
            payload["limitPrice"] = str(request.limit_price)
        if request.stop_price is not None:
            payload["stopPrice"] = str(request.stop_price)
        data = self._request(
            "POST",
            f"/userapigateway/trading/{self.account_id}/order",
            json=payload,
        )
        return Order(
            id=str(data.get("orderId") or order_id),
            symbol=request.symbol.upper(),
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=OrderStatus.PENDING,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
            raw=data if isinstance(data, dict) else {"response": data},
        )

    def cancel_order(self, order_id: str) -> Order:
        self._request(
            "DELETE",
            f"/userapigateway/trading/{self.account_id}/order/{order_id}",
        )
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
        side_raw = str(raw.get("orderSide") or raw.get("side") or "BUY").upper()
        side = OrderSide.BUY if side_raw.startswith("BUY") else OrderSide.SELL
        status_raw = str(raw.get("status") or raw.get("orderStatus") or "PENDING").lower()
        status = {
            "filled": OrderStatus.FILLED,
            "canceled": OrderStatus.CANCELED,
            "cancelled": OrderStatus.CANCELED,
            "rejected": OrderStatus.REJECTED,
            "open": OrderStatus.OPEN,
            "pending": OrderStatus.PENDING,
            "partially_filled": OrderStatus.PARTIALLY_FILLED,
        }.get(status_raw, OrderStatus.PENDING)
        inst = raw.get("instrument") or {}
        return Order(
            id=str(raw.get("orderId") or raw.get("id") or ""),
            symbol=str(inst.get("symbol") or raw.get("symbol") or ""),
            side=side,
            qty=float(raw.get("quantity") or raw.get("qty") or 0),
            order_type=OrderType.MARKET,
            status=status,
            filled_qty=float(raw.get("filledQuantity") or 0),
            filled_avg_price=float(raw["averagePrice"]) if raw.get("averagePrice") else None,
            raw=raw,
        )

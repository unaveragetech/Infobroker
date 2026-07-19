"""Interactive Brokers Client Portal adapter — rank #2 (speed), higher ops cost."""

from __future__ import annotations

from typing import Any, Optional

import requests
import urllib3

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

# Local Client Portal uses a self-signed cert by default.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

IBKR_PROFILE = BrokerProfile(
    id="ibkr",
    name="Interactive Brokers",
    rank=90,
    speed_score=9,
    reliability_score=6,
    cost_note="Lite often $0 US stocks; market data subscriptions may apply",
    paper_supported=True,
    requires_local_gateway=True,
    notes="Optional adapter (not in primary free ranking). Needs local Gateway.",
)


class IBKRBroker(BrokerAdapter):
    profile = IBKR_PROFILE

    def __init__(self, settings: Settings):
        self.base = settings.ibkr_base.rstrip("/")
        self.session = requests.Session()
        self.session.verify = False

    def _get(self, path: str, **params: Any) -> Any:
        try:
            resp = self.session.get(f"{self.base}{path}", params=params, timeout=30)
        except requests.RequestException as exc:
            raise BrokerError(
                "IBKR Client Portal unreachable. Start the Gateway and log in first."
            ) from exc
        if resp.status_code >= 400:
            raise BrokerError(f"IBKR GET {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, payload: dict) -> Any:
        try:
            resp = self.session.post(f"{self.base}{path}", json=payload, timeout=30)
        except requests.RequestException as exc:
            raise BrokerError("IBKR Client Portal unreachable.") from exc
        if resp.status_code >= 400:
            raise BrokerError(f"IBKR POST {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def healthcheck(self) -> dict[str, Any]:
        try:
            data = self._get("/v1/api/iserver/auth/status")
            return {
                "broker": self.profile.id,
                "ok": bool(data.get("authenticated")),
                "details": data,
            }
        except BrokerError as exc:
            return {"broker": self.profile.id, "ok": False, "error": str(exc)}

    def get_account(self) -> Account:
        accounts = self._get("/v1/api/portfolio/accounts")
        if not accounts:
            raise BrokerError("No IBKR accounts returned — authenticate in Client Portal")
        account_id = accounts[0].get("id") or accounts[0].get("accountId")
        summary = self._get(f"/v1/api/portfolio/{account_id}/summary")
        cash = float(summary.get("totalcashvalue", {}).get("amount", 0) or 0)
        equity = float(summary.get("netliquidation", {}).get("amount", cash) or cash)
        return Account(cash=cash, equity=equity, buying_power=equity, broker=self.profile.id)

    def get_quote(self, symbol: str) -> Quote:
        # Resolve conid then snapshot — simplified search path
        found = self._get("/v1/api/iserver/secdef/search", symbol=symbol.upper())
        if not found:
            raise BrokerError(f"IBKR symbol not found: {symbol}")
        conid = found[0].get("conid")
        snap = self._get(
            "/v1/api/iserver/marketdata/snapshot",
            conids=str(conid),
            fields="31,84,86",
        )
        row = snap[0] if isinstance(snap, list) and snap else {}
        last = float(row.get("31") or row.get("84") or 0)
        return Quote(
            symbol=symbol.upper(),
            bid=float(row["84"]) if row.get("84") else None,
            ask=float(row["86"]) if row.get("86") else None,
            last=last,
        )

    def list_positions(self) -> list[Position]:
        accounts = self._get("/v1/api/portfolio/accounts")
        account_id = accounts[0].get("id") or accounts[0].get("accountId")
        rows = self._get(f"/v1/api/portfolio/{account_id}/positions/0")
        out: list[Position] = []
        for r in rows or []:
            out.append(
                Position(
                    symbol=str(r.get("contractDesc") or r.get("ticker") or ""),
                    qty=float(r.get("position") or 0),
                    avg_entry=float(r.get("avgCost") or 0),
                    market_value=float(r.get("mktValue") or 0),
                    unrealized_pl=float(r.get("unrealizedPnl") or 0),
                )
            )
        return out

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        data = self._get("/v1/api/iserver/account/orders")
        orders = data.get("orders") if isinstance(data, dict) else data
        mapped = [
            Order(
                id=str(o.get("orderId") or o.get("id")),
                symbol=str(o.get("ticker") or ""),
                side=OrderSide.BUY if str(o.get("side", "")).upper().startswith("B") else OrderSide.SELL,
                qty=float(o.get("totalSize") or o.get("qty") or 0),
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                raw=o,
            )
            for o in (orders or [])
        ]
        return mapped

    def place_order(self, request: OrderRequest) -> Order:
        accounts = self._get("/v1/api/portfolio/accounts")
        account_id = accounts[0].get("id") or accounts[0].get("accountId")
        found = self._get("/v1/api/iserver/secdef/search", symbol=request.symbol.upper())
        if not found:
            raise BrokerError(f"IBKR symbol not found: {request.symbol}")
        conid = found[0]["conid"]
        order: dict[str, Any] = {
            "conid": conid,
            "orderType": {
                OrderType.MARKET: "MKT",
                OrderType.LIMIT: "LMT",
                OrderType.STOP: "STP",
                OrderType.STOP_LIMIT: "STP LMT",
            }[request.order_type],
            "side": "BUY" if request.side == OrderSide.BUY else "SELL",
            "tif": "DAY",
            "quantity": request.qty,
        }
        if request.limit_price is not None:
            order["price"] = request.limit_price
        if request.stop_price is not None:
            order["auxPrice"] = request.stop_price
        data = self._post(
            f"/v1/api/iserver/account/{account_id}/orders",
            {"orders": [order]},
        )
        first = data[0] if isinstance(data, list) and data else data
        return Order(
            id=str(first.get("order_id") or first.get("id") or ""),
            symbol=request.symbol.upper(),
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=OrderStatus.PENDING,
            raw=first if isinstance(first, dict) else {"response": first},
        )

    def cancel_order(self, order_id: str) -> Order:
        self._post(f"/v1/api/iserver/account/order/{order_id}/cancel", {})
        return Order(
            id=order_id,
            symbol="",
            side=OrderSide.BUY,
            qty=0,
            order_type=OrderType.MARKET,
            status=OrderStatus.CANCELED,
        )

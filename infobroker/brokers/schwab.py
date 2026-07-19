"""Charles Schwab Trader API adapter — rank #4 free retail path."""

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

SCHWAB_PROFILE = BrokerProfile(
    id="schwab",
    name="Charles Schwab",
    rank=91,
    speed_score=6,
    reliability_score=7,
    cost_note="$0 US stock commissions",
    paper_supported=False,
    requires_local_gateway=False,
    notes="OAuth app required. Good if you already hold funds at Schwab.",
)


class SchwabBroker(BrokerAdapter):
    profile = SCHWAB_PROFILE
    TOKEN_URL = "https://api.schwabapi.com/v1/oauth/token"
    TRADER_BASE = "https://api.schwabapi.com/trader/v1"
    MARKET_BASE = "https://api.schwabapi.com/marketdata/v1"

    def __init__(self, settings: Settings):
        if not settings.schwab_key or not settings.schwab_secret or not settings.schwab_refresh:
            raise BrokerError(
                "SCHWAB_APP_KEY, SCHWAB_APP_SECRET, and SCHWAB_REFRESH_TOKEN are required"
            )
        self.key = settings.schwab_key
        self.secret = settings.schwab_secret
        self.refresh = settings.schwab_refresh
        self.account_hash = settings.schwab_account
        self.session = requests.Session()
        self._access_token: Optional[str] = None
        self._ensure_token()

    def _ensure_token(self) -> None:
        resp = requests.post(
            self.TOKEN_URL,
            data={"grant_type": "refresh_token", "refresh_token": self.refresh},
            auth=(self.key, self.secret),
            timeout=30,
        )
        if resp.status_code >= 400:
            raise BrokerError(f"Schwab token refresh failed: {resp.status_code} {resp.text}")
        data = resp.json()
        self._access_token = data["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {self._access_token}"})

    def _get(self, base: str, path: str, **params: Any) -> Any:
        resp = self.session.get(f"{base}{path}", params=params, timeout=30)
        if resp.status_code == 401:
            self._ensure_token()
            resp = self.session.get(f"{base}{path}", params=params, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Schwab GET {path}: {resp.status_code} {resp.text}")
        return resp.json()

    def _post(self, path: str, payload: dict) -> Any:
        resp = self.session.post(f"{self.TRADER_BASE}{path}", json=payload, timeout=30)
        if resp.status_code >= 400:
            raise BrokerError(f"Schwab POST {path}: {resp.status_code} {resp.text}")
        return resp.json() if resp.text else {}

    def get_account(self) -> Account:
        accounts = self._get(self.TRADER_BASE, "/accounts")
        if not accounts:
            raise BrokerError("No Schwab accounts")
        acct = accounts[0].get("securitiesAccount") or accounts[0]
        if not self.account_hash:
            self.account_hash = str(acct.get("hashValue") or acct.get("accountNumber"))
        bals = acct.get("currentBalances") or {}
        cash = float(bals.get("cashBalance") or bals.get("availableFunds") or 0)
        equity = float(bals.get("liquidationValue") or bals.get("equity") or cash)
        return Account(cash=cash, equity=equity, buying_power=cash, broker=self.profile.id)

    def get_quote(self, symbol: str) -> Quote:
        data = self._get(self.MARKET_BASE, f"/quotes/{symbol.upper()}")
        q = data.get(symbol.upper()) or next(iter(data.values()), {})
        quote = q.get("quote") or q
        last = float(quote.get("lastPrice") or quote.get("mark") or 0)
        return Quote(
            symbol=symbol.upper(),
            bid=float(quote["bidPrice"]) if quote.get("bidPrice") is not None else None,
            ask=float(quote["askPrice"]) if quote.get("askPrice") is not None else None,
            last=last,
        )

    def list_positions(self) -> list[Position]:
        if not self.account_hash:
            self.get_account()
        data = self._get(self.TRADER_BASE, f"/accounts/{self.account_hash}", fields="positions")
        acct = data.get("securitiesAccount") or data
        out: list[Position] = []
        for p in acct.get("positions") or []:
            inst = p.get("instrument") or {}
            qty = float(p.get("longQuantity") or 0) - float(p.get("shortQuantity") or 0)
            out.append(
                Position(
                    symbol=str(inst.get("symbol", "")),
                    qty=qty,
                    avg_entry=float(p.get("averagePrice") or 0),
                    market_value=float(p.get("marketValue") or 0),
                )
            )
        return out

    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        if not self.account_hash:
            self.get_account()
        data = self._get(self.TRADER_BASE, f"/accounts/{self.account_hash}/orders")
        return [
            Order(
                id=str(o.get("orderId")),
                symbol=str(((o.get("orderLegCollection") or [{}])[0].get("instrument") or {}).get("symbol", "")),
                side=OrderSide.BUY
                if "BUY" in str(((o.get("orderLegCollection") or [{}])[0].get("instruction", "")))
                else OrderSide.SELL,
                qty=float(o.get("quantity") or 0),
                order_type=OrderType.MARKET,
                status=OrderStatus.OPEN,
                raw=o,
            )
            for o in data or []
        ]

    def place_order(self, request: OrderRequest) -> Order:
        if not self.account_hash:
            self.get_account()
        order_type_map = {
            OrderType.MARKET: "MARKET",
            OrderType.LIMIT: "LIMIT",
            OrderType.STOP: "STOP",
            OrderType.STOP_LIMIT: "STOP_LIMIT",
        }
        payload: dict[str, Any] = {
            "orderType": order_type_map[request.order_type],
            "session": "NORMAL",
            "duration": "DAY",
            "orderStrategyType": "SINGLE",
            "orderLegCollection": [
                {
                    "instruction": "BUY" if request.side == OrderSide.BUY else "SELL",
                    "quantity": request.qty,
                    "instrument": {"symbol": request.symbol.upper(), "assetType": "EQUITY"},
                }
            ],
        }
        if request.limit_price is not None:
            payload["price"] = request.limit_price
        if request.stop_price is not None:
            payload["stopPrice"] = request.stop_price
        self._post(f"/accounts/{self.account_hash}/orders", payload)
        return Order(
            id="submitted",
            symbol=request.symbol.upper(),
            side=request.side,
            qty=request.qty,
            order_type=request.order_type,
            status=OrderStatus.PENDING,
            limit_price=request.limit_price,
            stop_price=request.stop_price,
        )

    def cancel_order(self, order_id: str) -> Order:
        if not self.account_hash:
            self.get_account()
        resp = self.session.delete(
            f"{self.TRADER_BASE}/accounts/{self.account_hash}/orders/{order_id}",
            timeout=30,
        )
        if resp.status_code >= 400:
            raise BrokerError(f"Schwab cancel failed: {resp.status_code} {resp.text}")
        return Order(
            id=order_id,
            symbol="",
            side=OrderSide.BUY,
            qty=0,
            order_type=OrderType.MARKET,
            status=OrderStatus.CANCELED,
        )

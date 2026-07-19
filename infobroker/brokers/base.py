"""Shared broker contract for paper and live adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from uuid import uuid4


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"


class OrderStatus(str, Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELED = "canceled"
    REJECTED = "rejected"


@dataclass
class Quote:
    symbol: str
    bid: Optional[float]
    ask: Optional[float]
    last: float
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Position:
    symbol: str
    qty: float
    avg_entry: float
    market_value: float = 0.0
    unrealized_pl: float = 0.0


@dataclass
class Account:
    cash: float
    equity: float
    buying_power: float
    currency: str = "USD"
    broker: str = "unknown"


@dataclass
class OrderRequest:
    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType = OrderType.MARKET
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    time_in_force: str = "day"
    client_order_id: str = field(default_factory=lambda: uuid4().hex)


@dataclass
class Order:
    id: str
    symbol: str
    side: OrderSide
    qty: float
    order_type: OrderType
    status: OrderStatus
    filled_qty: float = 0.0
    filled_avg_price: Optional[float] = None
    limit_price: Optional[float] = None
    stop_price: Optional[float] = None
    submitted_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class BrokerProfile:
    """Metadata used to rank and display free broker options."""

    id: str
    name: str
    rank: int
    speed_score: int  # 1–10 higher = faster
    reliability_score: int  # 1–10 higher = more reliable for app use
    cost_note: str
    paper_supported: bool
    requires_local_gateway: bool
    notes: str


class BrokerError(Exception):
    """Broker adapter failure."""


class BrokerAdapter(ABC):
    profile: BrokerProfile

    @abstractmethod
    def get_account(self) -> Account:
        raise NotImplementedError

    @abstractmethod
    def get_quote(self, symbol: str) -> Quote:
        raise NotImplementedError

    @abstractmethod
    def list_positions(self) -> list[Position]:
        raise NotImplementedError

    @abstractmethod
    def list_orders(self, status: Optional[str] = None) -> list[Order]:
        raise NotImplementedError

    @abstractmethod
    def place_order(self, request: OrderRequest) -> Order:
        raise NotImplementedError

    @abstractmethod
    def cancel_order(self, order_id: str) -> Order:
        raise NotImplementedError

    def place_bracket(
        self,
        symbol: str,
        side: OrderSide,
        qty: float,
        take_profit: Optional[float] = None,
        stop_loss: Optional[float] = None,
    ) -> list[Order]:
        """Default: entry + optional stop. Brokers may override with native brackets."""
        orders: list[Order] = []
        entry = self.place_order(
            OrderRequest(symbol=symbol, side=side, qty=qty, order_type=OrderType.MARKET)
        )
        orders.append(entry)
        if stop_loss is not None and entry.status == OrderStatus.FILLED:
            exit_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            stop = self.place_order(
                OrderRequest(
                    symbol=symbol,
                    side=exit_side,
                    qty=qty,
                    order_type=OrderType.STOP,
                    stop_price=stop_loss,
                )
            )
            orders.append(stop)
        if take_profit is not None and entry.status == OrderStatus.FILLED:
            exit_side = OrderSide.SELL if side == OrderSide.BUY else OrderSide.BUY
            limit = self.place_order(
                OrderRequest(
                    symbol=symbol,
                    side=exit_side,
                    qty=qty,
                    order_type=OrderType.LIMIT,
                    limit_price=take_profit,
                )
            )
            orders.append(limit)
        return orders

    def healthcheck(self) -> dict[str, Any]:
        account = self.get_account()
        return {
            "broker": self.profile.id,
            "ok": True,
            "cash": account.cash,
            "equity": account.equity,
        }

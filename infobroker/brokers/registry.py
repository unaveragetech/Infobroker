"""Broker factory — primary free execution: Alpaca, Public, Tradier."""

from __future__ import annotations

from typing import Callable

from infobroker.brokers.alpaca import ALPACA_PROFILE, AlpacaBroker
from infobroker.brokers.base import BrokerAdapter, BrokerError, BrokerProfile
from infobroker.brokers.ibkr import IBKR_PROFILE, IBKRBroker
from infobroker.brokers.paper import PAPER_PROFILE, PaperBroker
from infobroker.brokers.public_com import PUBLIC_PROFILE, PublicBroker
from infobroker.brokers.schwab import SCHWAB_PROFILE, SchwabBroker
from infobroker.brokers.tradestation import TRADESTATION_PROFILE, TradeStationBroker
from infobroker.brokers.tradier import TRADIER_PROFILE, TradierBroker
from infobroker.config import Settings, get_settings

# Primary free execution ranking (user-specified)
PRIMARY_PROFILES: list[BrokerProfile] = [
    ALPACA_PROFILE,
    PUBLIC_PROFILE,
    TRADIER_PROFILE,
]

OPTIONAL_PROFILES: list[BrokerProfile] = [
    IBKR_PROFILE,
    SCHWAB_PROFILE,
    TRADESTATION_PROFILE,
]


def ranked_free_brokers() -> list[BrokerProfile]:
    return sorted(PRIMARY_PROFILES, key=lambda p: p.rank)


def create_broker(
    name: str | None = None,
    settings: Settings | None = None,
    user: str = "default",
) -> BrokerAdapter:
    settings = settings or get_settings()
    broker_id = (name or settings.broker).strip().lower()

    factories: dict[str, Callable[[], BrokerAdapter]] = {
        "paper": lambda: PaperBroker(
            ledger_path=settings.ledger_path,
            starting_cash=settings.starting_cash,
            user=user,
        ),
        "alpaca": lambda: AlpacaBroker(settings),
        "public": lambda: PublicBroker(settings),
        "tradier": lambda: TradierBroker(settings),
        "ibkr": lambda: IBKRBroker(settings),
        "schwab": lambda: SchwabBroker(settings),
        "tradestation": lambda: TradeStationBroker(settings),
    }
    if broker_id not in factories:
        raise BrokerError(
            f"Unknown broker '{broker_id}'. Choose: {', '.join(factories)}"
        )
    return factories[broker_id]()


def describe_brokers() -> str:
    lines = [
        "Execution brokers (free / programmatic) — ranked by speed + reliability:\n"
    ]
    for p in ranked_free_brokers():
        lines.append(
            f"  #{p.rank} {p.name} [{p.id}]\n"
            f"     speed={p.speed_score}/10  reliability={p.reliability_score}/10\n"
            f"     cost: {p.cost_note}\n"
            f"     {p.notes}"
        )
    lines.append(
        "\nMarket data: yfinance (primary), Finnhub, Alpha Vantage"
    )
    lines.append("Local paper broker (no keys): INFOBROKER_BROKER=paper")
    lines.append(
        "Optional adapters also registered: ibkr, schwab, tradestation"
    )
    return "\n".join(lines)

"""Pre-trade risk checks — teach and block bad practices."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from infobroker.brokers.base import Account, OrderRequest, OrderSide, Position


@dataclass
class RiskLimits:
    max_position_pct: float = 0.10  # 10% of equity per position
    max_daily_loss_pct: float = 0.03
    require_stop_on_live: bool = True
    min_buying_power: float = 1.0


@dataclass
class RiskVerdict:
    allowed: bool
    warnings: list[str]
    blockers: list[str]

    @property
    def message(self) -> str:
        parts = []
        if self.blockers:
            parts.append("BLOCKED: " + "; ".join(self.blockers))
        if self.warnings:
            parts.append("WARN: " + "; ".join(self.warnings))
        return " | ".join(parts) if parts else "OK"


def evaluate_order(
    request: OrderRequest,
    account: Account,
    positions: list[Position],
    last_price: float,
    *,
    stop_price: Optional[float] = None,
    is_live: bool = False,
    limits: Optional[RiskLimits] = None,
) -> RiskVerdict:
    limits = limits or RiskLimits()
    warnings: list[str] = []
    blockers: list[str] = []

    notional = abs(request.qty * last_price)
    if account.equity <= 0:
        blockers.append("Account equity is zero")
        return RiskVerdict(False, warnings, blockers)

    position_pct = notional / account.equity
    if position_pct > limits.max_position_pct:
        blockers.append(
            f"Position size {position_pct:.1%} exceeds max {limits.max_position_pct:.0%} of equity"
        )
    elif position_pct > limits.max_position_pct * 0.7:
        warnings.append(
            f"Large size ({position_pct:.1%} of equity). Consider scaling in."
        )

    if request.side == OrderSide.BUY and notional > account.buying_power:
        blockers.append("Insufficient buying power")

    if request.side == OrderSide.SELL:
        held = next((p for p in positions if p.symbol == request.symbol.upper()), None)
        if not held or held.qty < request.qty:
            blockers.append("Cannot sell more shares than you hold (no naked short in v1)")

    effective_stop = stop_price or request.stop_price
    if is_live and limits.require_stop_on_live and request.side == OrderSide.BUY:
        if effective_stop is None:
            blockers.append(
                "Live buys require a stop-loss. Set stop_price or use a bracket order."
            )

    if effective_stop is not None and request.side == OrderSide.BUY:
        if effective_stop >= last_price:
            blockers.append("Stop-loss must be below current price for long entries")
        else:
            risk_pct = (last_price - effective_stop) / last_price
            if risk_pct > 0.08:
                warnings.append(
                    f"Wide stop ({risk_pct:.1%} risk). Teaching tip: tighter invalidation is safer while learning."
                )

    if account.buying_power < limits.min_buying_power and request.side == OrderSide.BUY:
        blockers.append("Buying power too low")

    return RiskVerdict(allowed=not blockers, warnings=warnings, blockers=blockers)


def teaching_checklist(symbol: str, side: str, thesis: str = "") -> list[str]:
    return [
        f"Symbol: {symbol.upper()} — do you know the catalyst or setup?",
        f"Side: {side.upper()} — what proves you wrong (invalidation)?",
        "Size: risk ≤ 1% of equity on the stop distance?",
        "Chart: trend, level, and volume agree — or are you chasing?",
        "Plan: take-profit and stop set before entry?",
        *( [f"Thesis noted: {thesis}"] if thesis else ["Write a one-line thesis before sending."] ),
    ]

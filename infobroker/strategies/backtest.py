"""Minimal backtester over OHLCV — same signals can later drive live/paper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pandas as pd

from infobroker.data.indicators import sma
from infobroker.data.market import fetch_ohlcv


SignalFn = Callable[[pd.DataFrame], pd.Series]


@dataclass
class BacktestResult:
    symbol: str
    start: str
    end: str
    trades: int
    total_return_pct: float
    max_drawdown_pct: float
    equity_curve: pd.Series


def sma_crossover_signal(fast: int = 20, slow: int = 50) -> SignalFn:
    def _signal(df: pd.DataFrame) -> pd.Series:
        close = df["Close"]
        f = sma(close, fast)
        s = sma(close, slow)
        raw = (f > s).astype(int) - (f < s).astype(int)
        # Position: 1 long, 0 flat (no short in v1 learner mode)
        return (raw > 0).astype(int)

    return _signal


def run_backtest(
    symbol: str,
    start: str,
    end: str,
    signal_fn: SignalFn | None = None,
    starting_cash: float = 10_000.0,
) -> BacktestResult:
    df = fetch_ohlcv(symbol, start, end)
    if df.empty:
        raise ValueError(f"No data for {symbol}")
    signal_fn = signal_fn or sma_crossover_signal()
    signal = signal_fn(df).reindex(df.index).fillna(0)
    close = df["Close"].astype(float)

    cash = starting_cash
    shares = 0.0
    equity = []
    trades = 0
    prev = 0

    for ts, price in close.items():
        pos = int(signal.loc[ts])
        if pos == 1 and prev == 0 and cash > 0:
            shares = cash / float(price)
            cash = 0.0
            trades += 1
        elif pos == 0 and prev == 1 and shares > 0:
            cash = shares * float(price)
            shares = 0.0
            trades += 1
        prev = pos
        equity.append(cash + shares * float(price))

    curve = pd.Series(equity, index=close.index, name="equity")
    ret = (curve.iloc[-1] / starting_cash - 1.0) * 100
    peak = curve.cummax()
    dd = ((curve / peak) - 1.0).min() * 100
    return BacktestResult(
        symbol=symbol.upper(),
        start=start,
        end=end,
        trades=trades,
        total_return_pct=round(float(ret), 2),
        max_drawdown_pct=round(float(dd), 2),
        equity_curve=curve,
    )

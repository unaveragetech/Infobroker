"""Base strategy catalog — free yfinance backtests, no signup."""

from __future__ import annotations

from typing import Any, Callable

import pandas as pd

from infobroker.data.indicators import macd_series, rsi_series, sma
from infobroker.strategies.backtest import SignalFn, run_backtest, sma_crossover_signal


def rsi_mean_reversion(period: int = 14, low: float = 30, high: float = 70) -> SignalFn:
    def _signal(df: pd.DataFrame) -> pd.Series:
        rsi = rsi_series(df["Close"], period)
        # Enter long when oversold; exit when overbought
        pos = pd.Series(0, index=df.index, dtype=int)
        long = False
        for i, ts in enumerate(df.index):
            v = rsi.iloc[i]
            if pd.isna(v):
                pos.iloc[i] = int(long)
                continue
            if not long and v <= low:
                long = True
            elif long and v >= high:
                long = False
            pos.iloc[i] = int(long)
        return pos

    return _signal


def macd_cross_signal() -> SignalFn:
    def _signal(df: pd.DataFrame) -> pd.Series:
        macd = macd_series(df["Close"].astype(float))
        return (macd["macd_line"] > macd["signal_line"]).fillna(False).astype(int)

    return _signal


def buy_and_hold_signal() -> SignalFn:
    def _signal(df: pd.DataFrame) -> pd.Series:
        s = pd.Series(1, index=df.index, dtype=int)
        return s

    return _signal


def breakout_20d_signal() -> SignalFn:
    def _signal(df: pd.DataFrame) -> pd.Series:
        high = df["High"].astype(float)
        close = df["Close"].astype(float)
        prior_high = high.rolling(20).max().shift(1)
        pos = pd.Series(0, index=df.index, dtype=int)
        long = False
        for i, ts in enumerate(df.index):
            ph = prior_high.iloc[i]
            c = close.iloc[i]
            if pd.isna(ph):
                pos.iloc[i] = 0
                continue
            if not long and c > ph:
                long = True
            elif long and c < sma(close, 20).iloc[i]:
                long = False
            pos.iloc[i] = int(long)
        return pos

    return _signal


STRATEGIES: dict[str, dict[str, Any]] = {
    "sma_crossover": {
        "id": "sma_crossover",
        "name": "SMA Crossover (20/50)",
        "description": "Long when SMA20 > SMA50; flat otherwise. Classic trend follower.",
        "cost": "Free (yfinance)",
        "signup": False,
        "factory": sma_crossover_signal,
    },
    "rsi_mean_reversion": {
        "id": "rsi_mean_reversion",
        "name": "RSI Mean Reversion",
        "description": "Buy RSI≤30, exit RSI≥70. Teaching tool — can fail in strong trends.",
        "cost": "Free (yfinance)",
        "signup": False,
        "factory": rsi_mean_reversion,
    },
    "macd_cross": {
        "id": "macd_cross",
        "name": "MACD Cross",
        "description": "Long when MACD line crosses above signal; flat when below.",
        "cost": "Free (yfinance)",
        "signup": False,
        "factory": macd_cross_signal,
    },
    "buy_hold": {
        "id": "buy_hold",
        "name": "Buy & Hold",
        "description": "Benchmark: stay long the whole period.",
        "cost": "Free (yfinance)",
        "signup": False,
        "factory": buy_and_hold_signal,
    },
    "breakout_20d": {
        "id": "breakout_20d",
        "name": "20-Day Breakout",
        "description": "Enter on close above prior 20-day high; exit under SMA20.",
        "cost": "Free (yfinance)",
        "signup": False,
        "factory": breakout_20d_signal,
    },
}


def list_strategies() -> list[dict[str, Any]]:
    return [
        {
            "id": s["id"],
            "name": s["name"],
            "description": s["description"],
            "cost": s["cost"],
            "signup_required": s["signup"],
        }
        for s in STRATEGIES.values()
    ]


def run_strategy_backtest(
    strategy_id: str,
    symbol: str,
    start: str,
    end: str,
    starting_cash: float = 10_000.0,
) -> dict[str, Any]:
    meta = STRATEGIES.get(strategy_id)
    if not meta:
        raise ValueError(f"Unknown strategy: {strategy_id}. Choose from {list(STRATEGIES)}")
    factory: Callable[..., SignalFn] = meta["factory"]
    result = run_backtest(
        symbol,
        start,
        end,
        signal_fn=factory(),
        starting_cash=starting_cash,
    )
    # Benchmark buy & hold on same window
    bh = run_backtest(
        symbol,
        start,
        end,
        signal_fn=buy_and_hold_signal(),
        starting_cash=starting_cash,
    )
    curve = result.equity_curve
    equity_pts = []
    if curve is not None and not curve.empty:
        step = max(1, len(curve) // 80)
        for i, (ts, val) in enumerate(curve.items()):
            if i % step == 0 or i == len(curve) - 1:
                equity_pts.append(
                    {
                        "t": ts.isoformat() if hasattr(ts, "isoformat") else str(ts),
                        "v": round(float(val), 2),
                    }
                )
    return {
        "strategy": meta["id"],
        "strategy_name": meta["name"],
        "symbol": result.symbol,
        "start": result.start,
        "end": result.end,
        "trades": result.trades,
        "total_return_pct": result.total_return_pct,
        "max_drawdown_pct": result.max_drawdown_pct,
        "buy_hold_return_pct": bh.total_return_pct,
        "vs_buy_hold_pct": round(result.total_return_pct - bh.total_return_pct, 2),
        "data_source": "yfinance (free, no signup)",
        "equity": equity_pts,
    }

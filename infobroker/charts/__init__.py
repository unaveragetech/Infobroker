"""Chart helpers — thin wrappers; full suite remains in legacy graph.py."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

from infobroker.data.indicators import calculate_rsi, sma
from infobroker.data.market import fetch_ohlcv


def save_price_ma_chart(
    symbol: str,
    start: str,
    end: str,
    out_dir: str | Path = ".",
) -> Path:
    df = fetch_ohlcv(symbol, start, end)
    close = df["Close"]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(close.index, close, label="Close")
    ax.plot(close.index, sma(close, 50), label="MA50")
    ax.plot(close.index, sma(close, 200), label="MA200")
    ax.set_title(f"{symbol.upper()} price + MAs")
    ax.legend()
    ax.grid(True, alpha=0.3)
    out = Path(out_dir) / f"{symbol.upper()}_ma.png"
    fig.tight_layout()
    fig.savefig(out)
    plt.close(fig)
    return out


def latest_rsi(symbol: str, start: str, end: str) -> float | str:
    df = fetch_ohlcv(symbol, start, end)
    return calculate_rsi(df["Close"])

"""Extra multi-page insight content layered onto base lessons."""

from __future__ import annotations

from typing import Any

# Additional pages keyed by lesson id (appended after auto-built pages)
EXTRA_PAGES: dict[str, list[dict[str, Any]]] = {
    "candles": [
        {
            "title": "Timeframes & session context",
            "insight": (
                "A perfect hammer on the 1‑minute chart means little if the daily is "
                "breaking a multi-month low. Always name the timeframe before you name "
                "the pattern."
            ),
            "sections": [
                {
                    "heading": "Multi-timeframe stack",
                    "text": (
                        "Swing traders: daily for bias, 1H/15m for entry. Day traders: "
                        "15m/5m for structure, 1m only for trigger. If higher timeframe "
                        "is against you, cut size or skip."
                    ),
                },
                {
                    "heading": "Session opens",
                    "text": (
                        "The first 15–30 minutes often print long wicks as overnight "
                        "orders clear. Waiting for a settled open range can save you "
                        "from fake ‘reversal’ candles that are just auction noise."
                    ),
                },
            ],
            "examples": [
                {
                    "title": "Same candle, two meanings",
                    "detail": (
                        "A daily hammer at the 200‑day MA after a selloff is a swing "
                        "study. The identical shape on a 1‑minute chart into lunch "
                        "chop is usually noise — same picture, different homework."
                    ),
                }
            ],
            "chart": {"type": "candles_demo", "caption": "Context first: pattern + level + timeframe."},
            "quiz": {
                "q": "You see a hammer. What do you check before considering a long?",
                "a": "Timeframe bias, nearby support, and where the stop (wick low) would sit.",
            },
        },
        {
            "title": "From candle to ticket",
            "insight": (
                "Patterns do not place orders — you do. Translate every candle idea into "
                "entry, invalidation, and size before you touch Submit."
            ),
            "sections": [
                {
                    "heading": "Checklist after a signal candle",
                    "text": (
                        "1) Where is invalidation (beyond the wick)? 2) Is R acceptable? "
                        "3) Is volume confirming? 4) Does this match your playbook name? "
                        "If any answer is fuzzy, flat is allowed."
                    ),
                }
            ],
            "practice": [
                "Open Chart studio on a watchlist name and mark one rejection wick with a written stop.",
                "Preview a paper order that uses that stop — read the risk checklist.",
            ],
            "chart": {"type": "stops_demo", "caption": "Candle idea → stop under wick → sized ticket."},
        },
    ],
    "trend": [
        {
            "title": "Regime changes",
            "insight": (
                "Most losses come from trading yesterday’s regime. When SMA50 crosses "
                "below SMA200 or higher lows fail, your long playbook should go quieter."
            ),
            "sections": [
                {
                    "heading": "Early warnings",
                    "text": (
                        "Lower high against an uptrend, failed reclaim of SMA50, and "
                        "expanding volume on down days. One warning is a watch; a cluster "
                        "is a size-down or stand-aside signal."
                    ),
                }
            ],
            "chart": {"type": "trend_ma", "caption": "Watch for broken higher-low structure, not just MA slope."},
            "quiz": {
                "q": "Price is above SMA200 but below a falling SMA50. What regime is this?",
                "a": "Mixed / corrective — favor smaller size or wait for reclaim of SMA50.",
            },
        }
    ],
    "rsi": [
        {
            "title": "RSI in Infobroker tools",
            "insight": (
                "Desk scanner and Chart studio RSI are TA-Lib RSI(14) on yfinance "
                "closes. Treat them as the same language across backtests and live study."
            ),
            "sections": [
                {
                    "heading": "Link to strategies",
                    "text": (
                        "The Strategies tab RSI mean-reversion backtest is a teaching "
                        "tool — it will lose in strong trends. Use it to feel the failure "
                        "mode, not as a money printer."
                    ),
                }
            ],
            "chart": {"type": "rsi_demo", "caption": "RSI can stay extreme — that is the lesson."},
        }
    ],
    "risk": [
        {
            "title": "Risk across order types",
            "insight": (
                "Market brackets, stop entries, and stop-limits change how your planned "
                "1R shows up in fills. Know the difference before you size up."
            ),
            "sections": [
                {
                    "heading": "Gaps",
                    "text": (
                        "A stop market can fill worse than the stop price on a gap. Your "
                        "account risk % is a budget for those days — not a guarantee of "
                        "exact loss."
                    ),
                },
                {
                    "heading": "Paper practice",
                    "text": (
                        "On Infobroker paper, process stops deliberately. Feeling a stop "
                        "hit on a journaled idea builds the habit better than reading about it."
                    ),
                },
            ],
            "chart": {"type": "risk_demo", "caption": "Same dollar risk, different stop distances → different share counts."},
        }
    ],
    "chase": [
        {
            "title": "Rewiring the urge",
            "insight": (
                "Chasing is a timing error wrapped in a feeling. Replace ‘I need to be in’ "
                "with ‘I need my level’."
            ),
            "sections": [
                {
                    "heading": "Operational fix",
                    "text": (
                        "Set alerts at the retest. Use limit orders. If the move never "
                        "comes back, you did not ‘miss’ a good trade — you avoided a late one."
                    ),
                }
            ],
            "chart": {"type": "chase_demo", "caption": "Spike = study. Retest = plan."},
        }
    ],
    "support_resistance": [
        {
            "title": "Confluence scoring",
            "insight": (
                "Give a level a score: prior swing (+1), MA (+1), round number (+1), "
                "high-volume day (+1). Trade 3+ confluence; ignore lonely lines."
            ),
            "sections": [
                {
                    "heading": "When levels fail",
                    "text": (
                        "Failed levels become magnets the other way. A broken support "
                        "often retests as resistance — flip your bias, don’t argue with the break."
                    ),
                }
            ],
            "chart": {"type": "levels_demo", "caption": "Break → retest → role reversal."},
        }
    ],
    "volume": [
        {
            "title": "RVol on this desk",
            "insight": (
                "Volume Leaders and the RVol column answer ‘is anyone here?’ High RVol "
                "raises both opportunity and trap rate — tighten process, don’t loosen risk."
            ),
            "chart": {"type": "volume_demo", "caption": "Participation confirms or denies the break."},
        }
    ],
    "stops": [
        {
            "title": "Tutor walkthrough: place a stop",
            "insight": (
                "Open the order ticket → choose Market → set Stop loss under structure → "
                "Preview → Submit. On paper, later click Process paper stops when price tags it."
            ),
            "practice": [
                "Place a 1-share paper bracket with a real swing-low stop.",
                "Write the invalidation sentence: ‘I am wrong if price closes below ___.’",
            ],
            "chart": {"type": "stops_demo", "caption": "Invalidation first, size second."},
        }
    ],
    "macd": [
        {
            "title": "MACD vs price leadership",
            "insight": (
                "Price leads; MACD narrates. If they disagree at a level, believe price "
                "and use MACD only to time patience."
            ),
            "chart": {"type": "macd_demo", "caption": "Crosses need a level — or they are chatter."},
        }
    ],
    "playbook": [
        {
            "title": "Weekly review ritual",
            "insight": (
                "Every weekend: count trades in R, note which playbook name was used, "
                "and cut any setup that was improvisation."
            ),
            "sections": [
                {
                    "heading": "Learning tab",
                    "text": (
                        "Use the Learning tab Trade history panel to re-read what you "
                        "actually did — the story under each order is the tutor talking "
                        "about your tape, not a textbook."
                    ),
                }
            ],
            "chart": {"type": "playbook_demo", "caption": "Process loop beats inspiration."},
        }
    ],
}

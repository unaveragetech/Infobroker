"""Guided tutor: ways to trade — multi-page curriculum."""

from __future__ import annotations

from typing import Any

TUTOR_ID = "ways_to_trade"

TUTOR_CURRICULUM: dict[str, Any] = {
    "id": TUTOR_ID,
    "title": "Ways to trade (tutor path)",
    "level": "Tutor",
    "topics": ["market", "limit", "stop", "brackets", "swing", "intraday", "risk"],
    "body": (
        "A teacher-style path through every basic way you can trade on this desk — "
        "from market buys to brackets — with when to use each and how to practice."
    ),
    "overview": (
        "Think of this as sitting with a tutor. We will walk order types, styles "
        "(swing vs day), risk, and how Infobroker’s ticket, chart studio, and paper "
        "ledger fit together. Finish every page before you size up live."
    ),
    "pages": [
        {
            "title": "1 · What ‘a trade’ really is",
            "insight": (
                "A trade is a hypothesis with a price that proves you wrong. Without "
                "invalidation, you have a hope, not a trade."
            ),
            "sections": [
                {
                    "heading": "The four sentences",
                    "text": (
                        "1) Bias (bullish/bearish/range). 2) Trigger (what makes you enter). "
                        "3) Invalidation (stop). 4) Management (target or trail). Say them "
                        "out loud before Submit."
                    ),
                },
                {
                    "heading": "Paper first",
                    "text": (
                        "Infobroker defaults to paper. Use it until your process is boring. "
                        "Boring process + small live size later beats exciting guesses."
                    ),
                },
            ],
            "chart": {"type": "playbook_demo", "caption": "Hypothesis → ticket → journal."},
            "practice": ["Open Account and confirm you are on paper/sim mode."],
        },
        {
            "title": "2 · Market orders",
            "insight": (
                "Market means ‘take me to the current auction.’ Fast fills, less price "
                "control. Best when you already have a level and need certainty of entry."
            ),
            "sections": [
                {
                    "heading": "When a tutor says yes",
                    "text": (
                        "Breakout retest that just held, news already digested, or closing "
                        "a risk (getting flat). When a tutor says no: chasing a vertical bar."
                    ),
                },
                {
                    "heading": "On this desk",
                    "text": (
                        "Order ticket → Side Buy/Sell → Type Market → optional Stop loss / "
                        "Take profit for a bracket → Preview → Submit."
                    ),
                },
            ],
            "examples": [
                {
                    "title": "Clean market long",
                    "detail": (
                        "Pullback holds SMA20 on rising volume. You buy market 1 share with "
                        "stop under the pullback low. You accepted the spread to lock the idea."
                    ),
                }
            ],
            "chart": {"type": "trend_ma", "caption": "Market entry after the level proves itself."},
            "quiz": {
                "q": "Why preview even a market order?",
                "a": "To force risk, checklist, and size thinking before emotion clicks Submit.",
            },
        },
        {
            "title": "3 · Limit orders",
            "insight": (
                "Limit means ‘only at my price or better.’ More control, fill not guaranteed. "
                "This is how patient traders buy dips and sell rips."
            ),
            "sections": [
                {
                    "heading": "Tutor tip",
                    "text": (
                        "Place limits at your level before the move if you can. If price "
                        "never trades there, you were not ‘wrong’ — the setup never arrived."
                    ),
                },
                {
                    "heading": "On this desk",
                    "text": (
                        "Order type Limit → fill Limit price → Preview. Combine with a "
                        "protective stop after fill (or plan the stop before)."
                    ),
                },
            ],
            "chart": {"type": "levels_demo", "caption": "Limit rests at the level; chase buys the air above it."},
            "practice": ["Preview a limit buy 1% below last on a watchlist name (do not need to submit)."],
        },
        {
            "title": "4 · Stop & stop-limit entries",
            "insight": (
                "Stop entries are for breakout participation: ‘buy strength / sell weakness’ "
                "only after price proves the break. Stop-limit adds a limit cap — may miss the fill."
            ),
            "sections": [
                {
                    "heading": "Stop market vs stop-limit",
                    "text": (
                        "Stop market: triggers then markets you in — you get filled, price "
                        "may slip. Stop-limit: triggers then rests as limit — you may not fill "
                        "in a runaway move. Pick consciously."
                    ),
                },
                {
                    "heading": "On this desk",
                    "text": (
                        "Order type Stop or Stop-limit → Stop price (and Limit if needed). "
                        "This is different from Stop loss on a market bracket (that protects "
                        "an open position)."
                    ),
                },
            ],
            "chart": {"type": "chase_demo", "caption": "Breakout stop sits above resistance — not in the middle of the spike."},
        },
        {
            "title": "5 · Brackets: entry + stop + target",
            "insight": (
                "A bracket packages the plan: get in, define pain, define reward. It is "
                "how you stop negotiating with yourself after the fill."
            ),
            "sections": [
                {
                    "heading": "R framing",
                    "text": (
                        "If stop is 1R away and target is 2R, you need well under a 50% win "
                        "rate to break even before costs — still, the math keeps you honest."
                    ),
                },
                {
                    "heading": "Paper stops",
                    "text": (
                        "Local paper resting stops fill when you Process paper stops (or the "
                        "assistant runs process_stops). Practice that loop."
                    ),
                },
            ],
            "chart": {"type": "risk_demo", "caption": "Entry, −1R stop, +2R target — one picture."},
            "practice": ["Submit a 1-share paper market buy with stop and take-profit filled in."],
        },
        {
            "title": "6 · Swing trading style",
            "insight": (
                "Swing trading holds days to weeks. Bias from daily/weekly structure; "
                "entries from pullbacks to MAs or broken levels. Fewer decisions, wider stops, "
                "smaller share counts for the same dollar risk."
            ),
            "sections": [
                {
                    "heading": "Infobroker fit",
                    "text": (
                        "Chart studio on 6–12 months, Strategies SMA/MACD backtests for "
                        "feel, scanner for RSI/MA stack context — then a patient limit or "
                        "market on the pullback."
                    ),
                }
            ],
            "chart": {"type": "trend_ma", "caption": "Swing: higher timeframe bias + pullback entry."},
        },
        {
            "title": "7 · Intraday / day style",
            "insight": (
                "Day trading closes by the session. Needs liquidity, hard no-trade rules "
                "(first minutes, FOMC), and faster invalidation. Most beginners lose here "
                "by overtrading — start with one setup only."
            ),
            "sections": [
                {
                    "heading": "Tutor rules of thumb",
                    "text": (
                        "Trade names with elevated RVol, respect VWAP/open range, and "
                        "predefine max trades per day. If you cannot watch the screen, "
                        "you are not day trading — you are gambling with delays."
                    ),
                }
            ],
            "chart": {"type": "volume_demo", "caption": "Intraday edges need participation (volume)."},
        },
        {
            "title": "8 · Mean reversion vs trend following",
            "insight": (
                "Mean reversion fades extremes back to a mean (VWAP/MA/RSI bands). Trend "
                "following buys strength / sells weakness. Mixing them without naming which "
                "you are doing is how playbooks melt."
            ),
            "sections": [
                {
                    "heading": "Which lesson to open",
                    "text": (
                        "Mean reversion → RSI + support lessons. Trend → trend + volume + "
                        "chase (so you don’t buy late). Strategies tab lets you backtest both "
                        "feelings for free with yfinance."
                    ),
                }
            ],
            "chart": {"type": "rsi_demo", "caption": "Same RSI number: fade in a range, respect in a trend."},
            "quiz": {
                "q": "Price makes higher highs above rising SMA200 and RSI is 72. Fade or respect?",
                "a": "Respect / tighten risk — overbought can persist in trends; fading is advanced.",
            },
        },
        {
            "title": "9 · Shorting & selling (risk-aware)",
            "insight": (
                "Selling to close a long is risk reduction. Opening a short needs borrow/"
                "broker support and different risk (squeezes). Infobroker paper blocks naked "
                "shorts in v1 — use that as a teaching guardrail."
            ),
            "sections": [
                {
                    "heading": "Tutor framing",
                    "text": (
                        "Learn to sell winners and losers on longs first. When shorting is "
                        "available live, require the same stop discipline as longs — hope is "
                        "not a hedge."
                    ),
                }
            ],
            "chart": {"type": "levels_demo", "caption": "Failed resistance is often clearer than shorting thin air."},
        },
        {
            "title": "10 · Your homework loop on this desk",
            "insight": (
                "Tutor close-out: Scan → Chart studio → matching Learn lesson → Risk "
                "preview → Ticket → Learning tab journal. Skip a box and the lesson was theater."
            ),
            "sections": [
                {
                    "heading": "Next actions",
                    "text": (
                        "1) Finish any unread skill lessons in the sidebar. 2) Place one "
                        "paper bracket that matches a named setup. 3) Re-open this trade in "
                        "the Learning tab history and read the idea story. 4) Ask Grapevine "
                        "to quiz you on one page of this tutor path."
                    ),
                }
            ],
            "chart": {"type": "playbook_demo", "caption": "Graduate when the loop is automatic."},
            "practice": [
                "Run Find trades once, then reject or accept with a written playbook name.",
                "Open Learning → Trade history and explain your last fill in two sentences.",
            ],
            "takeaways": [
                "Name the order type and the style before you click.",
                "Invalidation is mandatory.",
                "Paper reps beat theory.",
            ],
        },
    ],
}


def get_tutor() -> dict[str, Any]:
    pages = TUTOR_CURRICULUM["pages"]
    return {
        **TUTOR_CURRICULUM,
        "page_count": len(pages),
        "is_tutor": True,
    }


def list_tutor_summary() -> dict[str, Any]:
    t = TUTOR_CURRICULUM
    return {
        "id": t["id"],
        "title": t["title"],
        "body": t["body"],
        "level": t["level"],
        "topics": t["topics"],
        "page_count": len(t["pages"]),
        "is_tutor": True,
    }

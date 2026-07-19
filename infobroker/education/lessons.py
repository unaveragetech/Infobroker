"""Structured trading lessons for the Learn sidebar + detail viewer."""

from __future__ import annotations

from typing import Any

# Each lesson: id, title, teaser/body (sidebar), level, topics, sections,
# terms, examples, chart (demo type + caption), takeaways, practice

LESSONS: list[dict[str, Any]] = [
    {
        "id": "candles",
        "title": "Read a candle",
        "level": "Beginner",
        "topics": ["OHLC", "wicks", "rejection", "engulfing"],
        "body": (
            "Each candle shows open, high, low, close. A long upper wick after a rally "
            "often means buyers lost control (rejection). Don't buy the wick — wait for "
            "a close back above the level."
        ),
        "overview": (
            "Candlesticks compress four prices into one visual. The body is the distance "
            "between open and close; wicks (shadows) show the extremes. Color usually "
            "means close ≥ open (bullish) vs close < open (bearish). Context beats any "
            "single pattern — a hammer at support is not the same as a hammer mid-trend."
        ),
        "sections": [
            {
                "heading": "The four numbers",
                "text": (
                    "Open = first trade of the period. High/Low = extremes. Close = last trade. "
                    "On a daily chart each candle is one session; on a 5‑minute chart each candle "
                    "is five minutes. Always know which timeframe you are reading."
                ),
            },
            {
                "heading": "Wicks tell the fight",
                "text": (
                    "A long upper wick after a push up = sellers rejected higher prices "
                    "(shooting star / pin). A long lower wick after a selloff = buyers "
                    "defended (hammer). Buying the tip of a wick is chasing — wait for the "
                    "next candle to close back through the level you care about."
                ),
            },
            {
                "heading": "Bodies and momentum",
                "text": (
                    "Large bodies show conviction. Tiny bodies (doji / spinning top) show "
                    "indecision. Two large opposite bodies (engulfing) can mark a turn when "
                    "they appear at a prior high/low or moving-average confluence — not in "
                    "the middle of nowhere."
                ),
            },
            {
                "heading": "Common beginner mistakes",
                "text": (
                    "1) Naming every pattern without a plan. 2) Ignoring volume. "
                    "3) Mixing timeframes (buying a 1‑minute hammer while the daily is "
                    "breaking down). 4) Entering before the candle closes — wicks can "
                    "still print."
                ),
            },
        ],
        "terms": [
            {"term": "Body", "def": "Open-to-close range; the ‘real’ battle of the period."},
            {"term": "Wick / shadow", "def": "High or low beyond the body — rejected prices."},
            {"term": "Engulfing", "def": "Current body fully covers prior body; possible reversal cue."},
            {"term": "Doji", "def": "Open ≈ close; indecision, useful only with structure."},
        ],
        "examples": [
            {
                "title": "Rejection at resistance",
                "detail": (
                    "Stock rallies into a prior high. The session prints a tall upper wick "
                    "and closes near the open. Next day opens lower. Lesson: the wick was "
                    "the warning — the close confirmed sellers won."
                ),
            },
            {
                "title": "Hammer at support",
                "detail": (
                    "Price tags a rising 50‑day MA, sells hard intraday, then closes near "
                    "the high (long lower wick). Volume expands. A long can be planned with "
                    "a stop under the wick low — not because ‘hammer = buy’, but because "
                    "structure + reaction + defined risk agree."
                ),
            },
        ],
        "chart": {
            "type": "candles_demo",
            "caption": "Left: bullish hammer at a support line. Right: shooting-star rejection at resistance. Bodies and wicks labeled.",
        },
        "takeaways": [
            "Read body + wick + where it sits on the chart.",
            "Wait for the close when the wick matters to your level.",
            "Pair patterns with support/resistance and a stop.",
        ],
        "practice": [
            "Open Chart studio on a watchlist name. Mark yesterday’s high/low.",
            "Find one rejection wick and one hammer this month — note what happened next.",
            "Write your invalidation level before imagining the entry.",
        ],
    },
    {
        "id": "trend",
        "title": "Trade with the trend",
        "level": "Beginner",
        "topics": ["moving averages", "higher highs", "pullbacks"],
        "body": (
            "Price above rising 50/200 MAs favors longs; below favors caution or shorts. "
            "Counter-trend trades need smaller size and faster invalidation."
        ),
        "overview": (
            "Trend is the path of least resistance. In an uptrend you generally see higher "
            "highs and higher lows; in a downtrend, lower highs and lower lows. Moving "
            "averages (SMA 20/50/200) are a simple map of that path — not magic lines."
        ),
        "sections": [
            {
                "heading": "Structure first",
                "text": (
                    "Before indicators: can you mark swing highs/lows? Uptrend = buyers "
                    "defend higher lows. When a higher low fails, the trend thesis weakens. "
                    "That failure is often a better short setup than shorting every green day."
                ),
            },
            {
                "heading": "Moving averages as context",
                "text": (
                    "Price above a rising 50‑day and 200‑day MA is a bullish regime for "
                    "swing traders. Below both is bearish. A flat 200‑day means range — "
                    "breakout/fade tactics beat trend-following. SMA20 is for short-term "
                    "pullbacks; SMA200 is the big-picture filter."
                ),
            },
            {
                "heading": "Pullbacks vs reversals",
                "text": (
                    "In a healthy uptrend, dips toward SMA20/50 with declining panic volume "
                    "are often buys for trend followers. A break of the last higher low with "
                    "expanding volume is different — that is structure change, not a dip."
                ),
            },
            {
                "heading": "Counter-trend rules",
                "text": (
                    "Fading a strong trend is advanced. If you do it: smaller size, tighter "
                    "stop, take profits faster, and require a clear level (prior high + "
                    "divergence or exhaustion wick). Never size a counter-trend trade like "
                    "a with-trend swing."
                ),
            },
        ],
        "terms": [
            {"term": "Higher high / higher low", "def": "Building blocks of an uptrend."},
            {"term": "SMA50 / SMA200", "def": "Medium and long-term average prices; regime filters."},
            {"term": "Pullback", "def": "Temporary move against the trend that does not break structure."},
            {"term": "Regime", "def": "Bull / bear / range environment that should change your playbook."},
        ],
        "examples": [
            {
                "title": "With-trend long",
                "detail": (
                    "Daily closes above rising SMA50 and SMA200. Price pulls back to SMA20 "
                    "on lighter volume, prints a hammer, and resumes. Entry near the MA with "
                    "stop under the pullback low keeps risk defined."
                ),
            },
            {
                "title": "Fighting the tape",
                "detail": (
                    "Stock is below a falling SMA200. RSI dips under 30. Buying ‘oversold’ "
                    "without a base often means catching a falling knife. Wait for a higher "
                    "low above a broken trendline — or stay flat."
                ),
            },
        ],
        "chart": {
            "type": "trend_ma",
            "caption": "Uptrend: price making higher lows above rising SMA50 (amber) and SMA200 (violet). Pullback marked at the 50.",
        },
        "takeaways": [
            "Trade smaller (or not at all) against the dominant regime.",
            "Use MAs as filters and pullback zones, not precise triggers alone.",
            "Structure break > indicator opinion.",
        ],
        "practice": [
            "In Chart studio, load SPY 1 year. Is price above or below SMA200?",
            "Mark the last three swing lows on a name you like — still rising?",
            "Write one with-trend setup and one reason you would stay out.",
        ],
    },
    {
        "id": "rsi",
        "title": "RSI is not a buy button",
        "level": "Intermediate",
        "topics": ["momentum", "overbought", "oversold", "divergence"],
        "body": (
            "RSI < 30 can stay oversold in a downtrend. Use RSI with structure (support) "
            "and a stop under the swing low — never as a standalone signal."
        ),
        "overview": (
            "RSI (Relative Strength Index, usually 14 periods) measures recent momentum on "
            "a 0–100 scale. Traditional labels: above 70 ‘overbought’, below 30 ‘oversold’. "
            "Those labels are descriptions of momentum, not automatic reverse signals."
        ),
        "sections": [
            {
                "heading": "What RSI actually measures",
                "text": (
                    "RSI compares average up-closes to average down-closes. High RSI means "
                    "recent gains dominated; low RSI means recent losses dominated. In strong "
                    "trends RSI can stay elevated or depressed for weeks."
                ),
            },
            {
                "heading": "Oversold ≠ buy",
                "text": (
                    "In a downtrend, RSI < 30 often means the selloff is active — not that "
                    "a bottom is in. Combine with: (1) a prior support or MA, (2) a "
                    "candle/structure stop, (3) optional bullish divergence (price lower "
                    "low, RSI higher low)."
                ),
            },
            {
                "heading": "Overbought ≠ short",
                "text": (
                    "Trending names can ride RSI > 70. Shorting solely because RSI is high "
                    "is how shorts get run over. Prefer failed breakouts, bearish engulfing "
                    "at resistance, or RSI bearish divergence with a break of a short-term "
                    "higher low."
                ),
            },
            {
                "heading": "Divergence (use carefully)",
                "text": (
                    "Bullish divergence: price makes a lower low, RSI makes a higher low — "
                    "selling pressure may be fading. Bearish: price higher high, RSI lower "
                    "high. Divergences fail often; treat them as alerts to tighten risk or "
                    "watch for confirmation, not as market orders."
                ),
            },
        ],
        "terms": [
            {"term": "RSI(14)", "def": "Default lookback; Infobroker scanner and chart studio use 14."},
            {"term": "Overbought / oversold", "def": "Momentum extremes — not guaranteed reversals."},
            {"term": "Divergence", "def": "Price and RSI disagree at swings; confirmation still required."},
            {"term": "Failure swing", "def": "RSI fails to make a new extreme then crosses back — classic Wilder idea."},
        ],
        "examples": [
            {
                "title": "False oversold buy",
                "detail": (
                    "Name gaps down on bad news. RSI hits 22. Buyers pile in. Next three "
                    "days make new lows. The ‘RSI buy’ ignored the broken trend and news "
                    "regime. A stop under day‑one low would have limited damage."
                ),
            },
            {
                "title": "RSI + level",
                "detail": (
                    "RSI dips to 28 as price tags a multi-month support that held twice "
                    "before. A bullish engulfing prints on rising volume. Plan: long with "
                    "stop under support. RSI was a filter; the level and candle were the trade."
                ),
            },
        ],
        "chart": {
            "type": "rsi_demo",
            "caption": "Price (top) can keep falling while RSI (bottom) stays under 30. Horizontal lines at 30 and 70 mark traditional zones.",
        },
        "takeaways": [
            "Never market-buy only because RSI < 30.",
            "Prefer RSI as confirmation with structure and a stop.",
            "In strong trends, respect momentum extremes instead of fading them blindly.",
        ],
        "practice": [
            "Open Chart studio RSI panel on AAPL. Note how long RSI can stay > 60 in a rally.",
            "Find one RSI < 30 event that continued lower — screenshot the lesson.",
            "On your next idea, write the level and stop before looking at RSI.",
        ],
    },
    {
        "id": "risk",
        "title": "Define risk first",
        "level": "Beginner",
        "topics": ["position size", "stop distance", "R-multiples"],
        "body": (
            "Decide stop distance before shares. Shares = (account risk $) / (entry − stop). "
            "If the size feels exciting, it is probably too large."
        ),
        "overview": (
            "Professionals start with ‘How much can I lose if I am wrong?’ Amateurs start "
            "with ‘How many shares can I afford?’ Infobroker’s order preview and teaching "
            "checklist push you toward the first habit."
        ),
        "sections": [
            {
                "heading": "The sizing formula",
                "text": (
                    "1) Pick account risk per trade (often 0.25%–1% of equity while learning). "
                    "2) Pick entry and invalidation (stop). "
                    "3) Risk per share = |entry − stop|. "
                    "4) Shares = dollar risk / risk per share. "
                    "If shares × price > your buying-power comfort, skip or wait for a tighter "
                    "setup — do not move the stop farther to ‘fit’ a larger size."
                ),
            },
            {
                "heading": "Stop placement logic",
                "text": (
                    "Stops belong beyond the level that proves your idea wrong: under a "
                    "swing low, under a breakout level, or under a key MA with a buffer for "
                    "noise. Arbitrary round-number stops (‘I’ll risk $1’) ignore structure "
                    "and get wicked out."
                ),
            },
            {
                "heading": "R-multiples",
                "text": (
                    "If you risk $100 (1R) and take $200 profit, that is +2R. Tracking R "
                    "keeps you honest when share counts differ. A +2R win and a −1R loss "
                    "net positive even with a 50% win rate — if you keep size consistent."
                ),
            },
            {
                "heading": "Live vs paper",
                "text": (
                    "On paper, practice the same size rules you will use live. Infobroker "
                    "can require a stop on live buys (risk guardrails). Brackets (entry + "
                    "stop + optional take-profit) force the plan into the ticket."
                ),
            },
        ],
        "terms": [
            {"term": "Account risk $", "def": "Max loss if stop hits; choose before entry."},
            {"term": "Invalidation", "def": "Price that proves the thesis wrong — your stop home."},
            {"term": "1R", "def": "One unit of planned risk; profits measured as multiples of R."},
            {"term": "Bracket", "def": "Entry plus protective stop and optional target order."},
        ],
        "examples": [
            {
                "title": "Worked example",
                "detail": (
                    "Equity $10,000. Risk 0.5% = $50. Long at $100, stop $97 → $3 risk/share. "
                    "Shares = 50 / 3 ≈ 16 shares (not 100 shares ‘because I can’). Max loss "
                    "≈ $48 if the stop fills cleanly."
                ),
            },
            {
                "title": "Wide stop trap",
                "detail": (
                    "Same $50 risk, but stop is $10 away → only 5 shares. That feels ‘too "
                    "small’, so the trader moves the stop to $2 away without a reason. Now "
                    "noise can stop them out while the real thesis is still intact — or "
                    "they size up and blow the risk budget. Fix the setup, not the math."
                ),
            },
        ],
        "chart": {
            "type": "risk_demo",
            "caption": "Entry, stop, and target as R-multiples. Position size shrinks when stop distance grows — same dollar risk.",
        },
        "takeaways": [
            "Size from risk and stop distance, never from FOMO share count.",
            "If the stop must be wide, size down or skip.",
            "Use brackets so the plan survives emotion after entry.",
        ],
        "practice": [
            "For a pretend long on your favorite ticker, write entry, stop, and shares at 0.5% risk.",
            "Preview an order in Infobroker with a stop — read the checklist.",
            "Journal one trade in R, not just dollars.",
        ],
    },
    {
        "id": "chase",
        "title": "Avoid chasing",
        "level": "Beginner",
        "topics": ["FOMO", "extension", "pullbacks", "VWAP"],
        "body": (
            "A vertical green candle into resistance is FOMO bait. Prefer pullbacks to "
            "prior breakout levels or VWAP with volume confirmation."
        ),
        "overview": (
            "Chasing means buying (or shorting) after the easy move already happened, "
            "usually into a level where other traders are fading. The entry feels urgent; "
            "the risk/reward is already poor."
        ),
        "sections": [
            {
                "heading": "What chase looks like",
                "text": (
                    "A tall green candle far above the open, into yesterday’s high or a "
                    "round number, with you clicking buy because the chat is green. Or "
                    "shorting a waterfall into support because ‘it can’t go lower’. Both "
                    "are late."
                ),
            },
            {
                "heading": "Better alternatives",
                "text": (
                    "1) Wait for a pullback to the breakout level (old resistance → new "
                    "support). 2) Wait for VWAP reclaim/reject on intraday. 3) Use limit "
                    "orders at your level instead of market orders into the spike. "
                    "4) If you miss it, miss it — another ticker will print tomorrow."
                ),
            },
            {
                "heading": "Volume tells honesty",
                "text": (
                    "Breakouts that hold usually show expanding volume on the thrust and "
                    "lighter volume on the pullback. Chase entries often happen on the "
                    "climax bar — the highest volume of the day — right before a pause."
                ),
            },
            {
                "heading": "Emotional tells",
                "text": (
                    "Heart rate up, skipping the preview checklist, increasing size "
                    "‘just this once’, and needing the trade to work immediately. When "
                    "you notice that, flat is a position."
                ),
            },
        ],
        "terms": [
            {"term": "FOMO", "def": "Fear of missing out — urgency without a plan."},
            {"term": "Extension", "def": "Price stretched far from a mean (VWAP/MA); mean-reversion risk rises."},
            {"term": "Breakout retest", "def": "Price returns to the breakout level; often a cleaner entry."},
            {"term": "VWAP", "def": "Volume-weighted average price; intraday fair-value anchor."},
        ],
        "examples": [
            {
                "title": "Chase vs retest",
                "detail": (
                    "Stock breaks $50 on huge volume and runs to $53 in minutes. Chase buy "
                    "at $53 risks a snapback to $50. Patient trader waits for a pullback "
                    "toward $50–$50.50 with a stop under $49.50 — same idea, better R."
                ),
            },
            {
                "title": "Climax short trap",
                "detail": (
                    "After a −8% day, shorts pile in at the lows. Next open gaps up. The "
                    "chase short ignored support and short-covering risk. Waiting for a "
                    "failed bounce under VWAP is slower and usually cleaner."
                ),
            },
        ],
        "chart": {
            "type": "chase_demo",
            "caption": "Vertical thrust into resistance (chase zone) vs later pullback to the breakout level (planned entry).",
        },
        "takeaways": [
            "If entry requires a market order into a vertical bar, pause.",
            "Prefer retests and defined stops over FOMO fills.",
            "Missing a move is cheaper than forced R.",
        ],
        "practice": [
            "Replay one hot day on a liquid name — mark where chase hurts.",
            "Set an alert at a level instead of watching every tick.",
            "Use Infobroker Preview before Submit even on paper.",
        ],
    },
    {
        "id": "support_resistance",
        "title": "Support & resistance",
        "level": "Beginner",
        "topics": ["levels", "breaks", "retests", "confluence"],
        "body": (
            "Horizontals and prior swing highs/lows are where orders cluster. Trade the "
            "reaction at the level — not a guess that the level is ‘magic’."
        ),
        "overview": (
            "Support is a price zone where buying previously emerged; resistance is where "
            "selling emerged. Zones beat exact pennies. The best levels have confluence: "
            "prior swing + MA + round number + high-volume node."
        ),
        "sections": [
            {
                "heading": "How to draw levels",
                "text": (
                    "Connect obvious swing highs/lows that price has reacted to more than "
                    "once. Prefer daily/4H for swing trades. Avoid clutter — three clean "
                    "levels beat twenty lines."
                ),
            },
            {
                "heading": "Break vs fakeout",
                "text": (
                    "A close beyond a level on rising volume is more meaningful than a wick. "
                    "Fakeouts wick through then close back inside. Many traders wait for "
                    "the retest: broken resistance becomes support (and vice versa)."
                ),
            },
            {
                "heading": "Using levels in Infobroker",
                "text": (
                    "When you select a symbol, note day high/low on the desk and Chart "
                    "studio range. Place stops beyond the zone that invalidates your idea, "
                    "not exactly on the round number everyone else shares."
                ),
            },
        ],
        "terms": [
            {"term": "Zone", "def": "A band of prices, not a single tick."},
            {"term": "Retest", "def": "Return to a broken level to confirm role reversal."},
            {"term": "Confluence", "def": "Multiple reasons the same price matters."},
            {"term": "Liquidity grab", "def": "Wick beyond highs/lows that triggers stops then reverses."},
        ],
        "examples": [
            {
                "title": "Role reversal",
                "detail": (
                    "Resistance at $180 caps three rallies. A daily close at $182 on volume "
                    "breaks it. Pullback to $180–$180.50 that holds becomes a long with stop "
                    "under the zone."
                ),
            },
        ],
        "chart": {
            "type": "levels_demo",
            "caption": "Horizontal resistance broken, then retested as support. Fake wick below support labeled.",
        },
        "takeaways": [
            "Draw fewer, better levels.",
            "Respect closes and volume; distrust lone wicks.",
            "Plan the retest instead of FOMO-breaking.",
        ],
        "practice": [
            "Mark two resistances and one support on your top watchlist name.",
            "Note whether yesterday’s high acted as magnet or rejection.",
        ],
    },
    {
        "id": "volume",
        "title": "Read volume",
        "level": "Intermediate",
        "topics": ["RVol", "confirmation", "climax", "dry-up"],
        "body": (
            "Volume is participation. Breakouts with expanding volume deserve more trust "
            "than quiet drifts. Relative volume (RVol) on the desk compares today to recent averages."
        ),
        "overview": (
            "Price is the path; volume is how many people cared. Rising price on rising "
            "volume supports a trend. Rising price on dying volume can mean a weak rally. "
            "Infobroker’s RVol column flags unusually active sessions."
        ),
        "sections": [
            {
                "heading": "Confirmation",
                "text": (
                    "A breakout candle with volume well above the 5–10 day average is a "
                    "participation signal. The same breakout on below-average volume is "
                    "suspect — often fails or needs a second try."
                ),
            },
            {
                "heading": "Climax and dry-up",
                "text": (
                    "Climax: huge volume at an extreme after a long move — can mark "
                    "exhaustion. Dry-up: volume shrinks into a tight range before the next "
                    "expansion — coiled spring. Neither alone is a signal; both change odds."
                ),
            },
            {
                "heading": "Using RVol on the desk",
                "text": (
                    "RVol ~1.0 is normal. RVol 2×+ means the name is ‘in play’. That can "
                    "be opportunity or trap — check the lesson on chasing. Sort volume "
                    "leaders, then apply level + risk rules before acting."
                ),
            },
        ],
        "terms": [
            {"term": "RVol", "def": "Today’s volume ÷ recent average volume."},
            {"term": "Climax", "def": "Spike in volume at a price extreme; possible exhaustion."},
            {"term": "Confirmation", "def": "Volume agreeing with the price break direction."},
        ],
        "examples": [
            {
                "title": "Quiet fake breakout",
                "detail": (
                    "Price nudges above resistance on RVol 0.6. No follow-through. Next day "
                    "slips back. The volume lesson: without participation, treat breaks as "
                    "probes."
                ),
            },
        ],
        "chart": {
            "type": "volume_demo",
            "caption": "Price breakout aligned with a volume surge (green bars), then a quieter pullback — healthier than a silent break.",
        },
        "takeaways": [
            "Ask ‘who is participating?’ on every breakout.",
            "High RVol demands tighter process, not looser risk.",
            "Pullbacks on lighter volume are often healthier than panic volume dips.",
        ],
        "practice": [
            "Sort Infobroker volume leaders. Open Chart studio volume panel on #1.",
            "Compare a high-RVol day to a quiet day on the same ticker.",
        ],
    },
    {
        "id": "stops",
        "title": "Stops that make sense",
        "level": "Intermediate",
        "topics": ["invalidation", "brackets", "paper stops"],
        "body": (
            "A stop is where your idea is wrong — not where the pain feels tolerable. "
            "On paper, use Process paper stops; on live brokers, resting stop orders live with the broker."
        ),
        "overview": (
            "Stops convert a thesis into a number. Without them, every dip is a debate. "
            "Infobroker supports protective stops and take-profit on market brackets, plus "
            "stop / stop-limit entry types on the order ticket."
        ),
        "sections": [
            {
                "heading": "Technical vs mental stops",
                "text": (
                    "Technical: under swing low / beyond level. Mental: ‘I’ll get out if it "
                    "feels bad’ — usually too late. Prefer resting orders. On Infobroker "
                    "paper, open stops stay until you click Process paper stops or the "
                    "assistant runs process_stops."
                ),
            },
            {
                "heading": "Stop types",
                "text": (
                    "Stop market: becomes a market order when the stop price trades — "
                    "fills are not guaranteed at the stop. Stop-limit: becomes a limit "
                    "when triggered — may not fill in a gap. Protective stop on a bracket "
                    "is for exit after you are already in."
                ),
            },
            {
                "heading": "Gaps and slippage",
                "text": (
                    "News gaps can fill worse than your stop. That is why account risk % "
                    "matters — assume occasional slippage. Reduce size ahead of binary "
                    "events if you cannot afford the gap."
                ),
            },
        ],
        "terms": [
            {"term": "Protective stop", "def": "Exit order that caps loss after entry."},
            {"term": "Stop-limit", "def": "Triggered stop that then rests as a limit; fill not guaranteed."},
            {"term": "Bracket", "def": "Entry + stop ± take-profit as a package."},
        ],
        "examples": [
            {
                "title": "Paper bracket",
                "detail": (
                    "Buy 1 share market with stop loss and take-profit filled in the ticket. "
                    "Infobroker places the entry then resting exit orders. Process stops "
                    "when quotes cross your stop in paper mode."
                ),
            },
        ],
        "chart": {
            "type": "stops_demo",
            "caption": "Long entry with stop under swing low and take-profit at prior high. Distance entry→stop is your 1R.",
        },
        "takeaways": [
            "Place stops at invalidation, then size to that distance.",
            "Know stop vs stop-limit behavior before using them live.",
            "On paper, actually process stops — practice the habit.",
        ],
        "practice": [
            "Submit a paper bracket with a real swing-low stop.",
            "Change order type to stop and preview — read any blockers.",
        ],
    },
    {
        "id": "macd",
        "title": "MACD without the mystique",
        "level": "Intermediate",
        "topics": ["momentum", "signal line", "histogram"],
        "body": (
            "MACD is a moving-average story: line vs signal and the histogram gap. Crosses "
            "lag price — use them with trend and levels, same as RSI."
        ),
        "overview": (
            "MACD (Moving Average Convergence Divergence) subtracts a longer EMA from a "
            "shorter EMA, then smooths that difference into a signal line. The histogram "
            "is the gap between MACD and signal — a visual of momentum accelerating or fading."
        ),
        "sections": [
            {
                "heading": "Bullish / bearish cross",
                "text": (
                    "MACD crossing above signal is traditionally bullish; below is bearish. "
                    "In ranges you get whipsaws. In trends, crosses against the regime are "
                    "often noise. Infobroker’s scanner flags MACD with an ‘active day’ tip "
                    "— still confirm with level + volume."
                ),
            },
            {
                "heading": "Histogram",
                "text": (
                    "Rising histogram (less negative or more positive) means momentum "
                    "improving for bulls. Shrinking histogram into a high can warn that "
                    "upside momentum is cooling — again, not a standalone short signal."
                ),
            },
            {
                "heading": "With Chart studio",
                "text": (
                    "Open the MACD panel for your ticker/period. Align a cross with a "
                    "support retest for a long study; ignore crosses mid-air with no level."
                ),
            },
        ],
        "terms": [
            {"term": "MACD line", "def": "EMA12 − EMA26 (common defaults)."},
            {"term": "Signal", "def": "EMA of the MACD line (often 9)."},
            {"term": "Histogram", "def": "MACD − signal; momentum acceleration visual."},
        ],
        "examples": [
            {
                "title": "Cross at support",
                "detail": (
                    "Price holds SMA50. MACD histogram flips up and line crosses signal. "
                    "That stack is more interesting than a cross while price is mid-range."
                ),
            },
        ],
        "chart": {
            "type": "macd_demo",
            "caption": "MACD line (amber) crossing signal with histogram bars flipping from red to cyan — study only with price context above.",
        },
        "takeaways": [
            "MACD lags — great for confirmation, weak for sniper entries alone.",
            "Prefer crosses that agree with trend and a level.",
            "Histogram shrinkage is a warning light, not a market order.",
        ],
        "practice": [
            "Run the MACD strategy backtest on the Strategies tab vs buy&hold.",
            "Find one whipsaw cross in a sideways month.",
        ],
    },
    {
        "id": "playbook",
        "title": "Build a simple playbook",
        "level": "All levels",
        "topics": ["process", "checklist", "journal"],
        "body": (
            "A playbook is a short list of setups you are allowed to take — with entry, "
            "stop, target, and ‘no-trade’ rules. Everything else is entertainment."
        ),
        "overview": (
            "Infobroker exists to teach process: watchlist → scan → level → risk preview → "
            "order. Your playbook should be written down so FOMO cannot invent a new "
            "strategy every hour."
        ),
        "sections": [
            {
                "heading": "Minimum playbook fields",
                "text": (
                    "Name the setup (e.g. ‘trend pullback to SMA20’). Markets (US equities). "
                    "Timeframe. Entry trigger. Stop rule. Target or R-multiple. Max risk %. "
                    "When to stand aside (FOMC, first 5 minutes, RVol < 0.5, etc.)."
                ),
            },
            {
                "heading": "Using the desk as a loop",
                "text": (
                    "1) Refresh markets / scan. 2) Open Chart studio for candidates. "
                    "3) Open the matching Learn lesson if unsure. 4) Fill the ticket with "
                    "stop. 5) Preview. 6) Submit only if checklist is honest. 7) Journal "
                    "the R result."
                ),
            },
            {
                "heading": "Grapevine as coach, not boss",
                "text": (
                    "The assistant can hunt ideas and call tools, but you own the click. "
                    "Ask it to explain a ticker against your playbook rules — not to "
                    "override them."
                ),
            },
        ],
        "terms": [
            {"term": "Setup", "def": "A named, repeatable pattern with rules."},
            {"term": "No-trade list", "def": "Conditions where you flatten process and stay out."},
            {"term": "Edge", "def": "A statistical or process advantage — not a hot tip."},
        ],
        "examples": [
            {
                "title": "One-setup week",
                "detail": (
                    "Only trade ‘pullback to SMA20 in names above SMA200’ for five sessions. "
                    "Ignore everything else. Review win rate in R. Expand only after the "
                    "process feels boring — boring is good."
                ),
            },
        ],
        "chart": {
            "type": "playbook_demo",
            "caption": "A loop: Scan → Chart → Lesson → Risk → Ticket. Skipping boxes is how playbooks die.",
        },
        "takeaways": [
            "Write rules before the open.",
            "One setup executed well beats five half-remembered patterns.",
            "Use Infobroker’s checklist as the last gate.",
        ],
        "practice": [
            "Write a 6-line playbook in a note.",
            "Take one paper trade that matches it exactly — or take none.",
            "Ask Grapevine: ‘Does this idea match a pullback-to-SMA20 playbook?’",
        ],
    },
]


def list_lessons() -> list[dict[str, Any]]:
    """Sidebar summaries (teaser = body) with page counts."""
    from infobroker.education.multipage import build_pages

    out = []
    for l in LESSONS:
        pages = build_pages(l)
        out.append(
            {
                "id": l["id"],
                "title": l["title"],
                "body": l["body"],
                "level": l.get("level", ""),
                "topics": l.get("topics") or [],
                "page_count": len(pages),
            }
        )
    return out


def get_lesson(lesson_id: str) -> dict[str, Any] | None:
    from infobroker.education.multipage import attach_pages
    from infobroker.education.tutor import TUTOR_ID, get_tutor

    lid = (lesson_id or "").strip().lower()
    if lid == TUTOR_ID:
        return get_tutor()
    raw = next((dict(l) for l in LESSONS if l["id"] == lid), None)
    if not raw:
        return None
    return attach_pages(raw)


def list_lesson_ids() -> list[str]:
    from infobroker.education.tutor import TUTOR_ID

    return [l["id"] for l in LESSONS] + [TUTOR_ID]

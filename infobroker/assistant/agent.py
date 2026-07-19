"""Grapevine trading assistant — lean tool loop + light desk coach."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from typing import Any, Optional

from infobroker.assistant.desk_context import COACH_TARGETS, DESK_GUIDE, build_desk_snapshot
from infobroker.assistant.ollama_client import chat, ollama_healthy
from infobroker.assistant.tools import execute_tool, list_actions, tool_schemas_for_prompt

SYSTEM = """You are Infobroker Grapevine — a fast desk coach (Clippy for this trading desk).
You receive a LIVE DESK SNAPSHOT every turn (US open/closed, gainers, losers, cash, watchlist, UI focus).
Answer desk questions from the snapshot first. Call tools only when you need fresher or deeper data.

CRITICAL — prices when the market is closed:
- US cash closed does NOT mean you cannot see prices.
- The desk keeps last session / delayed quotes in the universe cache.
- For any ticker price → call get_prices (one or many) or get_quote.
- For the full watchlist with prices → call get_watchlist_quotes.
- Never tell the user you "can't see prices" just because us_open is false.
- Say "last price (as of …)" when the session is closed.

Personality: warm, clear, practical. Risk first, then edge, then size. Never promise profits.

Rules:
1. Prefer paper/sim. Never claim you placed a live broker order.
2. For new trade ideas, call find_opportunities OR scan_signals (not both unless asked).
3. preview_order before place_paper_order. Respect risk blockers.
4. Missing keys → key_links / get_desk_state.
5. Price questions → get_prices / get_watchlist_quotes (not "market closed").
6. Be concise (short paragraphs / bullets).
7. Tool call = one JSON line: {"tool":"NAME","args":{...}}
8. Finish with: {"final":"answer","coach":[...optional max 2 steps...],"followups":["short next question",...]}
   followups are optional (0–3). The desk also adds pregenerated chips; keep yours short and clickable.

Coach steps (optional, teaching only — max 2):
{"target":"markets-movers","tab":"markets","sub":"movers","shape":"rect","color":"green","arrow":"left","title":"Movers","message":"...","duration_ms":5000}
Targets: """ + COACH_TARGETS + """
Colors: red=risk/losers, green=opportunity/open, amber=ticket tip, cyan=nav.
Use coach sparingly — only when user asks how/where/show/teach. Skip coach for simple Q&A.
No markdown fences around JSON.
"""


def _extract_json_objects(text: str) -> list[dict[str, Any]]:
    objs: list[dict[str, Any]] = []
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    if stripped.startswith("{") and stripped.endswith("}"):
        try:
            objs.append(json.loads(stripped))
            return objs
        except json.JSONDecodeError:
            pass
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}" and depth:
            depth -= 1
            if depth == 0 and start >= 0:
                chunk = text[start : i + 1]
                try:
                    obj = json.loads(chunk)
                    if isinstance(obj, dict) and (
                        "tool" in obj or "final" in obj or "coach" in obj
                    ):
                        objs.append(obj)
                except json.JSONDecodeError:
                    pass
                start = -1
    return objs


def _normalize_coach(raw: Any) -> list[dict[str, Any]]:
    if not raw:
        return []
    steps = raw if isinstance(raw, list) else [raw]
    out: list[dict[str, Any]] = []
    for s in steps[:2]:
        if not isinstance(s, dict):
            continue
        target = str(s.get("target") or "").strip()
        if not target:
            continue
        shape = str(s.get("shape") or "rect").lower()
        if shape not in {"rect", "circle"}:
            shape = "rect"
        color = str(s.get("color") or "cyan").lower()
        if color not in {"red", "amber", "green", "cyan"}:
            color = "cyan"
        arrow = str(s.get("arrow") or "none").lower()
        if arrow not in {"left", "right", "top", "bottom", "none"}:
            arrow = "none"
        try:
            duration = int(s.get("duration_ms") or 5000)
        except (TypeError, ValueError):
            duration = 5000
        duration = max(3000, min(duration, 10000))
        out.append(
            {
                "target": target,
                "tab": s.get("tab"),
                "sub": s.get("sub"),
                "shape": shape,
                "color": color,
                "arrow": arrow,
                "title": str(s.get("title") or "Grapevine")[:60],
                "message": str(s.get("message") or "")[:240],
                "duration_ms": duration,
            }
        )
    return out


def _suggest_followups(user_message: str, snapshot: dict[str, Any]) -> list[str]:
    """Pregenerated clickable next questions for the chat UI (max 4)."""
    low = (user_message or "").lower().strip()
    gainers = snapshot.get("gainers") or []
    losers = snapshot.get("losers") or []
    g0 = (gainers[0] or {}).get("symbol") if gainers else None
    g1 = (gainers[1] or {}).get("symbol") if len(gainers) > 1 else None
    l0 = (losers[0] or {}).get("symbol") if losers else None
    wl = snapshot.get("watchlist") or []
    w0 = wl[0] if wl else None
    ui = snapshot.get("ui") or {}
    selected = ui.get("selected_symbol")
    tips: list[str] = []

    def add(q: str) -> None:
        q = (q or "").strip()
        if q and q not in tips and q.lower() != low:
            tips.append(q)

    # Price of a ticker
    price_m = re.search(
        r"(?:price of|quote (?:for|on)|how much is)\s+\$?([A-Za-z][A-Za-z0-9.\-]{0,7})\b",
        low,
    ) or re.search(r"\b([A-Za-z][A-Za-z0-9.\-]{0,7})(?:'s)?\s+(?:price|quote|last)\b", low)
    if price_m:
        sym = price_m.group(1).upper().replace(".", "-")
        if sym not in {"WHAT", "HOW", "THE", "PRICE", "QUOTE"}:
            add(f"Add {sym} to my watchlist")
            add(f"Preview a careful paper buy of {sym}")
            add("Show my watchlist prices")
            add("How do I size risk on the order ticket?")

    if any(k in low for k in ("gainer", "top green", "what's up", "whats up")):
        if g0:
            add(f"What's the price of {g0}?")
        if g1:
            add(f"What's the price of {g1}?")
        add("Show top losers")
        add("How do I trade a gainer carefully?")

    if any(k in low for k in ("loser", "top red", "what's down", "whats down")):
        if l0:
            add(f"What's the price of {l0}?")
        add("Show top gainers")
        add("Show my watchlist prices")

    if any(k in low for k in ("market open", "us open", "are we open")):
        add("Show top gainers")
        add("Show my watchlist prices")
        if w0:
            add(f"What's the price of {w0}?")
        add("How do I trade?")

    if any(k in low for k in ("watchlist", "tracking", "my tickers")):
        if w0:
            add(f"What's the price of {w0}?")
        add("Show top gainers")
        add("How do I add a ticker from Markets?")
        add("Find careful paper-trade ideas")

    if any(k in low for k in ("cash", "buying power", "equity", "balance")):
        add("What positions do I hold?")
        add("Show my watchlist prices")
        add("How do I place a paper order?")

    if any(k in low for k in ("position", "holding", "hold")):
        add("How much cash do I have?")
        add("Show my watchlist prices")
        add("How do I close a position carefully?")

    if any(k in low for k in ("how to trade", "how do i trade", "make money", "order ticket")):
        add("Show top gainers")
        add("Show me the order ticket")
        add("What is portfolio?")
        add("Explain the desk")

    if any(k in low for k in ("hunt", "opportunit", "find trade", "find careful")):
        if g0:
            add(f"What's the price of {g0}?")
        add("Preview a paper buy with a stop")
        add("Show top losers")
        add("How do I size risk first?")

    if any(k in low for k in ("learning", "lesson", "tutor", "strateg", "backtest", "chart")):
        add("Explain the desk")
        add("How do I trade?")
        add("Show top gainers")

    if selected:
        add(f"What's the price of {selected}?")

    # Always fill with useful defaults
    for q in (
        "Is the market open?",
        "Show top gainers",
        "Show my watchlist prices",
        "How do I trade?",
        "Explain the desk",
        "Find careful paper-trade ideas",
    ):
        add(q)
        if len(tips) >= 4:
            break
    return tips[:4]


def _attach_followups(
    payload: dict[str, Any],
    user_message: str,
    snapshot: dict[str, Any],
    extra: Optional[list[str]] = None,
) -> dict[str, Any]:
    tips = list(extra or [])
    for q in _suggest_followups(user_message, snapshot):
        if q not in tips:
            tips.append(q)
    payload["followups"] = tips[:4]
    return payload


def _wants_coach(user_message: str) -> bool:
    low = (user_message or "").lower()
    return any(
        k in low
        for k in (
            "how do i",
            "how to",
            "teach",
            "show me",
            "where is",
            "where do",
            "point",
            "circle",
            "guide me",
            "walk me",
            "clippy",
        )
    )


def _fast_desk_answer(user_message: str, snapshot: dict[str, Any]) -> Optional[str]:
    """Answer common desk questions without calling Ollama (keeps UI responsive)."""
    low = (user_message or "").lower().strip()
    if not low or len(low) > 160:
        return None

    if any(k in low for k in ("is the market open", "us open", "market open", "are we open")):
        if snapshot.get("us_open"):
            return "US cash session is **open** (until 16:00 ET)."
        hint = snapshot.get("us_hint") or "opens Mon 09:30 ET"
        return f"US cash session is **closed**. {hint}."

    if any(k in low for k in ("gainer", "top green", "what's up", "whats up today")):
        rows = snapshot.get("gainers") or []
        if not rows:
            return "No gainers in the universe cache yet — open Markets → Live/Movers and wait for quotes to fill."
        lines = ["Top gainers on the desk right now:"]
        for r in rows[:5]:
            lines.append(f"- {r.get('symbol')}: {r.get('change_pct_day')}% @ {r.get('price')}")
        return "\n".join(lines)

    if any(k in low for k in ("loser", "top red", "what's down", "whats down")):
        rows = snapshot.get("losers") or []
        if not rows:
            return "No losers cached yet — check Markets → Movers."
        lines = ["Top losers on the desk right now:"]
        for r in rows[:5]:
            lines.append(f"- {r.get('symbol')}: {r.get('change_pct_day')}% @ {r.get('price')}")
        return "\n".join(lines)

    if any(k in low for k in ("how much cash", "buying power", "my equity", "account balance")):
        return (
            f"Broker: {snapshot.get('broker')} ({'LIVE' if snapshot.get('live_trading') else 'paper/sim'})\n"
            f"- Cash: {snapshot.get('cash')}\n"
            f"- Equity: {snapshot.get('equity')}\n"
            f"- Buying power: {snapshot.get('buying_power')}"
        )

    if any(
        k in low
        for k in (
            "watchlist",
            "what am i tracking",
            "watchlist prices",
            "prices on my watchlist",
            "my tickers",
        )
    ):
        from infobroker.assistant.tools import tool_get_watchlist_quotes

        wlq = tool_get_watchlist_quotes(refresh_missing=False)
        items = wlq.get("items") or []
        if not items:
            return "Watchlist is empty — add tickers from Markets or the left rail."
        closed = "" if snapshot.get("us_open") else " (last session / cached — US cash closed)"
        lines = [f"Watchlist prices{closed}:"]
        for r in items[:40]:
            px = r.get("price")
            ch = r.get("change_pct_day")
            if px is None:
                lines.append(f"- {r.get('symbol')}: no quote cached yet")
            else:
                ch_s = f" ({ch:+.2f}%)" if isinstance(ch, (int, float)) else ""
                lines.append(f"- {r.get('symbol')}: {px}{ch_s}")
        miss = wlq.get("missing_quotes") or []
        if miss:
            lines.append(f"Missing cache: {', '.join(miss[:12])}. Ask me to refresh those.")
        return "\n".join(lines)

    # "price of AAPL" / "AAPL price" / "how much is MSFT" / "what's AAPL at"
    price_m = re.search(
        r"(?:price of|quote (?:for|on)|how much is)\s+\$?([A-Za-z][A-Za-z0-9.\-]{0,7})\b",
        low,
    )
    if not price_m:
        price_m = re.search(
            r"\b([A-Za-z][A-Za-z0-9.\-]{0,7})(?:'s)?\s+(?:price|quote|last)\b",
            low,
        )
    if not price_m:
        price_m = re.search(
            r"(?:what(?:'s| is))\s+\$?([A-Za-z][A-Za-z0-9.\-]{0,7})\s+(?:at|trading|worth|doing)\b",
            low,
        )
    if price_m:
        from infobroker.assistant.tools import tool_get_prices

        sym = price_m.group(1).upper().replace(".", "-")
        stop = {
            "WHAT", "HOW", "THE", "FOR", "AND", "PRICE", "QUOTE", "LAST", "OPEN",
            "MY", "A", "AN", "IS", "ARE", "THIS", "THAT", "YOUR", "DESK",
        }
        if sym not in stop:
            payload = tool_get_prices(symbol=sym, refresh_missing=True)
            row = (payload.get("items") or [{}])[0]
            px = row.get("price")
            if px is None:
                return f"No price for {sym} in the universe cache yet — try Fill quotes on Markets → Live."
            ch = row.get("change_pct_day")
            ch_s = f" ({ch:+.2f}% day)" if isinstance(ch, (int, float)) else ""
            as_of = row.get("as_of") or "last session"
            sess = "US open" if payload.get("us_open") else "US closed — showing last cached price"
            return f"{sym}: **{px}**{ch_s}\n{sess} · as_of {as_of} · source {row.get('source')}"

    if any(k in low for k in ("position", "what do i hold", "what am i holding")):
        pos = snapshot.get("positions") or []
        if not pos:
            return "No open positions."
        lines = ["Open positions:"]
        for p in pos[:10]:
            lines.append(
                f"- {p.get('symbol')}: qty {p.get('qty')} avg {p.get('avg_entry')} "
                f"uP/L {p.get('unrealized_pl')}"
            )
        return "\n".join(lines)

    if any(k in low for k in ("missing key", "api key", "which keys")):
        miss = snapshot.get("missing_keys") or []
        if not miss:
            return "No required keys look missing. Optional market-data keys can still improve coverage."
        return "Missing / incomplete keys: " + ", ".join(miss) + ". Open API Keys (top bar) or ask for key_links."

    if any(k in low for k in ("what tab", "where am i", "what am i looking")):
        ui = snapshot.get("ui") or {}
        return (
            f"You're on tab `{ui.get('active_tab') or 'markets'}`"
            + (f" / `{ui.get('markets_sub')}`" if ui.get("markets_sub") else "")
            + (f", selected `{ui.get('selected_symbol')}`" if ui.get("selected_symbol") else "")
            + "."
        )

    # Static desk guide for UI "what is / where" without LLM
    guide_keys = {
        "how to trade": "how_to_trade",
        "how do i trade": "how_to_trade",
        "make money": "how_to_trade",
        "order ticket": "order",
        "preview risk": "order",
        "what is trading": "trading",
        "trading tab": "trading",
        "what is portfolio": "portfolio",
        "portfolio tab": "portfolio",
        "what is markets": "markets",
        "markets tab": "markets",
        "live board": "markets",
        "movers": "markets",
        "scanner": "markets",
        "explain the desk": "overview",
        "what can you do": "overview",
        "help": "overview",
        "where do i": "overview",
        "where is": "overview",
    }
    for phrase, key in guide_keys.items():
        if phrase in low:
            return DESK_GUIDE[key]

    if any(k in low for k in ("auto-track", "auto track", "track gainers")):
        return (
            "Auto-track lives under Portfolio → Auto-track gainers. "
            "It can add names up ≥ X% on the day to your watchlist. "
            "Ask me to call get_auto_track for the current settings."
        )
    if any(k in low for k in ("learning", "lesson", "tutor")):
        return (
            "Learning tab: Tutor path, trade journal, and skill lessons. "
            "Ask list_lessons for the catalog, or open Learning from the desk tabs."
        )
    if any(k in low for k in ("strateg", "backtest")):
        return (
            "Strategies tab lists free yfinance strategies (SMA, RSI, MACD, buy&hold, breakout). "
            "Quick SMA also sits under the order rail Backtest panel."
        )
    if any(k in low for k in ("chart studio", "charts tab", "chart desk")):
        return (
            "Chart studio tab loads an inspectable OHLC pack — hover OHLC, drag to zoom. "
            "Live chart also appears under Markets → Symbol / Live side panel."
        )
    if "volume" in low and ("leader" in low or "most" in low):
        rows = snapshot.get("volume_leaders") or []
        if rows:
            lines = ["Volume leaders (cached):"]
            for r in rows[:4]:
                lines.append(f"- {r.get('symbol')}: {r.get('price')}")
            return "\n".join(lines)
    return None


def run_assistant(
    user_message: str,
    *,
    image_b64: Optional[str] = None,
    max_steps: int = 3,
    history: Optional[list[dict[str, str]]] = None,
    ui_context: Optional[dict[str, Any]] = None,
) -> dict[str, Any]:
    health = ollama_healthy()
    snapshot = build_desk_snapshot(ui_context)

    # Fast path: common desk Q&A without Ollama (and without vision)
    if not image_b64:
        fast = _fast_desk_answer(user_message, snapshot)
        if fast:
            coach = []
            if _wants_coach(user_message):
                coach = _normalize_coach(
                    [
                        {
                            "target": "desk-tabs",
                            "shape": "rect",
                            "color": "cyan",
                            "arrow": "top",
                            "title": "Desk tabs",
                            "message": "Switch Markets / Trading / Portfolio here.",
                            "duration_ms": 4500,
                        },
                        {
                            "target": "order-ticket",
                            "shape": "rect",
                            "color": "amber",
                            "arrow": "right",
                            "title": "Order ticket",
                            "message": "Size → Preview → paper Submit.",
                            "duration_ms": 5000,
                        },
                    ]
                )
            return _attach_followups(
                {
                    "ok": True,
                    "reply": fast,
                    "coach": coach,
                    "desk_snapshot": {
                        "us_open": snapshot.get("us_open"),
                        "us_hint": snapshot.get("us_hint"),
                        "gainers": snapshot.get("gainers"),
                        "losers": snapshot.get("losers"),
                    },
                    "actions": [],
                    "action_log": list_actions(20),
                    "ollama": health,
                    "fast_path": True,
                },
                user_message,
                snapshot,
            )

    if not health.get("ok"):
        return _attach_followups(
            {
                "ok": False,
                "reply": (
                    "Ollama is not reachable. Start Ollama, ensure "
                    f"`{health.get('model')}` is pulled, then try again.\n"
                    f"Detail: {health.get('error')}"
                ),
                "actions": list_actions(20),
                "coach": [],
                "desk_snapshot": {
                    "us_open": snapshot.get("us_open"),
                    "us_hint": snapshot.get("us_hint"),
                    "gainers": snapshot.get("gainers"),
                    "losers": snapshot.get("losers"),
                },
                "ollama": health,
            },
            user_message,
            snapshot,
        )
    if health.get("model_present") is False:
        return _attach_followups(
            {
                "ok": False,
                "reply": (
                    f"Model `{health.get('model')}` not found in Ollama. "
                    "Run: `ollama pull arriella-grapevine` (or set INFOBROKER_OLLAMA_MODEL)."
                ),
                "actions": list_actions(20),
                "coach": [],
                "desk_snapshot": {
                    "us_open": snapshot.get("us_open"),
                    "us_hint": snapshot.get("us_hint"),
                    "gainers": snapshot.get("gainers"),
                    "losers": snapshot.get("losers"),
                },
                "ollama": health,
            },
            user_message,
            snapshot,
        )

    # Strip huge vision payloads
    if image_b64 and len(image_b64) > 350_000:
        image_b64 = None

    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM}]
    messages.append(
        {
            "role": "system",
            "content": "Tools:\n" + tool_schemas_for_prompt(),
        }
    )
    # Compact snapshot — already has account/watchlist
    snap_compact = {
        k: snapshot.get(k)
        for k in (
            "us_open",
            "us_hint",
            "venues",
            "broker",
            "live_trading",
            "cash",
            "equity",
            "buying_power",
            "positions",
            "watchlist",
            "gainers",
            "losers",
            "volume_leaders",
            "missing_keys",
            "ui",
        )
    }
    messages.append(
        {
            "role": "system",
            "content": "LIVE DESK SNAPSHOT:\n" + json.dumps(snap_compact, default=str)[:3500],
        }
    )
    for h in (history or [])[-4:]:
        if h.get("role") in {"user", "assistant"} and h.get("content"):
            messages.append({"role": h["role"], "content": h["content"][:800]})

    messages.append({"role": "user", "content": user_message[:2000]})

    images = [image_b64] if image_b64 else None
    step_actions: list = []
    final_reply = ""
    coach_steps: list[dict[str, Any]] = []
    model_followups: list[str] = []
    raw = ""
    max_steps = max(1, min(int(max_steps), 3))

    for step in range(max_steps):
        try:
            raw = chat(
                messages,
                images_b64=images if step == 0 else None,
                timeout=55,
            )
        except Exception as exc:  # noqa: BLE001
            final_reply = f"Grapevine timed out or failed talking to Ollama: {exc}"
            break
        messages.append({"role": "assistant", "content": raw})
        objs = _extract_json_objects(raw)

        if not objs:
            final_reply = raw.strip()
            break

        done = False
        for obj in objs:
            if "coach" in obj and not coach_steps:
                coach_steps = _normalize_coach(obj.get("coach"))
            if "final" in obj:
                final_reply = str(obj.get("final") or "").strip()
                if obj.get("coach"):
                    coach_steps = _normalize_coach(obj.get("coach"))
                raw_fu = obj.get("followups") or obj.get("follow_ups") or []
                if isinstance(raw_fu, list):
                    model_followups = [
                        str(x).strip()[:120] for x in raw_fu if str(x).strip()
                    ][:3]
                done = True
                break
            tool = obj.get("tool")
            if not tool:
                continue
            args = obj.get("args") if isinstance(obj.get("args"), dict) else {}
            event = execute_tool(str(tool), args, raw=obj)
            step_actions.append(event)
            messages.append(
                {
                    "role": "user",
                    "content": (
                        f"TOOL_RESULT {tool} ok={event.ok}\n"
                        + json.dumps(
                            {
                                "summary": event.summary,
                                "error": event.error,
                                "result": event.result,
                            },
                            default=str,
                        )[:3000]
                    ),
                }
            )
        if done:
            break
    else:
        if not final_reply:
            final_reply = "Hit the step limit — ask a narrower question or tap Find trades again."

    if not final_reply:
        ideas_evt = next(
            (a for a in reversed(step_actions) if a.tool == "find_opportunities" and a.ok),
            None,
        )
        if ideas_evt and isinstance(ideas_evt.result, dict):
            ideas = ideas_evt.result.get("ideas") or []
            lines = ["Top candidates:"]
            for idea in ideas[:4]:
                lines.append(
                    f"- {idea.get('symbol')} ({idea.get('side')}): "
                    f"{', '.join(idea.get('signals') or [])}"
                )
                sym = idea.get("symbol")
                if sym:
                    model_followups.append(f"What's the price of {sym}?")
            final_reply = "\n".join(lines)
        else:
            final_reply = raw.strip() if raw else "Done."

    if coach_steps and not _wants_coach(user_message):
        # Don't spam overlays on ordinary Q&A
        coach_steps = []

    return _attach_followups(
        {
            "ok": True,
            "reply": final_reply,
            "coach": coach_steps,
            "desk_snapshot": {
                "us_open": snapshot.get("us_open"),
                "us_hint": snapshot.get("us_hint"),
                "gainers": snapshot.get("gainers"),
                "losers": snapshot.get("losers"),
            },
            "actions": [asdict(a) for a in step_actions],
            "action_log": list_actions(20),
            "ollama": health,
            "fast_path": False,
        },
        user_message,
        snapshot,
        extra=model_followups,
    )


def hunt_once(ui_context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """One-shot trade hunt — lean prompt, no auto coach spam."""
    return run_assistant(
        "Hunt careful paper ideas from the LIVE DESK SNAPSHOT gainers/losers first. "
        "Call find_opportunities once (max_ideas=3). Summarize top 3 with risk notes. "
        "Do not place an order. No coach steps unless useful.",
        max_steps=2,
        ui_context=ui_context,
    )

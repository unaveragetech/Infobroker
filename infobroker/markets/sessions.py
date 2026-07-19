"""World market session clocks (local rules — no API required)."""

from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

# Regular cash sessions (local exchange time). Holidays ignored for desk UX.
_MARKETS: list[dict[str, Any]] = [
    {
        "id": "nyse",
        "name": "New York",
        "short": "NY",
        "tz": "America/New_York",
        "open": time(9, 30),
        "close": time(16, 0),
        "weekdays": {0, 1, 2, 3, 4},
    },
    {
        "id": "london",
        "name": "London",
        "short": "LDN",
        "tz": "Europe/London",
        "open": time(8, 0),
        "close": time(16, 30),
        "weekdays": {0, 1, 2, 3, 4},
    },
    {
        "id": "frankfurt",
        "name": "Frankfurt",
        "short": "FRA",
        "tz": "Europe/Berlin",
        "open": time(9, 0),
        "close": time(17, 30),
        "weekdays": {0, 1, 2, 3, 4},
    },
    {
        "id": "tokyo",
        "name": "Tokyo",
        "short": "TYO",
        "tz": "Asia/Tokyo",
        "open": time(9, 0),
        "close": time(15, 0),
        "weekdays": {0, 1, 2, 3, 4},
    },
    {
        "id": "hongkong",
        "name": "Hong Kong",
        "short": "HK",
        "tz": "Asia/Hong_Kong",
        "open": time(9, 30),
        "close": time(16, 0),
        "weekdays": {0, 1, 2, 3, 4},
        # lunch break 12:00–13:00
        "breaks": [(time(12, 0), time(13, 0))],
    },
    {
        "id": "sydney",
        "name": "Sydney",
        "short": "SYD",
        "tz": "Australia/Sydney",
        "open": time(10, 0),
        "close": time(16, 0),
        "weekdays": {0, 1, 2, 3, 4},
    },
]


def _in_session(local: datetime, mkt: dict[str, Any]) -> bool:
    if local.weekday() not in mkt["weekdays"]:
        return False
    t = local.time().replace(tzinfo=None)
    if not (mkt["open"] <= t < mkt["close"]):
        return False
    for start, end in mkt.get("breaks") or []:
        if start <= t < end:
            return False
    return True


def _tz_abbr(local: datetime) -> str:
    name = local.tzname() or ""
    # Prefer short forms users recognize
    mapping = {
        "Eastern Standard Time": "ET",
        "Eastern Daylight Time": "ET",
        "EST": "ET",
        "EDT": "ET",
        "GMT": "GMT",
        "BST": "BST",
        "Central European Standard Time": "CET",
        "Central European Summer Time": "CET",
        "Japan Standard Time": "JST",
        "Hong Kong Standard Time": "HKT",
        "Australian Eastern Standard Time": "AEST",
        "Australian Eastern Daylight Time": "AEDT",
    }
    return mapping.get(name, name or "local")


def _next_open_local(local: datetime, mkt: dict[str, Any]) -> datetime | None:
    """Next regular-session open in the market's local timezone."""
    if _in_session(local, mkt):
        return None
    # Still today, before the open bell
    if local.weekday() in mkt["weekdays"] and local.time().replace(tzinfo=None) < mkt["open"]:
        return datetime.combine(local.date(), mkt["open"], tzinfo=local.tzinfo)
    for i in range(1, 8):
        d = local.date() + timedelta(days=i)
        if d.weekday() in mkt["weekdays"]:
            return datetime.combine(d, mkt["open"], tzinfo=local.tzinfo)
    return None


def _next_open_hint(local: datetime, mkt: dict[str, Any]) -> str | None:
    """Short human hint when closed, e.g. 'opens Mon 09:30 ET'."""
    nxt = _next_open_local(local, mkt)
    if not nxt:
        return None
    abbr = _tz_abbr(nxt)
    if nxt.date() == local.date():
        return f"opens {nxt.strftime('%H:%M')} {abbr}"
    return f"opens {nxt.strftime('%a')} {nxt.strftime('%H:%M')} {abbr}"


def market_clocks(now: datetime | None = None) -> dict[str, Any]:
    """Snapshot of major venues: local time, open/closed, UTC reference."""
    utc_now = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    markets: list[dict[str, Any]] = []
    any_open = False
    for mkt in _MARKETS:
        tz = ZoneInfo(mkt["tz"])
        local = utc_now.astimezone(tz)
        is_open = _in_session(local, mkt)
        any_open = any_open or is_open
        nxt = None if is_open else _next_open_local(local, mkt)
        markets.append(
            {
                "id": mkt["id"],
                "name": mkt["name"],
                "short": mkt["short"],
                "timezone": mkt["tz"],
                "tz_abbr": _tz_abbr(local),
                "local_time": local.strftime("%H:%M:%S"),
                "local_date": local.strftime("%Y-%m-%d"),
                "offset": local.strftime("%z"),
                "is_open": is_open,
                "session": "open" if is_open else "closed",
                "hint": None if is_open else _next_open_hint(local, mkt),
                "next_open": nxt.isoformat() if nxt else None,
                "next_open_label": None if is_open else _next_open_hint(local, mkt),
                "hours": f"{mkt['open'].strftime('%H:%M')}–{mkt['close'].strftime('%H:%M')}",
            }
        )

    us = next((m for m in markets if m["id"] == "nyse"), None)
    return {
        "as_of": utc_now.isoformat(),
        "utc": utc_now.strftime("%H:%M:%S"),
        "local": datetime.now().astimezone().strftime("%H:%M:%S"),
        "local_tz": datetime.now().astimezone().tzname() or "local",
        "any_open": any_open,
        "us_open": bool(us and us["is_open"]),
        "us_hint": (us or {}).get("hint"),
        "us_next_open": (us or {}).get("next_open"),
        "us_next_open_label": (us or {}).get("next_open_label"),
        "us_hours": (us or {}).get("hours"),
        "markets": markets,
    }

"""US equity listings from NASDAQ Trader (official symbol directories)."""

from __future__ import annotations

import csv
import io
import re
from typing import Any
from urllib.request import Request, urlopen

# Yahoo chart-friendly tickers (drop preferred "=" / warrant "$" quirks)
_YAHOO_SYM_RE = re.compile(r"^[A-Z][A-Z0-9\-]{0,11}$")

NASDAQ_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/nasdaqlisted.txt"
OTHER_LISTED = "https://www.nasdaqtrader.com/dynamic/SymDir/otherlisted.txt"

# otherlisted Exchange codes → human labels (CQS)
_EXCHANGE_MAP = {
    "A": "NYSE American",
    "N": "NYSE",
    "P": "NYSE Arca",
    "Z": "BATS",
    "V": "IEX",
    "Q": "NASDAQ",
}

_UA = "Mozilla/5.0 (compatible; Infobroker/0.7; +local)"


def yahoo_symbol(raw: str) -> str:
    """Normalize exchange ticker to Yahoo chart symbol."""
    sym = (raw or "").strip().upper().replace(" ", "")
    if not sym:
        return ""
    # Class shares: BRK.B → BRK-B (Yahoo)
    sym = sym.replace(".", "-")
    if sym == "BRK-B":
        return "BRK-B"
    return sym


def _classify(name: str, etf_flag: bool) -> str:
    n = (name or "").lower()
    if etf_flag or " etf" in n or n.endswith(" etf"):
        return "etf"
    if "warrant" in n:
        return "warrant"
    if " right" in n or n.endswith(" rights"):
        return "right"
    if " unit" in n:
        return "unit"
    if "preferred" in n or " preference" in n:
        return "preferred"
    if "adr" in n or "american depositary" in n:
        return "adr"
    if "common stock" in n or "ordinary shares" in n or "class a" in n or "class b" in n:
        return "stock"
    if "note" in n or "bond" in n or "debenture" in n:
        return "fixed_income"
    return "other"


def _fetch_text(url: str, timeout: int = 60) -> str:
    req = Request(url, headers={"User-Agent": _UA})
    with urlopen(req, timeout=timeout) as resp:  # noqa: S310 — official NASDAQ HTTPS
        return resp.read().decode("latin-1", errors="replace")


def _parse_pipe(text: str) -> list[dict[str, str]]:
    # Drop File Creation Time footer lines
    lines = [
        ln
        for ln in text.splitlines()
        if ln.strip() and not ln.startswith("File Creation Time")
    ]
    if not lines:
        return []
    reader = csv.DictReader(io.StringIO("\n".join(lines)), delimiter="|")
    return [dict(row) for row in reader if row]


def fetch_us_listings() -> list[dict[str, Any]]:
    """
    Download NASDAQ + NYSE/Arca/etc directories and return normalized rows.

    Each row: symbol, name, exchange, etf, asset_class, source
    """
    out: dict[str, dict[str, Any]] = {}

    nasdaq_raw = _fetch_text(NASDAQ_LISTED)
    for row in _parse_pipe(nasdaq_raw):
        if (row.get("Test Issue") or "N").strip().upper() == "Y":
            continue
        sym = yahoo_symbol(row.get("Symbol") or "")
        if not sym or not _YAHOO_SYM_RE.match(sym):
            continue
        name = (row.get("Security Name") or "").strip()
        etf = (row.get("ETF") or "N").strip().upper() == "Y"
        out[sym] = {
            "symbol": sym,
            "name": name,
            "exchange": "NASDAQ",
            "etf": etf,
            "asset_class": _classify(name, etf),
            "source": "nasdaqlisted",
        }

    other_raw = _fetch_text(OTHER_LISTED)
    for row in _parse_pipe(other_raw):
        if (row.get("Test Issue") or "N").strip().upper() == "Y":
            continue
        # Prefer NASDAQ Symbol column when present (already Yahoo-friendly)
        raw_sym = row.get("NASDAQ Symbol") or row.get("ACT Symbol") or ""
        sym = yahoo_symbol(raw_sym)
        if not sym or not _YAHOO_SYM_RE.match(sym):
            continue
        name = (row.get("Security Name") or "").strip()
        etf = (row.get("ETF") or "N").strip().upper() == "Y"
        exch = _EXCHANGE_MAP.get((row.get("Exchange") or "").strip().upper(), "Other")
        # Don't overwrite a richer NASDAQ listing unless missing
        if sym in out and out[sym].get("source") == "nasdaqlisted":
            continue
        out[sym] = {
            "symbol": sym,
            "name": name,
            "exchange": exch,
            "etf": etf,
            "asset_class": _classify(name, etf),
            "source": "otherlisted",
        }

    return sorted(out.values(), key=lambda r: r["symbol"])

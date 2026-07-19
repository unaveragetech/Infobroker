"""
Infobroker MCP server — lets Cursor (or any MCP client) read/act on the desk.

Run:
  python -m infobroker.mcp_server

Cursor mcp.json example:
  {
    "mcpServers": {
      "infobroker": {
        "command": "python",
        "args": ["-m", "infobroker.mcp_server"],
        "cwd": "C:/Users/b0052/Desktop/info_broker-auto"
      }
    }
  }
"""

from __future__ import annotations

import json
from typing import Any

from infobroker.assistant.tools import TOOLS, execute_tool, tool_schemas_for_prompt


def _try_fastmcp() -> bool:
    try:
        from mcp.server.fastmcp import FastMCP  # type: ignore
    except Exception:
        return False

    mcp = FastMCP("infobroker")

    @mcp.tool()
    def get_desk_state() -> str:
        """Account, watchlist, missing API keys."""
        return json.dumps(execute_tool("get_desk_state").result, default=str)

    @mcp.tool()
    def find_opportunities(max_ideas: int = 5) -> str:
        """Rank trade candidates from scanner + volume leaders."""
        return json.dumps(
            execute_tool("find_opportunities", {"max_ideas": max_ideas}).result,
            default=str,
        )

    @mcp.tool()
    def scan_signals() -> str:
        """RSI/MA/MACD scan over watchlist."""
        return json.dumps(execute_tool("scan_signals").result, default=str)

    @mcp.tool()
    def get_highlights() -> str:
        """Day/week movers and notables."""
        return json.dumps(execute_tool("get_highlights").result, default=str)

    @mcp.tool()
    def preview_order(
        symbol: str, side: str = "buy", qty: float = 1.0, stop_price: float | None = None
    ) -> str:
        """Risk-check an order without placing it."""
        args: dict[str, Any] = {"symbol": symbol, "side": side, "qty": qty}
        if stop_price is not None:
            args["stop_price"] = stop_price
        return json.dumps(execute_tool("preview_order", args).result, default=str)

    @mcp.tool()
    def place_paper_order(
        symbol: str,
        side: str = "buy",
        qty: float = 1.0,
        stop_price: float | None = None,
        take_profit: float | None = None,
    ) -> str:
        """Place paper/sim order only (refuses live)."""
        args: dict[str, Any] = {"symbol": symbol, "side": side, "qty": qty}
        if stop_price is not None:
            args["stop_price"] = stop_price
        if take_profit is not None:
            args["take_profit"] = take_profit
        return json.dumps(execute_tool("place_paper_order", args).result, default=str)

    @mcp.tool()
    def key_links() -> str:
        """Signup links for Alpaca, Public, Tradier, Finnhub, Alpha Vantage."""
        return json.dumps(execute_tool("key_links").result, default=str)

    @mcp.tool()
    def add_watch(symbol: str) -> str:
        """Add ticker to watchlist."""
        return json.dumps(execute_tool("add_watch", {"symbol": symbol}).result, default=str)

    @mcp.tool()
    def get_tracked() -> str:
        """Quotes for watchlist tickers."""
        return json.dumps(execute_tool("get_tracked").result, default=str)

    @mcp.tool()
    def backtest(symbol: str, start: str, end: str, strategy: str = "sma_crossover") -> str:
        """Free yfinance strategy backtest."""
        return json.dumps(
            execute_tool(
                "backtest",
                {"symbol": symbol, "start": start, "end": end, "strategy": strategy},
            ).result,
            default=str,
        )

    @mcp.tool()
    def list_strategies() -> str:
        """Base strategies catalog."""
        return json.dumps(execute_tool("list_strategies").result, default=str)

    @mcp.tool()
    def get_chart_pack(symbol: str, start: str, end: str) -> str:
        """Price/volume/RSI/MACD chart pack for a date range."""
        return json.dumps(
            execute_tool("get_chart_pack", {"symbol": symbol, "start": start, "end": end}).result,
            default=str,
        )

    @mcp.tool()
    def place_order(
        symbol: str,
        side: str = "buy",
        qty: float = 1.0,
        order_type: str = "market",
        limit_price: float | None = None,
        stop_price: float | None = None,
        take_profit: float | None = None,
    ) -> str:
        """Paper order: market/limit/stop + optional exits."""
        args: dict[str, Any] = {
            "symbol": symbol,
            "side": side,
            "qty": qty,
            "order_type": order_type,
        }
        if limit_price is not None:
            args["limit_price"] = limit_price
        if stop_price is not None:
            args["stop_price"] = stop_price
        if take_profit is not None:
            args["take_profit"] = take_profit
        return json.dumps(execute_tool("place_order", args).result, default=str)

    @mcp.tool()
    def process_stops() -> str:
        """Process paper stop orders."""
        return json.dumps(execute_tool("process_stops").result, default=str)

    @mcp.tool()
    def mcp_control(action: str = "status") -> str:
        """Note: nested MCP control of this same process — prefer desk Services tab."""
        return json.dumps(execute_tool("mcp_control", {"action": action}).result, default=str)

    @mcp.tool()
    def ollama_control(action: str = "status") -> str:
        """Grapevine/Ollama status|warm|unload|list_models."""
        return json.dumps(execute_tool("ollama_control", {"action": action}).result, default=str)

    @mcp.tool()
    def list_tool_docs() -> str:
        """Describe all Infobroker tools."""
        return tool_schemas_for_prompt()

    mcp.run()
    return True


def _stdio_fallback() -> None:
    """Minimal JSON-RPC-ish stdin loop when mcp package is missing."""
    import sys

    print(
        json.dumps(
            {
                "ready": True,
                "server": "infobroker-fallback",
                "tools": list(TOOLS),
                "hint": "pip install mcp  for full MCP; or POST /api/assistant/* on the web app",
            }
        ),
        flush=True,
    )
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError:
            print(json.dumps({"ok": False, "error": "invalid_json"}), flush=True)
            continue
        name = req.get("tool") or req.get("method")
        args = req.get("args") or req.get("params") or {}
        if name in {"list_tools", "tools/list"}:
            print(
                json.dumps(
                    {
                        "ok": True,
                        "tools": [
                            {"name": s.name, "description": s.description} for s in TOOLS.values()
                        ],
                    }
                ),
                flush=True,
            )
            continue
        event = execute_tool(str(name), args if isinstance(args, dict) else {})
        print(
            json.dumps(
                {
                    "ok": event.ok,
                    "summary": event.summary,
                    "result": event.result,
                    "error": event.error,
                },
                default=str,
            ),
            flush=True,
        )


def main() -> None:
    if not _try_fastmcp():
        _stdio_fallback()


if __name__ == "__main__":
    main()

# Infobroker MCP + Grapevine Assistant

## In-app assistant (Grapevine)

The desk right sidebar runs **Arriella Grapevine** via local Ollama. Grapevine was **designed for Infobroker** — using it is highly advised. After you start the desk, click **Tour** first; see [USAGE.md](USAGE.md) for screenshots and model-capability requirements.

```bash
ollama list   # expect arriella-grapevine:latest (or your INFOBROKER_OLLAMA_MODEL)
python -m infobroker.web.app
# http://127.0.0.1:8000/  → click Tour
```

Alternate models need chat completion, image summary, image→text, thinking, and reductive output.

### Behavior

- **Fast path** — common desk Q&A (open/closed, gainers, cash, prices, watchlist) without calling the LLM
- **Tool loop** — deeper actions (hunt, preview, paper orders, portfolio, …)
- **Prices when closed** — `get_prices` / `get_watchlist_quotes` read the universe cache (last session quotes)
- **Follow-up chips** — pregenerated clickable next questions under each reply
- **Coach overlays** — optional highlights (manual Next; kept light)
- **Send view** — captures the active panel only (not the full page)

Env (optional):

```bash
OLLAMA_HOST=http://127.0.0.1:11434
INFOBROKER_OLLAMA_MODEL=arriella-grapevine:latest
```

## MCP server (Cursor / external agents)

```bash
pip install mcp
python -m infobroker.mcp_server
```

Safe Cursor fragment (also in [mcp.example.json](mcp.example.json)):

```json
{
  "mcpServers": {
    "infobroker": {
      "command": "python",
      "args": ["-m", "infobroker.mcp_server"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

Point `command` at your venv’s `python` if needed. **Do not commit** a `.cursor/mcp.json` that embeds absolute machine paths or secrets.

Desk **Services & keys** can start/stop/restart a desk-managed MCP process and warm/unload Grapevine.

`place_paper_order` / `place_order` refuse live mode from the assistant path.

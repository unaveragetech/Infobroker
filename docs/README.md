# Infobroker documentation

Technical reference for the Infobroker desk. The same content is browsable under **Settings → Docs**.

| Doc | Topic |
|-----|--------|
| [USAGE.md](USAGE.md) | **Start here after launch** — Tour, UI screenshots, Grapevine / model requirements, desk insights |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Full stack + mermaid diagrams |
| [DATA.md](DATA.md) | Market data, universe cache, closed-session prices |
| [RATE_LIMITS.md](RATE_LIMITS.md) | Provider quotas and how Infobroker avoids them |
| [BROKERS.md](BROKERS.md) | Free execution brokers + market-data providers |
| [MCP.md](MCP.md) | Grapevine assistant + MCP server for Cursor |
| [../exchanges.md](../exchanges.md) | Exchange reference notes |
| [../README.md](../README.md) | Setup scripts and feature overview |
| [../DONATE.md](../DONATE.md) | PayPal support link |
| [../LICENSE](../LICENSE) | SDUC License v1.1 |
| [mcp.example.json](mcp.example.json) | Safe Cursor MCP fragment (no machine paths) |

## Setup

```powershell
# Windows
powershell -ExecutionPolicy Bypass -File .\setup.ps1
.\.venv\Scripts\Activate.ps1
python -m infobroker.web.app
```

```bash
# macOS / Linux
bash setup.sh
source .venv/bin/activate
python -m infobroker.web.app
```

## OpenAPI

With the desk running: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

JSON catalog: `GET /api/docs` · page: `GET /api/docs/{id}`

## Secrets

- Copy [`.env.example`](../.env.example) → `.env` locally  
- **Never commit `.env`, `users.json`, or `data/*` ledgers/caches**  
- API keys: desk **API Keys** modal (localhost-only settings API)  

## Support

[Donate via PayPal](https://www.paypal.com/donate/?hosted_button_id=2RXWCC28FJ79N)

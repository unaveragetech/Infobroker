# Infobroker documentation

Technical reference for the Infobroker desk. The same content is browsable in the UI under **Settings → Docs**.

| Doc | Topic |
|-----|--------|
| [DATA.md](DATA.md) | How market data, universe cache, and closed-session prices work |
| [BROKERS.md](BROKERS.md) | Free execution brokers + market-data providers |
| [MCP.md](MCP.md) | Grapevine assistant + MCP server for Cursor |
| [ARCHITECTURE.md](ARCHITECTURE.md) | Package layout and request path |
| [../exchanges.md](../exchanges.md) | Exchange reference notes |
| [../README.md](../README.md) | Quick start and feature overview |
| [mcp.example.json](mcp.example.json) | Safe Cursor MCP fragment (no machine paths) |

## OpenAPI

With the desk running: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

JSON catalog: `GET /api/docs` · page: `GET /api/docs/{id}`

## Secrets

- Copy [`.env.example`](../.env.example) → `.env` locally
- **Never commit `.env`, `users.json`, or `data/*` ledgers/caches**
- API keys are edited in the desk **API Keys** modal (localhost-only settings API)

# API Contracts

## WebUI HTTP Contracts

All WebUI endpoints are local runtime endpoints served by FastAPI. They are not the public GitHub Pages site.

- `GET /`: serves `webui/static/index.html`.
- `GET /favicon.ico`: serves dashboard favicon.
- `GET /events`: Server-Sent Events stream with `state` events and keepalive `ping`.
- `GET /state?user_id=<id>`: composed runtime/dashboard snapshot, with optional user isolation.
- `GET /avatar`: local public media portrait fallback or official logo.
- `GET /health`: returns `{"status": "ok"}`.
- `GET /api/stats`: persistent stats plus uptime.
- `GET /api/memory`: process/system memory health.
- `GET /api/mcp/status`: secret-safe MCP status.
- `GET /api/plugins/status`: secret-safe plugin registry status.
- `GET /api/memory/layers`: layered memory diagnostics.
- `GET /thoughts`: current and recent thoughts.
- `GET /api/soul`, `/api/soul/history`, `/api/soul/experience`, `/api/soul/conflicts`, `/api/soul/somatic`: soul/affect diagnostics.
- `GET /api/aliveness`, `/api/aliveness/new`, and aliveness subroutes: interoceptive/idle/bids/memory/inconsistency diagnostics.
- `POST /api/chat`: body includes `text`, optional `user_id`, optional `message_id`; returns `status`, `message_id`, and `user_id`.
- `GET /api/settings`: returns editable settings file contents.
- `POST /api/settings`: body includes `file` and `content`; only `settings.json`, `self.json`, `directives.json`, and `instructions.md` are allowed.

Status: decided from `webui/app.py`.

## Runtime Event Contracts

Incoming chat messages are emitted as `message_received` with fields such as:

- `text`
- `chat_id`
- `user_id`
- `source`
- `message_id`
- optional `webui_user_id`

Output adapters listen for events such as `send_text`, `send_voice_file`, `send_image`, `send_video`, `proactive_message`, and `proactive_message_ready`.

Status: decided from terminal, Telegram, and WebUI adapters.

## CLI Contracts

Public CLI commands:

- `alive-ai init <directory>`
- `alive-ai setup [--yes]`
- `alive-ai demo [--port 8080]`
- `alive-ai update [--yes]`
- `alive-ai start [--skip-install]`
- `alive-ai stop`
- `alive-ai chat [--skip-install]`
- `alive-ai chat --plain`
- `alive-ai doctor [--fix]`
- `alive-ai uninstall`

Status: decided from README and `cli/index.js`.

## Config Contract

Startup reads, in order:

1. `.env`
2. `config/secrets.env`
3. `config/settings.json`

`config/settings.json` values are exported into process environment for simple scalar settings. Dict/nested values are not exported as scalars.

Status: decided from `main.py`.

## Provider Contracts

- OpenRouter uses `https://openrouter.ai/api/v1`, `OPENROUTER_API_KEY`, and task-specific `OPENROUTER_MODEL_*` settings.
- ZAI uses `ZAI_API_KEY` and `ZAI_MODEL_*`.
- Ollama uses `OLLAMA_URL` and `OLLAMA_MODEL_*`.
- OpenAI-compatible providers use provider-specific base URL and model settings.
- Generic OpenAI-compatible local/server providers must not receive provider-specific reasoning controls unless their adapter explicitly supports them.

Status: decided from `brain/llm/factory.py` and tests.

## MCP Contracts

- MCP is off unless `MCP_ENABLED` and `MCP_MODE` enable it.
- `MCP_SERVERS` declares servers/tools.
- Status endpoints must redact env values and sensitive args.
- Tool proposals store redacted arguments, decision, status, and results.
- Execution must be blocked until the proposal is explicitly approved.

Status: decided from `core/mcp/` and tests.

## Plugin API

- The internal plugin registry and `/api/plugins/status` diagnostics surface are live runtime internals.
- The public plugin API is roadmap only for now.
- There is no stable external plugin contract yet.
- Do not document, promise, or implement third-party plugin compatibility as stable without updating the source of truth and locking contracts first.

Status: decided by operator on 2026-06-10.

## External Service Contracts

- Telegram: token and owner id are configured locally; owner-only commands require owner match.
- OpenMind: optional cloud/local semantic memory bridge configured with `OPENMIND_ENABLED`, `OPENMIND_MODE`, `OPENMIND_BASE_URL`, and optional key.
- Redis: optional local vector cache controlled by `REDIS_VECTOR_MEMORY_ENABLED` and Docker settings.
- Fal.ai/voice providers: optional output services, skipped when keys are missing.

Status: decided from README/config examples.

## Contract Gaps

- API response schemas for every WebUI endpoint are not formally typed in a shared schema file.
- CLI runtime metadata under `.alive-ai/` is not yet documented as a stable schema.

Status: unknown.

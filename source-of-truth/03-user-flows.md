# User Flows

## Scaffold Flow

1. User runs `npx alive-ai@latest init my-ai`.
2. CLI creates an isolated project directory and copies runtime assets from the package.
3. User enters the project and runs `npx . setup`.
4. Setup creates local config, data, media folders, and runtime identity files.

Canonical created paths include `config/settings.json`, `config/self.json`, `config/directives.json`, `config/instructions.md`, `data/`, `mypics/`, and `myvids/`.

Status: decided from README and `cli/index.js`.

## Setup Flow

Setup asks for local configuration: LLM provider, Telegram, voice, image generation, memory, MCP, Redis vector cache, and agent identity fields. It accepts `skip` for optional keys and `local` for Ollama.

`config/settings.json` is the runtime source of truth created by setup. `.env` and `config/secrets.env` are read for compatibility and secrets before settings are exported into the process.

Status: decided from README, examples, and `main.py`.

## Terminal Chat Flow

- `npx . chat` starts the Python runtime in terminal mode with a split-pane TUI by default.
- `npx . chat --plain` starts raw terminal chat.
- Terminal chat emits the same `message_received` event contract used by Telegram.
- `/exit`, `/quit`, or `/stop` ends terminal chat.
- Terminal commands include `/help`, `/dashboard`, `/status`, `/stats`, `/self`, `/discover`, `/iam`, `/ilike`, `/ihate`, `/rethink`, `/settings`, `/reset`, and `/impulse`.

Status: decided from README and `input/terminal/listener.py`.

## Telegram Flow

- `npx . start` starts the configured input channel, usually Telegram.
- Telegram requires a bot token for Telegram mode; otherwise terminal chat is the fallback path.
- Public Telegram commands include `/start` and `/help`.
- Owner-only commands require `TELEGRAM_OWNER_ID` and include status, impulse, settings, dashboard, self-authorship, MCP, memory wipe/reset, and advanced thinking controls.

Status: decided from README and `input/telegram/commands.py`.

## Runtime Stop Flow

- Foreground runtime should stop on `Ctrl+C`.
- `npx . stop` stops the running project process using project-local runtime metadata under `.alive-ai/`.
- Docker-managed Redis is stopped by `npx . stop` when Redis vector memory is enabled, preserving the Redis volume.
- `docker compose down -v` is the intentional Redis vector memory wipe path.

Status: decided from README and prior release notes; verify exact current `cli/index.js` behavior before changing stop internals.

## WebUI Flow

- The runtime starts the WebUI when `WEBUI_ENABLED` is not false.
- Default local dashboard URL is `http://127.0.0.1:8080`.
- Dashboard streams state over SSE and can poll `/state`.
- WebUI chat posts to `/api/chat`, appends a user journal row, and emits `message_received` into the same runtime event path.
- Settings can be read and saved through `/api/settings`; JSON saves are validated and written atomically.

Status: decided from README and `webui/app.py`.

## Memory Flow

- Built-in local memory and internal state persist under project-local `data/`.
- Per-user WebUI chat rows are journaled under `data/users/<user>/webui_chat.jsonl`.
- Episodic, semantic, emotional, autobiographical, dream, and shadow memory layers can feed prompt context.
- OpenMind is optional and adds semantic recall across tools/machines.
- Redis Stack is optional vector cache, not required when OpenMind is enabled.

Status: decided from README, `webui/persistence.py`, and memory modules.

## MCP Flow

- MCP is disabled by default.
- MCP server catalog/status can be exposed without secrets.
- Normal chat cannot execute tools directly.
- Tool calls must be proposed, permission-checked, owner-approved when required, and then executed through the guarded path.
- Audit and proposal state are stored under `data/mcp/`.

Status: decided from `core/mcp/` and tests.

## Benchmark Flow

- `python3 benchmarks/run_benchmarks.py --dry-run-script` previews the benchmark conversation.
- Full benchmark runs compare live WebUI runtime and raw model baselines.
- Benchmark outputs are local-only artifacts; publish only sanitized reports/screenshots.

Status: decided from README.

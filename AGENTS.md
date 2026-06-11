# Agent instructions - Alive-AI

Alive-AI is a local-first emotional companion runtime with an npm CLI, Python runtime, terminal/Telegram input, optional OpenMind/Redis/MCP integrations, and a local FastAPI WebUI. Main code lives in `cli/`, `main.py`, `core/`, `brain/`, `heart/`, `input/`, `output/`, `skills/`, `webui/`, `pages/`, and `tests/`.

## Read the source of truth first

`source-of-truth/*` is the canonical truth for product behavior, flows, data model, API contracts, naming, deployment, and unresolved decisions. It wins over stale README text, old release notes, comments, and assumptions. Start from `source-of-truth/00-overview.md` and `source-of-truth/source-map.yaml`; use `source-of-truth/10-glossary.md` for names.

When a change affects covered behavior, update the relevant source-of-truth file in the same change. Do not create a second authority for the same fact.

## Verification gates

- `npm run smoke` for the lightweight CLI/static/Python compile smoke.
- `python3 -m unittest` or focused tests under `tests/` for runtime/provider/WebUI/MCP changes.
- `npm pack --dry-run` for package contents or release changes.
- Installed-project smoke when changing CLI lifecycle, scaffold, update, package files, process stop/start, or runtime path resolution.
- Pages/static verification when editing `pages/src/` or generated `docs/`.
- Release when the touched surface works under the relevant checks; do not add ceremony for untouched surfaces.

## Hard rules

- Keep `Alive-AI` as the product name and `alive-ai` as the package/CLI name.
- Treat the public positioning as emotional companion runtime first; research/general-agent framing is supporting context.
- Keep the configured agent identity separate from the framework name.
- Keep the current dark technical/cyber companion visual direction for now, but match UI colors to the actual logo palette.
- Treat owner/operator and conversation user as the only canonical roles for now; the owner can also be a conversation user.
- Keep local-first ownership: runtime data, config, media, cache, and secrets stay local unless explicitly integrated.
- Retain local `data/`, media, memories, Redis vectors, and OpenMind-linked memory indefinitely by default; destructive cleanup requires explicit owner/operator action.
- Treat backup/restore as manual project-folder backup for now; do not invent first-class export/restore commands without source-of-truth changes.
- Keep normal local WebUI binding on `127.0.0.1`; Docker/container WebUI runs should bind `0.0.0.0` inside the container, and current `main.py` still needs that implementation.
- Publish only after the changed package/runtime/site surface actually works under relevant verification.
- Treat the public plugin API as roadmap-only; internal plugin registry/status surfaces are not a stable external plugin contract.
- Additional partner-style safety boundaries are deferred; do not invent new product-level safety policy beyond existing source/code boundaries.
- Do not invent extra roles, billing, hosted backend behavior, plugin API stability, or deployment rules not in `source-of-truth/`.
- Do not let normal chat execute MCP tools directly; MCP remains default-deny, proposal-based, approval-gated, and redacted.
- Do not weaken provider response-shaping or reasoning-artifact rejection without targeted tests.
- If source truth is missing or ambiguous, use `onboard-source`.
- If decided truth must change, use `remake-source`.

## Useful pointers

- `README.md` - public product and setup docs, but roadmap items are not all live behavior.
- `package.json` - npm package authority and `npm run smoke`.
- `pyproject.toml` - Python package metadata.
- `cli/index.js` - scaffold/setup/update/start/stop/chat/doctor/uninstall lifecycle.
- `main.py` - runtime bootstrap, config loading, WebUI startup, signal handling.
- `core/message_handler.py` and `core/thinking.py` - response assembly and sanitization path.
- `brain/llm/` - provider adapters and fallback routing.
- `webui/app.py` - local FastAPI dashboard endpoints.
- `core/mcp/` - MCP catalog, permission, proposal, approval, execution, and audit flow.
- `tests/` - regression tests for provider shaping, MCP, memory, WebUI, and runtime state.

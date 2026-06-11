# Deployment

## Environments

- Source checkout: `/Users/vdpm/Documents/codex-projects/alive-ai` in the current local workspace.
- npm package: `alive-ai`.
- Public static site: GitHub Pages at `https://vindepemarte.github.io/alive-ai/`.
- Local runtime project: a user-scaffolded directory created by `npx alive-ai@latest init my-ai`.
- Local dashboard: `http://127.0.0.1:8080` by default.
- Docker: optional local/container runtime plus Redis Stack.

Status: decided from repo metadata and README.

## Package Distribution

`package.json` is the npm package authority. Current bootstrap metadata:

- package: `alive-ai`
- version: `0.2.5`
- bin: `alive-ai` -> `cli/index.js`
- Node requirement: `>=18`
- license: MIT
- homepage: GitHub Pages
- repository: `vindepemarte/alive-ai`

Status: decided at bootstrap; version expected to drift.

## Python Runtime Distribution

`pyproject.toml` declares:

- project: `alive-ai-runtime`
- version: `0.2.5`
- Python: `>=3.11`
- packages: `alive_ai`, `brain`, `core`, `heart`, `input`, `output`, `skills`, `webui`

Status: decided at bootstrap; version expected to drift.

## Local Storage And Secrets

- Runtime config: `config/settings.json`, `config/self.json`, `config/directives.json`, `config/instructions.md`.
- Secrets/compatibility: `.env`, `config/secrets.env`, and local settings keys.
- Runtime data: `data/`.
- Media: `mypics/`, `myvids/`.
- Cache: `.cache/`.
- Process metadata: `.alive-ai/`.

Status: decided.

## Local Data Lifecycle

Local runtime data, media, memories, Redis vectors, and OpenMind-linked memory are kept indefinitely by default. Alive-AI must not auto-expire or auto-delete them. Export, deletion, wipe, reset, uninstall, destructive sync, or replacement must be an explicit owner/operator action.

Status: decided by operator on 2026-06-10.

## Backup And Restore

Backup/restore is manual for now. The owner/operator backs up and restores the local Alive-AI project folder directly. First-class export/restore commands are not a current canonical requirement.

Status: decided by operator on 2026-06-10.

## Public Site Deployment

The public site is static. It uses `pages/` source and `docs/` output. It cannot call or host the local FastAPI runtime. The static dashboard demo is not live state.

Status: decided.

## Docker

Dockerfile uses `python:3.11-slim`, installs system/Python dependencies, copies the app, and runs `python main.py`.

`docker-compose.yml` defines:

- `alive-ai` service, port `8080:8080`, volume-mounted project, `.env`, and Redis dependency.
- `redis` service using `redis/redis-stack-server:latest`, port `6379:6379`, persistent volume.

Canonical WebUI binding:

- Normal local runs bind to `127.0.0.1` by default.
- Docker/container runs bind to `0.0.0.0` inside the container so the configured Docker port mapping can expose the dashboard to the host.
- Do not bind normal local runs to `0.0.0.0` by default.

Implementation gap: `main.py` currently starts WebUI on `127.0.0.1` unconditionally. Code must become container-aware before Docker WebUI exposure can be claimed as working.

Status: decided by operator delegation on 2026-06-10.

## Release Readiness

Canonical rule: if it works, it can publish. "Works" means the touched release surface has been verified with the relevant local checks.

- Always run `npm run smoke` for normal package/runtime changes.
- Run focused Python tests or `python3 -m unittest` when runtime/provider/WebUI/MCP behavior changes.
- Run `npm pack --dry-run` when package contents, npm metadata, CLI scaffold files, or release packaging changes.
- Run installed/scaffolded project smoke when CLI lifecycle, update, start/stop, package contents, or runtime path resolution changes.
- Run public site build/static verification when `pages/` or generated `docs/` output changes.
- Do not publish from source-only confidence when the changed behavior can differ in the packed or installed project.

Status: decided by operator on 2026-06-10.

## Deployment Gaps

- Docker WebUI binding is decided but not yet implemented in `main.py`.
- No canonical hosted backend environment exists for the live runtime.

Status: unknown.

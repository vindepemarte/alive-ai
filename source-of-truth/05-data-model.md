# Data Model

Alive-AI is local-first and primarily file-backed. There is no canonical relational database schema in this repo at bootstrap.

Status: decided from file layout and runtime modules.

## Canonical Entities

- Project: one local Alive-AI installation or cloned package checkout.
- Agent identity: the configured AI person in `config/self.json`.
- Runtime settings: provider, channel, WebUI, memory, media, MCP, and behavior settings in `config/settings.json`.
- Directives: behavioral rules in `config/directives.json` and optional `config/instructions.md`.
- User: a normalized local user id, Telegram user id, terminal owner id, or WebUI user id.
- Message: incoming/outgoing visible chat row, episodic memory row, Telegram message, or WebUI journal row.
- Internal state: emotion, soul, circadian, somatic, attachment, subconscious, conflict, dream, narrative, and related JSON stores under `data/`.
- Memory: working, episodic, semantic, emotional, procedural, autobiographical, dream, shadow, optional OpenMind records, and optional Redis vectors.
- MCP server/tool: configured server declaration and tool metadata from `MCP_SERVERS`.
- MCP proposal: redacted local proposal row under `data/mcp/proposals.json`.
- MCP audit event: redacted append-only audit row under `data/mcp/audit.jsonl`.
- Media asset: user-provided or generated image/video/audio files under `mypics/`, `myvids/`, output folders, and related metadata.

Status: decided/assumed from modules and examples.

## Config Files

- `config/settings.json`: runtime settings created by setup; treated as runtime source of truth.
- `config/self.json`: configured agent identity/personality and self-authorship state.
- `config/directives.json`: identity directives and safety/behavior boundaries.
- `config/instructions.md`: optional local instruction layer.
- `.env` and `config/secrets.env`: compatibility and secrets inputs loaded before settings are exported by `main.py`.

Status: decided.

## Project Storage

- `data/`: local durable runtime state.
- `data/users/<user>/`: per-user durable stores.
- `data/users/<user>/webui_chat.jsonl`: visible WebUI chat journal.
- `data/mcp/proposals.json`: MCP proposal store.
- `data/mcp/audit.jsonl`: MCP audit log.
- `.alive-ai/runtime.json`: project-local runtime marker used by stop/start lifecycle.
- `.cache/`: local model/embedding/cache artifacts.
- `mypics/` and `myvids/`: local media owned by the project/operator.

Status: decided where files are evidenced by code/docs; runtime marker is decided from prior release notes and should be rechecked before editing CLI lifecycle.

## Retention And Deletion

- Local `data/`, media folders, memories, Redis vectors, and OpenMind-linked memory are retained indefinitely by default.
- Nothing in those stores should be automatically deleted, expired, pruned, reset, or overwritten as a lifecycle policy unless the owner/operator explicitly requests export, deletion, wipe, reset, uninstall, or replacement.
- Redis vectors are optional derived/search data, but when enabled they follow the same owner-explicit deletion rule.
- OpenMind-linked memory is treated as owner-controlled memory from Alive-AI's perspective. Do not implement automatic remote-memory deletion or destructive sync without an explicit owner action and documented contract.
- Conversation users do not gain deletion/export authority just by chatting with the companion.

Status: decided by operator on 2026-06-10.

## Backup And Restore

- Backup/restore is manual for now.
- The official backup unit is the owner/operator's local Alive-AI project folder, including config, data, media, and runtime-owned local state.
- Restore is manual project-folder restoration by the owner/operator.
- Alive-AI does not currently have first-class export/restore commands as a canonical requirement.
- Do not add automatic backup, cloud sync, or destructive migration behavior without updating the source of truth first.

Status: decided by operator on 2026-06-10.

## Ownership Rules

- Local project files belong to the owner/operator.
- The owner/operator is the person who runs the runtime and owns config, data, media, secrets, and privileged controls.
- A conversation user is any person talking to the companion through terminal, WebUI, Telegram, or another input channel.
- The owner/operator can also be the active conversation user.
- Another person can be a conversation user without becoming the owner/operator.
- `TELEGRAM_OWNER_ID` controls owner-only Telegram commands and MCP approval identity.
- Conversation users can converse; owner-only commands must not be exposed to non-owner Telegram users.
- WebUI active user resolution follows explicit user id, live active user, configured owner, runtime state, disk activity, and fallback `webui`.

Status: decided.

## Derived Or Cache Data

- Redis vector memory is optional derived/search data and should not replace file-backed memory/state.
- Public `docs/` output is generated/deployable static output from `pages/`, but it is also shipped in the npm package as a public portal artifact.
- Benchmark outputs under `benchmarks/report.html` and `benchmarks/results/` are local-only artifacts and should not become source truth without manual sanitization.

Status: decided/assumed.

## Open Data Questions

- Whether `.alive-ai/runtime.json` structure should be documented as a stable contract is unresolved.
- Whether OpenMind cloud records have a formal import/export/restore contract with local files is unresolved.

Status: unknown.

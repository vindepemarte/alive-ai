# Code Rules

## Source-Of-Truth Discipline

- Update `source-of-truth/` in the same change when behavior, APIs, config, deployment, or naming changes.
- Missing project truth routes to `onboard-source`.
- Changing decided truth routes to `remake-source`.
- Do not add a second authority for the same behavior in README, comments, or ad hoc notes.

Status: decided.

## Local-First Rules

- Runtime data, identity, config, cache, and media must resolve inside the local project unless explicitly configured otherwise.
- Public package/repo must not include private personas, private media, runtime data, secrets, benchmark transcripts, or local reports.
- Local WebUI is a runtime dashboard, not a hosted backend.
- Local `data/`, media, memories, Redis vectors, and OpenMind-linked memory are retained indefinitely by default; destructive cleanup requires explicit owner/operator action.
- Backup/restore is manual project-folder backup for now; first-class export/restore commands are not canonical requirements yet.

Status: decided.

## Provider And Response Rules

- Preserve provider-specific routing in `brain/llm/`; do not silently change provider aliases.
- Do not send OpenRouter-only reasoning controls to generic OpenAI-compatible providers.
- Keep `OPENROUTER_THINKING_ENABLED` provider-specific and opt-in.
- Do not weaken prompt leak/reasoning artifact rejection without adding or updating tests.
- Fallback responses must answer the current turn and must not replay stale unrelated text.

Status: decided from tests and prior bug memory.

## MCP Safety Rules

- Normal chat must not directly execute MCP tools.
- MCP default state is off/default-deny.
- Sensitive args/env values must stay redacted in status, proposal, and audit outputs.
- Owner approval remains required before execution.
- Dangerous scopes such as filesystem, shell, secrets, and broad network access must stay denied unless deliberately designed and documented.

Status: decided from `core/mcp/` and tests.

## WebUI Rules

- Live WebUI endpoints must remain local and secret-safe.
- Settings saves must validate JSON and write atomically.
- Dashboard snapshots should hydrate from durable stores, not only current browser session state.
- If changing dashboard code, verify the shipped static WebUI path because the npm package runs locally without a frontend build step.
- Keep `/api/plugins/status` diagnostic/secret-safe. Do not treat it as a stable public plugin API.

Status: decided.

## CLI And Release Rules

Release rule: publish when the changed product surface works. There is no rigid ceremony beyond proving the affected package, runtime, or public site path is functioning.

Default lightweight smoke check:

```bash
npm run smoke
```

Use broader verification only when relevant to the change:

```bash
python3 -m unittest
npm pack --dry-run
npm view alive-ai version --silent
```

For npm/runtime release changes, verify the source checkout, package contents, and installed/scaffolded project path when those surfaces can differ. Prior bugs showed source-checkout tests can pass while installed-project behavior differs.

For GitHub Pages changes, verify the public static site build/output path. Public Pages cannot depend on the local Python/FastAPI runtime.

Status: decided by operator on 2026-06-10.

## Frontend/Public Site Rules

- If editing `pages/src/`, update generated `docs/` output only through the established build path.
- Do not manually edit minified `docs/assets/*` as source truth.
- Public Pages cannot rely on the Python/FastAPI runtime.

Status: decided/assumed.

## Coding Constraints

- Keep config keys stable unless source-of-truth and setup/update migration behavior are updated.
- Keep owner-only Telegram commands gated.
- Keep benchmark outputs ignored/local unless manually sanitized.
- Keep `data/`, `.cache/`, `.alive-ai/`, media, and secrets out of public release artifacts unless intentionally listed as empty scaffold folders.
- Public plugin API remains roadmap-only; do not promise external plugin compatibility or stable third-party plugin contracts yet.

Status: decided.

# Open Questions

This file keeps live truth, risks, canonical decisions, and unresolved decisions separate.

## Live Truth

- Alive-AI is a public local-first emotional companion runtime/package with npm CLI, Python runtime, terminal chat, Telegram, optional OpenMind, optional Redis, optional MCP, and local WebUI.
- Current metadata version is `0.2.5` in both `package.json` and `pyproject.toml`.
- The repo did not have a source-of-truth directory, `AGENTS.md`, or `CLAUDE.md` before this bootstrap.
- WebUI FastAPI endpoints are local and served by the running Python runtime.
- The public Pages site is static.
- MCP is default-deny and approval-gated.

Status: decided.

## Risks And Collisions

- Docker compose maps `8080`, and canonical source says container runs should bind WebUI to `0.0.0.0`, but `main.py` currently binds `127.0.0.1` unconditionally. Treat Docker WebUI exposure as not implemented until code is changed and verified.
- README mixes current features, roadmap, and research vision; future agents must not treat roadmap items as implemented.
- Public generated `docs/` output can drift from `pages/src/` if not rebuilt.
- Provider response sanitization is high-risk: too loose leaks prompt/reasoning artifacts; too strict rejects valid user-facing answers.
- Prior installed-project issues showed source checkout validation is not enough for CLI/package releases.
- Example identity (`Alice`) can be mistaken for the product identity; the agent identity and framework name must stay separate.

Status: decided.

## Canonical Decisions

- Product name is `Alive-AI`.
- Package name is `alive-ai`.
- Public positioning is `emotional companion runtime`.
- Canonical roles are owner/operator and conversation user.
- The owner/operator runs the runtime and owns local config, data, media, secrets, and privileged controls.
- A conversation user is anyone talking to the companion; it can be the owner/operator or another non-owner user.
- The app is local-first and project-owned by the operator.
- `config/settings.json` is the runtime settings source created by setup.
- Runtime state and memories are file-backed under `data/`, with Redis and OpenMind optional.
- Local `data/`, media, memories, Redis vectors, and OpenMind-linked memory are retained indefinitely until explicit owner/operator export or deletion.
- Backup/restore is manual project-folder backup for now; first-class export/restore commands are not canonical requirements yet.
- Normal local WebUI runs bind to `127.0.0.1`; Docker/container WebUI runs should bind to `0.0.0.0` inside the container so port mapping exposes the dashboard to the host.
- Release rule is practical: if the touched release surface works under relevant verification, it can publish.
- Public plugin API is roadmap only for now; no stable external plugin contract exists yet.
- Brand direction stays close to the existing dark technical/cyber companion style for now, with UI colors matched to the actual logo palette.
- Owner-only commands are gated by configured owner id.
- Normal chat must not execute MCP tools directly.
- Public repo/package excludes private runtime data, secrets, personas, and media.
- Additional partner-style safety boundaries were deferred by the operator; no extra product-level safety policy is canonical yet beyond existing code/docs boundaries.

Status: decided.

## Open Decisions

1. Safety boundaries: additional non-negotiable safety and dependency boundaries for partner-style or emotionally attached agents are deferred. Keep this visible until the owner/operator defines them.

Status: unknown.

## Skipped For Now

- Billing, pricing, payouts, and immutable money ledgers are not current product surfaces in this repo.

Status: skipped.

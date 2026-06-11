# Alive-AI Source Of Truth

Status: initialized on 2026-06-10 from the live repo, package metadata, README, tests, and prior local memory notes. Repo-local files are canonical.

## Authority

`source-of-truth/` is the canonical project truth for Alive-AI. It constrains future AI work across product scope, runtime behavior, data ownership, API contracts, deployment, and unresolved decisions.

When code, old README text, stale release notes, or assumptions disagree with these files, future agents must surface the conflict and update the source of truth in the same change that changes behavior.

## Product Identity

- Product name: `Alive-AI` (decided from README, npm package, and public site copy).
- npm package name: `alive-ai` (decided from `package.json`).
- Python package/project name: `alive-ai-runtime` (decided from `pyproject.toml`).
- Current metadata version at bootstrap: `0.2.5` (decided from `package.json` and `pyproject.toml`; expected to drift with releases).
- Public positioning: emotional companion runtime (decided by operator on 2026-06-10).
- Supporting tagline: local-first emotional AI runtime with memory, impulses, terminal chat, Telegram, OpenMind, and a live WebUI (decided from README/package metadata).

## Canonical Scope

Alive-AI is canonically an emotional companion runtime. It is a local-first runtime and scaffold for emotionally continuous AI companions, giving a configured AI person persistent mood, memory, internal state, proactive impulses, terminal/Telegram input, optional voice/media, optional OpenMind memory, sandboxed MCP proposal infrastructure, and a local dashboard.

The project does not claim biological consciousness. It is an open-source simulation framework for affect, memory, autonomy, and inspectable local state.

## Source Files

- `01-product.md` - mission, users, scope, non-goals.
- `02-brand-visuals.md` - visual identity, assets, and frontend style truth.
- `03-user-flows.md` - CLI, setup, chat, Telegram, WebUI, memory, MCP, and benchmark flows.
- `04-tech-architecture.md` - runtime architecture, modules, constraints, and risks.
- `05-data-model.md` - local files, config, state, memory, and durable entities.
- `06-api-contracts.md` - WebUI endpoints, CLI contracts, provider contracts, and MCP contracts.
- `07-code-rules.md` - change rules, verification gates, release rules, and safety constraints.
- `08-deployment.md` - environments, package distribution, Pages, Docker, storage, and secrets.
- `09-open-questions.md` - live truth, risks, canonical decisions, and unresolved decisions.
- `10-glossary.md` - project vocabulary.
- `source-map.yaml` - machine-readable map of canonical facts and statuses.

## Status Vocabulary

- `decided`: evidenced by current code/docs or explicitly accepted by the operator.
- `assumed`: inferred from repo evidence but not explicitly confirmed.
- `unknown`: unresolved and must stay visible.
- `skipped`: intentionally not applicable for now.
- `deprecated`: old or legacy truth that should not guide new work.

## Agent Rule

Future agents must read `AGENTS.md`, this overview, and `source-map.yaml` before significant work. Missing truth routes to `onboard-source`; changing decided truth routes to `remake-source`.

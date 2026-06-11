# Product

## Mission

Alive-AI lets people run a local-first emotional AI companion with persistent emotional state, memory, impulses, and transparent runtime diagnostics. The product goal is not just answering prompts, but maintaining continuity across messages, idle time, memories, body-like state, and configured identity.

Status: decided from README and runtime modules.

## Positioning

The canonical public positioning is `emotional companion runtime`.

Research, general-agent, and autonomy language can support the product story, but it must not replace the primary hierarchy. Future public copy, docs, and release framing should lead with the companion-runtime use case, then explain local-first state, memory, affect, autonomy, and diagnostics as the reasons the companion feels continuous.

Status: decided by operator on 2026-06-10.

## Primary Users

- Local operators who scaffold an emotional companion with `npx alive-ai@latest init my-ai`.
- Companion, character, study partner, creative persona, or experimental agent builders who accept the boundary risks of emotionally continuous systems.
- Developers and researchers experimenting with affect, autonomy, memory, provider routing, and local-first companion runtimes.

Status: decided for positioning; assumed for exact audience order from README language and command surface.

## Roles

Alive-AI has two canonical roles for now:

- Owner/operator: the person who runs the runtime and owns the local project, config, data, media, secrets, and privileged control surfaces.
- Conversation user: the person talking to the companion. This can be the owner/operator or another user who only chats with the companion.

No other product roles are canonical at this time. Future roles for WebUI, Telegram, MCP, plugins, hosted surfaces, moderation, or sharing must be added to the source of truth before implementation.

Status: decided by operator on 2026-06-10.

## Core Capabilities

- Scaffold/update/uninstall a local project through the npm CLI.
- Configure identity, directives, providers, Telegram, voice, images, OpenMind, MCP, and Redis through local JSON/env files.
- Run terminal chat or Telegram input against the same Python runtime.
- Preserve internal state under project-local `data/`.
- Stream a local WebUI dashboard from the live runtime.
- Support optional local and cloud LLM providers: Ollama, OpenRouter, ZAI, LM Studio, llama.cpp server, vLLM, MLX-LM server, and generic OpenAI-compatible endpoints.
- Keep OpenMind optional as a long-term semantic memory bridge.
- Keep MCP tools disabled by default and separated into propose, approval, and execution flows.
- Run local human-feel benchmarks against the WebUI runtime and baselines.

Status: decided from README, config examples, and source modules.

## Non-Goals And Boundaries

- Alive-AI must not claim biological consciousness.
- The public repo must not include private personas, secrets, local media, or runtime data.
- Normal chat must not directly execute MCP tools.
- The runtime must not reveal hidden reasoning, system prompts, secrets, file paths, or private memory unless the operator explicitly requests allowed information.
- Emotional continuity must not be used to manipulate dependence; operator control stays central.
- Additional non-negotiable safety boundaries for emotionally attached or partner-style companions are not specified yet. Do not invent new product-level safety policy from silence; use the existing code/docs boundaries until the owner/operator defines more.

Status: decided for existing boundaries; additional partner-style boundaries deferred by operator on 2026-06-10.

## Product Surfaces

- npm package and CLI: `alive-ai`.
- Python runtime: `main.py` and packages under `core/`, `brain/`, `heart/`, `input/`, `output/`, `skills/`, and `webui/`.
- Local dashboard: `http://127.0.0.1:8080` by default.
- Public static portal: `https://vindepemarte.github.io/alive-ai/`.
- Static dashboard demo: `https://vindepemarte.github.io/alive-ai/dashboard.html`.

Status: decided from README and package metadata.

## Roadmap Truth

Implemented items are listed in README and should be treated as user-facing claims only when the matching code path still exists. Roadmap items such as desktop wrapper, browser onboarding wizard, more channels, plugin API, social presence, and autonomous life-direction planning are not current product guarantees.

Status: decided.

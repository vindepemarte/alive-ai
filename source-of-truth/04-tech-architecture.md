# Tech Architecture

## Stack

- CLI/runtime packaging: Node.js package with `cli/index.js`.
- Runtime: Python 3.11+ async application, entrypoint `main.py`.
- WebUI backend: FastAPI served locally by the runtime.
- Static public portal: React/Vite source under `pages/`, built into `docs/` for GitHub Pages.
- Optional services: Ollama, OpenRouter, ZAI, OpenAI-compatible model servers, OpenMind, Redis Stack, Docker, Telegram, gTTS/Google TTS/VibeVoice, Fal.ai.

Status: decided from package metadata, README, and source files.

## Main Modules

- `core/`: runtime lifecycle, events, config, state, directives, message handling, paths, MCP, plugin registry, and response shaping.
- `brain/`: LLM providers, memory layers, subconscious/default-mode loops, curiosity, narrative, dreams, language, and profile learning.
- `heart/`: affective/body-like systems such as emotions, hormones, circadian rhythm, interoception, attachment, and somatic state.
- `input/`: terminal and Telegram adapters plus command routing.
- `output/`: text, voice, image, and media output support.
- `skills/`: optional runtime skills such as self-authorship, scheduling, media managers, memory callbacks, and relationship modules.
- `webui/`: FastAPI dashboard server, bridge, static dashboard, and persistence projection.
- `benchmarks/`: human-feel and runtime comparison harness.

Status: decided from file layout and manifest.

## Runtime Bootstrap

`main.py` sets project-local environment defaults:

- `ALIVE_AI_ROOT`
- `ALIVE_AI_DATA_PATH`
- `DATA_PATH`
- HuggingFace/sentence-transformers cache paths under `.cache/`
- `TOKENIZERS_PARALLELISM=false`

It reads `.env`, `config/secrets.env`, and `config/settings.json`; then it initializes `core.self.Self`, optional WebUI, and the configured input channel.

Status: decided from `main.py`.

## Provider Architecture

LLM clients are built through `brain/llm/factory.py` and routed through `UnifiedLLM` when fallback behavior is enabled. Provider names are canonicalized so aliases like `local`, `lm-studio`, and `mlx-lm` map to implementation names.

OpenRouter reasoning controls are provider-specific and opt-in through `OPENROUTER_THINKING_ENABLED`; generic OpenAI-compatible providers must not receive unsupported reasoning controls.

Status: decided from `brain/llm/` and tests.

## Response Shaping

Visible provider content is sanitized to strip reasoning artifacts, prompt-template leaks, role leakage, and unusable fragments. Known bad leak patterns such as `structure:`, `Recent_turns`, `assistant_response:`, and `current_user_message:` are rejected.

Reply delivery is state-led and intentionally non-uniform. `core/response_texture.py` rolls a per-turn reply shape (clipped/compact/flowing/rambling/fragmented/trailing) weighted by live emotion, sleepiness, and energy, never repeats the previous shape at full weight, and forces a length contrast after several same-length replies. Long replies can be delivered as 2-3 separate message bubbles split only at natural boundaries, with probability shaped by arousal/energy and suppressed by sleepiness. Typing delay before a reply scales with sleepiness and sadness (slower) and high arousal (faster). Texture nudges are skipped for identity answers, system-transparency answers, and active boundary turns.

Status: decided from `core/response_texture.py`, `core/message_handler.py`, and tests.

## Dream Consequences

Dreams are consequential state, not decoration. At sleep time `brain/dreams.py` derives a dream tone (nightmare/anxious/melancholy/tender/surreal) from the persisted pre-sleep emotional state with weighted randomness, and sources dream fragments from recent high-emotion memories. Each dream stores a tone, a named waking feeling, and an emotional residue. On the first message after waking (user wake or natural wake within the last hour), the runtime consumes the residue exactly once, nudges the live heart dimensions, recomputes core affect, and persists it; the mood instruction names the lingering feeling so the reply is colored by the dream without explaining mechanics.

Status: decided from `brain/dreams.py`, `core/message_handler.py`, `core/thinking.py`, and tests.

## Persistence Architecture

Runtime state is file-backed under `data/` by default. Redis is optional. OpenMind is optional. The local project folder owns runtime config, data, media, cache, and process metadata.

Status: decided.

## WebUI Architecture

The live WebUI is served by FastAPI from `webui/static/index.html`, streams SSE from `/events`, and composes snapshots from live bridge state and durable stores. The public Pages site is separate static React output and cannot run the Python/FastAPI backend.

Normal local runs should bind the WebUI to `127.0.0.1` by default. Container/Docker runs should bind the WebUI to `0.0.0.0` inside the container so the compose `8080:8080` port mapping can expose the dashboard to the host. Host exposure is then controlled by Docker port publishing, not by changing the normal local loopback default.

Status: decided.

## MCP Architecture

MCP uses declaration/catalog loading, permission checks, proposal storage, approval, execution, and redacted audit logs. Default state is disabled/off. Dangerous scopes such as filesystem, shell, secrets, and broad network access are denied unless explicitly allowed and still approval-gated.

Status: decided.

## Known Architecture Risks

- Current code mismatch: Docker compose maps port `8080`, and canonical source now says container runs should bind WebUI to `0.0.0.0`, but `main.py` currently starts WebUI on `127.0.0.1` unconditionally. Implement container-aware binding before claiming Docker WebUI exposure works.
- Public Pages docs/assets can drift from runtime behavior if the React source and generated `docs/` output are not updated together.
- The README roadmap mixes implemented features and future plans; future agents must not treat unchecked roadmap items as live behavior.
- Provider routing and response shaping are high-risk because valid provider output can be rejected locally if sanitization is too broad.

Status: decided.

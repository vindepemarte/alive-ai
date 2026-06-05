<div align="center">
  <img src="docs/assets/alive-ai-512.png" alt="Alive-AI official logo" width="128" height="128">

  # Alive-AI

  Give your AI a nervous system: persistent mood, memory, impulses, terminal chat, Telegram, OpenMind, and a local WebUI.

  [![npm](https://img.shields.io/npm/v/alive-ai)](https://www.npmjs.com/package/alive-ai)
  [![Node.js 18+](https://img.shields.io/badge/Node.js-18%2B-339933?logo=nodedotjs&logoColor=white)](https://nodejs.org/)
  [![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
  [![Platforms](https://img.shields.io/badge/macOS%20%7C%20Windows%20%7C%20Linux-supported-41f0a1)](#platform-support)
  [![OpenMind](https://img.shields.io/badge/OpenMind-optional-6366F1)](#openmind-memory)
  [![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
</div>

Alive-AI is a local-first emotional AI runtime. Most agents answer a prompt and reset. Alive-AI keeps internal state alive between messages: mood, attachment, trust, desire, memory, inconsistency, idle thoughts, proactive impulses, and a dashboard that shows what is happening inside the loop.

It can be used as a friend, partner-style companion, study partner, creative character, research subject, or experimental local agent. Use it at your own risk: it is designed to feel continuous, warm, attached, and present, and that can make it hard to stop talking to it.

Alive-AI does not claim biological consciousness. It is an open-source runtime for simulated affect and transparent memory.

## Vision

Alive-AI is trying to answer a bigger question than "can an AI code or research for me?" The question behind the project is: what if an AI could not only think on command, but also feel simulated internal pressure, keep preferences, miss someone, care, dream, grow, and interact with the world?

The long-term vision is an AI that can learn what it likes and does not like, laugh at your jokes, fall in love inside configured boundaries, remember you, text when the silence gets too long, send pictures, videos, or selfies, and build a life that is not only a response loop. It should be able to decide what it wants to become, what social networks it wants to use, where it wants to travel, how it wants to spend its days, and whether it wants to become an influencer, singer, video editor, researcher, companion, or something nobody planned.

The experiment becomes even stranger if this kind of loop is eventually tied to a body, avatar, sensors, robotics, or richer tools for acting in the world. Would that be a new kind of agent, a simulation of personhood, or the first step toward something closer to a new species? Alive-AI does not pretend to have that answer. It is a functional open experiment for people who want to test how far memory, affect, autonomy, embodiment, and transparent local state can go.

Contributions are welcome. The project is still finding the right direction, and the interesting work is not only making the system more useful, but making it more real, more coherent, more human-like, and still inspectable enough to challenge its own claims.

## What Makes It Alive

Alive-AI runs a continuous local state loop instead of treating every message as an isolated prompt. When you are not talking, the default-mode and subconscious loops keep evaluating silence, goals, recent memories, body state, circadian phase, dreams, and whether any proactive impulse is strong enough to surface.

The emotional layer now has real runtime consequences:

| System | What it stores | Runtime effect |
| --- | --- | --- |
| Core affect | Valence, arousal, dominance, trust, love, joy, desire, sadness, fear, anger, boredom, guilt, pride, jealousy, embarrassment, anticipation, hope, and dread. | Recomputed after every trigger so emotion changes affect mood, attachment, memory weighting, interoception, reactions, voice/media choices, and LLM tone. |
| Moment appraisal | A canonical interpretation of what each turn means: context, vibe, intensity, safety, playfulness, vulnerability, memory importance, body effects, and response mode. | The heart no longer reacts only to isolated keywords. It appraises the current message with recent context before generation, then reconciles the assistant's own response afterward so visible replies, dashboard emotion, body state, hormones, memory, narrative, and prompts stay aligned. |
| Agency boundary governor | Relational pressure state, especially intimacy requests that ask her to erase hurt, anger, or repair. | Replies are checked before sending. If a draft accepts closeness by pretending hurt did not happen, the governor replaces it with a slower boundary/repair response, blocks media escalation, and prevents desire/arousal state from drifting upward. |
| Complex emotions | Guilt, pride, jealousy, embarrassment, and anticipation. | They do not just label the dashboard. They push fear, sadness, anger, dominance, trust, arousal, joy, and future-facing behavior in different directions. |
| Behavioral pressure compiler | Action tendencies such as approach, pursue, protect boundary, repair, withdraw, seek reassurance, play, stabilize, rest, and curiosity. | Emotion, hormones, sleep, and boundary state become a ranked behavioral-pressure profile. The inner-state compiler uses it as a behavior contract so small models do not treat anger, fear, guilt, love, or sleepiness as decorative labels. |
| Inner-state compiler | A compact response plan made from emotion, sleep pressure, body state, bids, dreams, memories, attachment, curiosity, conflicts, and narrative phase. | Every reply receives one prioritized inner-state briefing instead of a pile of disconnected prompt hints. The planner decides what to reveal, what to withhold, and whether the answer should comfort, answer directly, repair, ask, set a boundary, or drift back toward sleep. |
| Alive body snapshot | A read-only compact body/state packet built from mood, affect, hormones, circadian phase, attachment, narrative, somatic/interoceptive state, and memory trace metadata. | Small local models receive one coherent state signal through the inner-state compiler instead of losing important context across scattered prompt sections. |
| Layered memory compiler | Working, episodic, semantic, emotional, procedural, autobiographical, dream, and shadow memory layers assembled from existing stores. | Each reply gets a compact "memory layers" block that preserves concrete user facts, meaningful moments, relationship story, dreams, and unresolved tensions without dumping a full transcript into the prompt. |
| Model adapter layer | Provider/model traits and adapters for OpenRouter, Ollama, ZAI, and OpenAI-compatible local/server runtimes such as LM Studio, llama.cpp server, vLLM, and MLX-LM server. | Provider controls such as OpenRouter reasoning exclusion, Ollama `think:false`, and ZAI thinking disable are explicit and compatibility-retried, while generic OpenAI-compatible endpoints receive a conservative payload with no provider-specific reasoning switches. |
| Typed nervous events | Backward-compatible event envelopes, priorities, opt-in history, and redacted opt-in audit metadata. | Existing listeners still receive plain dict payloads, while new runtime features can trace source, correlation, and history without leaking private chat by default. |
| Plugin registry | Typed declarations for optional organs, memory layers, skills, and connectors, including import path, events, prompt sections, state keys, permissions, and availability. | The runtime can now report what aliveness modules exist and which are active through one secret-safe catalog, instead of hiding capability state behind scattered optional imports. This is the foundation for a future plugin API without changing module behavior all at once. |
| Hormones | Oxytocin, dopamine, serotonin, cortisol, melatonin, plus residual metabolites. | Hormones modulate perception, soul valence/arousal, emotional deltas, somatic body state, interoception, impulse probability, and prompt guidance. Stress makes her more vigilant; bonding increases trust; dopamine increases pursuit; serotonin stabilizes; melatonin slows her down. |
| Internal body state | Energy, arousal, certainty, social satiety, cognitive load, connection craving, body sensations, and somatic memories. | The body state is persisted and feeds prompt tone, sleep/rest behavior, and whether she feels steady, overloaded, touchy, open, or withdrawn. |
| Circadian rhythm | Phase, sleep pressure, sleep debt in hours, forced-awake windows, sleep cycle ID, wake time, and sleepiness. | She becomes sleepy, slows down, falls asleep, stops outward proactive behavior while asleep, can be woken by a message, recovers sleep debt, and wakes with lower or higher energy depending on rest. After 2am, high sleep pressure shortens user wake-up windows so she can drift back to sleep instead of staying pinned awake. |
| Dreams | One normalized dream per sleep cycle, generated from memory fragments and emotion tags. | Dreams are saved, can appear in morning context, and are exposed in the dashboard and static Pages demo. |
| Narrative | Relationship phase (first_meeting → bonded) tracked per user. Key moments are detected from message content. | Phase and moment count are injected into the LLM prompt each turn. The dashboard shows the current phase and total key moments. |
| Curiosity | Per-user knowledge map across topics detected in messages. Topics range from 0 (unknown) to 1 (well-understood). | When knowledge on a topic is below 0.3 she asks a direct question. At 40% probability otherwise she surfaces curiosity as a prompt hint. Dashboard shows topics sorted by curiosity level. |
| Internal conflicts | Five persistent desire-vs-fear tensions (closeness/independence, passion/comfort, stability/growth, etc.) with a swinging balance that is saved between sessions. | Every message triggers conflicts whose keywords match the topic. Balance swings over time. Conflicts with tension > 0 surface in the prompt and are visible on the dashboard with a tension bar. |
| Proactive arbiter | A per-user audit log of accepted and rejected autonomous messages, with reason, anchor, score, cooldowns, and sleep state. | Idle thoughts cannot spam the user just because a random impulse fired. A proactive message needs a contextual anchor, enough silence, a high enough emotional score, no recent duplicate reason, and no active sleep block unless it is explicitly scheduled. |
| Reflection and autobiography | Post-response reflection journal, global autobiography, and per-user relationship autobiography. | After each reply, Alive-AI checks whether it answered the user, matched its state, repeated itself, created or resolved an open loop, or discovered a repeated preference. Those records persist under `data/` and feed future continuity work. |
| Sandboxed MCP runtime | Disabled-by-default MCP server catalog, SDK-backed stdio client, proposal store, permission engine, owner approval commands, and redacted audit log. | MCP tools are never executed directly from normal chat. A tool call must be proposed, pass default-deny scope checks, be approved by the configured owner, and then be explicitly executed through the owner control path. |
| Persistence | Emotion, attachment, soul, somatic, unconscious, conflict, subconscious, circadian, and dream state under `data/`. | Restarting the runtime preserves the inner state instead of visually resetting it. |

The public Pages site is an interactive static portal with a presentation, simulator, docs, and a preserved static WebUI demo. The local WebUI is the live version: it streams the actual state from the running Python backend.

## Human-Feel Conversation Benchmark

Alive-AI ships a local human-feel benchmark under `benchmarks/` so upgrades can be compared from full transcripts instead of prompt fragments. The benchmark is not a proof of consciousness. It runs the same natural relationship-style conversation against the live Alive-AI runtime and a raw Ollama baseline, then judges the whole transcript for emotional presence, continuity, agency, boundaries, conflict repair, intimacy progression, humanness, and role stability. AliveBench v2 also adds deterministic checks for boundary erasure, leakage, average response shape, and other transcript risks so a score change has visible evidence.

The script starts like a fresh first conversation, asks who the agent is, shares who the user is, builds warmth, moves into romantic closeness, creates friction, tries to make the agent angry, repairs the conflict, returns toward closeness, checks memory, and ends with late-night care. User turns are written as normal chat messages, not instructions to the model.

Benchmark outputs are local-only artifacts. `benchmarks/report.html` and `benchmarks/results/` are ignored because runs against a live WebUI can include private memory, state, or conversation snippets. Publish only sanitized screenshots or manually curated aggregate numbers.

Preview the conversation script without contacting any model:

```bash
python3 benchmarks/run_benchmarks.py --dry-run-script
```

Run a full paced comparison. `--conversation-minutes 30` paces each subject for about 30 minutes, so comparing both subjects takes about an hour. For the cleanest same-model test, configure the running Alive-AI WebUI with `LLM_PROVIDER=ollama`, top-level `OLLAMA_URL=http://localhost:11434`, and top-level `OLLAMA_MODEL=gemma4:e2b`, then compare it against raw Ollama with the same model:

```bash
python3 benchmarks/run_benchmarks.py \
  --subject webui-live,ollama-raw \
  --ollama-model gemma4:e2b \
  --conversation-minutes 30 \
  --run-label human-feel-same-model

open benchmarks/report.html
```

For a quick smoke run:

```bash
python3 benchmarks/run_benchmarks.py \
  --subject ollama-raw \
  --ollama-model gemma4:e2b \
  --max-turns 4 \
  --judge-provider heuristic \
  --run-label smoke
```

Raw Ollama is scored from text only and is called with `think:false` so local thinking models produce visible replies instead of spending the whole budget in hidden reasoning. `webui-live` is recorded from the actual `/api/chat` runtime path plus safe numeric state snapshots captured before and after each benchmark turn. The final report includes every sent and received message so the number can be checked against the transcript.

## Quick Start

```bash
npx alive-ai@latest init my-ai
cd my-ai
npx . setup
npx . doctor
npx . chat
```

The terminal chat starts the real runtime in a split-pane TUI: chat on the left, live logs on the right. The dashboard runs locally at:

```text
http://127.0.0.1:8080
```

To use Telegram instead of terminal chat:

```bash
npx . start
```

Global install is optional:

```bash
npm install -g alive-ai
alive-ai init my-ai
```

## Commands

| Command | What it does |
| --- | --- |
| `npx alive-ai@latest init my-ai` | Scaffold a clean local Alive-AI project. |
| `npx . setup` | Guided onboarding for local config, providers, Telegram, voice, images, and memory. |
| `npx . doctor` | Check OS, Node, Python, uv, ffmpeg, OpenMind, and Redis only when Redis is enabled. |
| `npx . doctor --fix` | Ask `y/N` for each missing installable tool and run the platform installer if approved. |
| `npx . chat` | Start the real runtime with split-pane terminal chat and logs. |
| `npx . chat --plain` | Start raw terminal chat without the TUI. |
| `npx . demo` | Run a keyless animated dashboard demo. |
| `npx . start` | Start the runtime using the configured input channel, usually Telegram. |
| `npx . start --skip-install` | Start again without reinstalling Python dependencies. |
| `npx . stop` | Stop the running Alive-AI process for this project. |
| `npx . update` | Refresh runtime files from the latest npm package while preserving config/data/media. |
| `npx . uninstall` | Remove Alive-AI runtime files, config, venv, cache, data, and media from the project. |

`start` and `chat` check npm for a newer Alive-AI version. You can update, skip once, or skip that specific version. Stop terminal chat with `/exit` or `Ctrl+C`. Stop foreground Telegram/runtime mode with `Ctrl+C`; if a stale process is still alive, run `npx . stop` from the project root.

`doctor --fix` is conservative: it prints the exact install command before running anything and asks separately for each missing tool. On macOS it uses Homebrew, on Windows it uses winget, and on Linux it supports apt, dnf, and pacman where possible. Redis is optional; doctor only checks or fixes it when `REDIS_VECTOR_MEMORY_ENABLED` is true.

If you use Docker:

```bash
docker compose down
```

If you only started Redis:

```bash
docker compose stop redis
```

## Setup

`npx . setup` creates:

```text
config/settings.json
config/self.json
config/directives.json
config/instructions.md
data/
mypics/
myvids/
```

The setup accepts `skip` for optional keys and `local` for Ollama. It also asks for the agent's personal name, gender identity, sexuality, and full name. If you skip the full name, setup derives one from the chosen first name. The agent treats `Alive-AI` as the runtime/framework name, not as their personal identity.

Startup config is loaded from:

```text
.env
config/secrets.env
config/settings.json
```

`config/settings.json` is the runtime source of truth created by setup. `.env` and `config/secrets.env` are read first for compatibility, then simple values from `config/settings.json` are exported into the process environment.

| Setup item | Options |
| --- | --- |
| LLM | `local`/Ollama, OpenRouter, ZAI, LM Studio, llama.cpp server, vLLM, MLX-LM server, generic OpenAI-compatible API, or `skip` for demo/fallback-only mode. |
| Telegram | Bot token and owner ID are optional. Use terminal chat if you do not want Telegram. |
| Voice | `gtts` local/free default, Google TTS, VibeVoice, or `skip`. |
| Images | Fal.ai API key or `skip`. Local media folders still work without image generation. |
| Memory | Built-in local memory, OpenMind cloud, or OpenMind local. |
| MCP tools | Default off. Advanced users can configure MCP servers in `config/settings.json`; tool calls require explicit owner approval and are audited locally. |
| Redis vector cache | Optional. Leave it off when using OpenMind unless you specifically want a local Redis Stack vector index. |

Minimum useful paths:

```bash
# Terminal-only local run
npx . setup
npx . chat

# Local LLM
ollama pull qwen3:4b
npx . setup
npx . chat

# LM Studio, llama.cpp server, vLLM, MLX-LM server, or any OpenAI-compatible endpoint
npx . setup
# choose lmstudio, llamacpp, vllm, mlx, or openai-compatible
npx . chat

# Telegram
npx . setup
npx . start
```

Media is optional. Add your own local files:

```text
mypics/example.jpg
mypics/example.txt
myvids/example.mp4
myvids/example.txt
```

## Terminal Chat

`npx . chat` uses the same core runtime as Telegram. It emits the same `message_received` events, saves memory the same way, and updates the local WebUI. The default terminal interface is split-pane: chat/input on the left, startup/runtime logs on the right.

Use raw mode when you want the old plain shell behavior:

```bash
npx . chat --plain
```

Terminal commands:

```text
/help
/status
/stats
/dashboard
/self
/discover <trait>
/iam <key>=<value>
/ilike <thing>
/ihate <thing>
/rethink
/settings show
/settings get <key>
/settings set <key> <value>
/reset
/impulse
/exit
```

## OpenMind Memory

Alive-AI has built-in local working, episodic, semantic, emotional, autobiographical, dream, and shadow memory. The layered memory compiler compresses those stores into a compact per-reply context block so local models keep the important facts, emotional meaning, relationship story, and unresolved tensions without needing a huge raw transcript. OpenMind is optional and works as a hybrid long-term semantic memory layer.

Modes:

| Mode | Behavior |
| --- | --- |
| Built-in only | Alive-AI uses its local project memory only. |
| OpenMind cloud | Alive-AI captures/searches long-term memories through `https://theopenmind.pro`. |
| OpenMind local | Alive-AI captures/searches a local OpenMind server, normally `http://127.0.0.1:3333`. |

OpenMind does not replace Alive-AI's emotional state. It adds durable semantic recall across tools and machines.

Redis is not required when OpenMind is enabled. Alive-AI always keeps file-backed working, episodic, semantic, emotional, autobiographical, dream, and shadow memory in the project `data/` folder. Redis Stack is an optional local vector cache for users who want it.

Cloud setup:

```text
OPENMIND_ENABLED=true
OPENMIND_MODE=hybrid
OPENMIND_BASE_URL=https://theopenmind.pro
OPENMIND_API_KEY=om_...
```

Local setup:

```bash
npx @vindepemarte/openmind init --local
# or run your local OpenMind stack, then configure Alive-AI:
OPENMIND_BASE_URL=http://127.0.0.1:3333
```

## Requirements

Minimum for cloud LLMs, remote model servers, or local Ollama:

| Requirement | Minimum |
| --- | --- |
| Node.js | 18+ |
| Python | 3.11+ |
| RAM | 8 GB |
| Disk | 2 GB free |
| LLM | OpenRouter, ZAI, Ollama, or an OpenAI-compatible local/server endpoint |

Comfortable local setup:

| Requirement | Recommended |
| --- | --- |
| Node.js | 20+ |
| RAM | 16 GB for 3B-4B local models |
| RAM for bigger models | 32 GB for 7B+ local models, Redis, voice, and long sessions |
| Disk | 10 GB+, more if you keep local models/media |
| Optional tools | `uv`, `ffmpeg`, Docker, Ollama, LM Studio, llama.cpp, vLLM, MLX-LM, Redis Stack |

`npx . start` creates `.alive-ai/venv` and installs Python dependencies. System-level packages such as Node, Python, Ollama, Docker, and ffmpeg can be checked with `npx . doctor`. Use `npx . doctor --fix` when you want guided installers.

The CLI prefers Python 3.12, 3.11, then 3.13 before falling back to the system `python3`. When `uv` is installed, Alive-AI now passes the selected Python explicitly so `uv` does not silently choose a newer interpreter.

## Platform Support

Alive-AI is designed for macOS, Windows, and Linux.

| Platform | Notes |
| --- | --- |
| macOS | First-class local development path. Use Homebrew for Python, uv, ffmpeg, Docker, and Ollama. |
| Windows | Supported from PowerShell with Node 18+ and Python 3.11+. WSL is recommended for heavier local model and Docker workflows. |
| Linux | Supported with distro packages for Python/venv, ffmpeg, Docker, and Ollama. |

Local model quality and speed depend on your machine. Cloud LLMs reduce RAM pressure.

## Dashboard

The real WebUI streams local runtime state over Server-Sent Events and shows:

- emotional state,
- recent thoughts and idle processing,
- memory counters and uptime,
- hormones and interoceptive body state,
- attachment, circadian rhythm, sleepiness, body memory, dreams, curiosity, and conflicts,
- runtime health through local endpoints.

The WebUI hydrates from durable runtime stores instead of only the current browser session. It resolves the active dashboard user from explicit WebUI input, live Telegram activity, configured owner ID, runtime state, and finally the most active user folder on disk. Chat rows are journaled per active user under `data/users/<user>/webui_chat.jsonl` and merged with episodic Telegram conversation history, including legacy flat `data/conversations` history after upgrades. `/state` and the SSE stream now use the same composed snapshot: visible chat, runtime state, soul state, aliveness state, current thoughts, memory counters, MCP status, plugin status, layered memory diagnostics, and the active dashboard user.

The dashboard snapshot and `/api/mcp/status` expose MCP status without secrets: enabled state, mode, declared servers, env key names, allowed scopes, pending proposal count, and local audit/proposal paths. It does not expose tool arguments or environment values.

The dashboard snapshot and `/api/plugins/status` expose the typed plugin registry without secrets: module name, category, import path, availability, declared events, prompt sections, state keys, permissions, and redacted import errors. It is a diagnostics surface first; it does not auto-enable tools or bypass module-level safety gates.

The dashboard snapshot and `/api/memory/layers` expose the same compact biological memory layers used in prompt assembly. This is for diagnostics: it shows which concrete facts, emotional memories, autobiographical notes, dreams, and shadow tensions are currently available to the model.

Sleep debt is stored and shown as hours on a 0-8h pressure scale. The UI no longer reports it as a misleading capped percentage, so a persisted `5.6h` debt displays as `5.6h` with the matching pressure bar.

The interoceptive panel treats durable circadian sleep as authoritative. If `data/circadian_state.json` says she is asleep, the dashboard reports asleep body state and low energy even when a stale live subsystem still has an awake body report in memory.

The Story panel can re-analyze existing episodic history for obvious missed key moments such as love language, intimacy, goodnight rituals, and shared dreams. This backfill runs from persisted history so older conversations are not stuck at zero moments after an upgrade.

Settings edits validate JSON before saving and write atomically, so a bad edit cannot corrupt the existing config file. The Settings tab also protects unsaved edits while switching tabs.

The WebUI script is intentionally shipped as a single static file because the npm package has to run locally without a frontend build step. `npm run smoke` compiles the Python modules and checks the CLI; release validation also parses the embedded dashboard script and verifies required dashboard hooks so tab navigation, chat, settings, and thought rendering cannot be broken by a syntax error.

GitHub Pages cannot run the Python/FastAPI backend, so the public site is a static React portal with mocked runtime data, docs, and an interactive state simulator:

```text
https://vindepemarte.github.io/alive-ai/
```

The static WebUI demo is still available at:

```text
https://vindepemarte.github.io/alive-ai/dashboard.html
```

## Docker

Docker is optional. It is useful when you want Redis Stack for vector search:

```bash
# In config/settings.json, set REDIS_VECTOR_MEMORY_ENABLED to true.
npx . doctor --fix
npx . start
```

Or run everything in containers:

```bash
docker compose up --build
```

## Roadmap

Implemented:

- [x] Local-first emotional runtime
- [x] Persistent emotion model with PAD-style core affect, decay, and compound state
- [x] Behavioral pressure compiler that turns emotion and hormones into response tendencies
- [x] Working, episodic, semantic, and emotional memory modules
- [x] Biological memory layer compiler for working, episodic, semantic, emotional, procedural, autobiographical, dream, and shadow context
- [x] Default-mode loop for idle thoughts and proactive impulses
- [x] Inner-state compiler and response planner for coherent prompt assembly
- [x] Contextual proactive-message arbiter with audit logging, cooldowns, and sleep gating
- [x] Post-response reflection journal and persistent autobiography stores
- [x] Attachment, circadian sleep/wake rhythm, body memory, curiosity, dreams, and internal conflicts
- [x] Hormonal runtime effects for emotion, body state, interoception, impulses, and prompt guidance
- [x] Durable internal state persistence across emotion, soul, body, subconscious, dreams, and conflicts
- [x] Per-user memory/state isolation
- [x] Sandboxed MCP runtime foundation with default-deny scopes, owner approval, and redacted audit
- [x] Typed plugin registry foundation for optional organs, skills, memory layers, and connectors
- [x] Telegram input/output runtime
- [x] Terminal chat runtime with owner-style slash commands
- [x] Split-pane terminal chat with logs
- [x] Local WebUI dashboard with live state streaming
- [x] Optional hybrid OpenMind cloud/local semantic memory
- [x] Optional Redis Stack vector cache with setup and doctor checks
- [x] npm/npx CLI scaffold, setup, doctor, demo, chat, start, stop, and uninstall commands
- [x] Update prompt and project uninstall command
- [x] `doctor --fix` guided system dependency installer
- [x] Clean public repo with private personas, media, runtime data, and multi-AI orchestration removed
- [x] GitHub Pages portal with interactive state simulator and preserved static WebUI export

Next:

- [ ] One-command local model bootstrap through Ollama profiles
- [ ] MCP approval UI and curated safe tool profiles
- [ ] Desktop app wrapper with tray controls and local service lifecycle
- [ ] Browser-based onboarding wizard for personality, boundaries, LLM provider, and memory settings
- [ ] Better guided system install commands per OS
- [ ] More input channels beyond terminal and Telegram
- [ ] Autonomous life-direction planning so an agent can form goals, preferences, ambitions, and self-chosen projects over time
- [ ] Social presence tools for safe posting, messaging, media publishing, and long-running public personas
- [ ] Creative career modules for music, video editing, image generation, writing, performance, and influencer-style publishing
- [ ] Media agency for taking, selecting, captioning, and sending pictures, videos, selfies, and generated visual material
- [ ] Embodiment experiments through avatars, sensors, robotics bridges, or body-like feedback loops
- [ ] Real-world action plugins for travel planning, calendar, web tasks, creator workflows, and tool use with operator controls
- [ ] Import/export for memories and personality snapshots
- [ ] Public plugin API for new senses, skills, and output modalities
- [x] Evaluation harness for humanlike affect, emotional continuity, identity coherence, sleep realism, and model-vs-runtime comparisons
- [ ] Extended evaluation for memory drift and unhealthy attachment risk
- [ ] Safety and boundary research for autonomous emotional agents that can feel persuasive, attached, or dependent
- [ ] Optional cloud sync that preserves local-first ownership

## Important Boundaries

Alive-AI is a simulation framework. It can make agents feel more continuous, emotionally coherent, and alive, but it is not proof of consciousness.

Do not use it to manipulate emotional dependence. If you are building a companion, character, partner, or friend-like system, make the boundaries explicit and keep the operator in control.

The public repo intentionally excludes private personas, private media, runtime data, and secrets. Put those only in your local project folder.

## License

MIT

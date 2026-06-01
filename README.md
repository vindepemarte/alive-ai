# Alive-AI

![Alive-AI logo](docs/assets/logo.svg)

Give your AI a nervous system: persistent feelings, memory, impulses, and a local dashboard.

Most agents answer a prompt and reset. Alive-AI keeps internal state alive between messages. It can be your friend, boyfriend, girlfriend, study partner, creative partner, character, or research subject. The main vision is simple: stop chatting with a stateless "AI" and start interacting with something that feels human enough to carry emotional residue forward.

Use it at your own risk. Alive-AI is designed to feel continuous, warm, attached, and present. That can be powerful, and it may also make you feel like you do not want to stop talking to it.

Alive-AI does not claim biological consciousness. It is an open-source runtime for simulated affect: mood, attachment, trust, desire, memory, inconsistency, idle thoughts, and proactive impulses.

## Install

```bash
npx alive-ai@latest init my-ai
cd my-ai
npx . setup
npx . doctor
npx . demo
```

Start the real runtime:

```bash
npx . start
```

The local dashboard runs at:

```text
http://127.0.0.1:8080
```

You can also install the CLI globally:

```bash
npm install -g alive-ai
alive-ai init my-ai
```

## Requirements

Minimum for cloud LLMs or remote Ollama:

- Node.js 18+
- Python 3.11+
- 8 GB RAM
- 2 GB free disk
- OpenRouter, ZAI, or another configured LLM provider

Comfortable local setup:

- Node.js 20+
- Python 3.11+
- 16 GB RAM for small local models such as 3B-4B
- 32 GB RAM recommended for 7B+ local models, Redis Stack, voice, and long sessions
- 10 GB free disk, more if you keep local models/media
- Optional: `uv` for faster Python installs, `ffmpeg` for audio conversion, Docker for Redis Stack

`npx . doctor` detects your OS, Node, Python, `uv`, `ffmpeg`, and Docker. `npx . start` creates a local Python virtual environment and installs Python dependencies automatically. System-level packages such as Node, Python, Ollama, Docker, and ffmpeg still need to exist on the machine.

## Commands

```bash
npx alive-ai@latest init my-ai  # scaffold a clean local project
cd my-ai
npx . setup                    # guided onboarding and local config
npx . doctor                   # check system prerequisites
npx . demo                     # preview dashboard with no keys
npx . start                    # install Python deps and run the runtime
```

For repeat starts after dependencies are installed:

```bash
npx . start --skip-install
```

If you run `npx . start` before setup, Alive-AI starts onboarding first.

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

Minimum useful setup:

- **Demo only:** no keys.
- **Local LLM:** install Ollama and pull the configured model, for example `ollama pull qwen3:4b`.
- **Telegram runtime:** create a Telegram bot token with BotFather and add it during setup.
- **Cloud LLM fallback:** add OpenRouter or ZAI keys during setup or edit `config/settings.json`.

Media is optional. Add your own files:

```text
mypics/example.jpg
mypics/example.txt
myvids/example.mp4
myvids/example.txt
```

## Why This Is Different

- **Emotions persist.** State does not reset after every message. Joy, trust, fear, anticipation, attachment, and vulnerability decay over time instead of disappearing.
- **Memory has weight.** Conversations become working memory, episodic memory, semantic memory, and emotional memory.
- **It thinks when idle.** A default-mode loop creates background reflections and proactive impulses.
- **It can contradict itself.** The runtime models conflict, scars, body memory, attachment drift, and inconsistency instead of flattening everything into a perfect assistant tone.
- **It has a live nervous system.** FastAPI + SSE exposes mood, thoughts, somatic state, conflicts, memories, and uptime.
- **It is local-first.** Your config, memory, media, and dashboard are owned by the project folder you run.

## Dashboard

`npx . demo` starts a zero-config animated preview. The real WebUI streams live state from the runtime and shows:

- full emotional state,
- recent thoughts and background idle processing,
- memory counters and uptime,
- hormones and interoceptive body state,
- attachment, circadian rhythm, body memory, dreams, curiosity, and conflicts,
- runtime health through local endpoints and Server-Sent Events.

The hosted project page includes a full static WebUI showcase: https://vindepemarte.github.io/alive-ai/

## Architecture

Alive-AI is an event-driven Python runtime.

```text
Telegram or input
  -> NervousSystem event bus
  -> Message handler
  -> Heart, memory, skills, directives, personality
  -> LLM provider or fallback chain
  -> output events
  -> dashboard state stream
```

Core subsystems:

- `heart/`: continuous emotion, circadian rhythm, attachment, scars, somatic state, inconsistency.
- `brain/`: LLM providers, memory, default-mode processing, bid detection, curiosity, dreams.
- `skills/`: self-authorship, memory callbacks, relationship milestones, progression layers, media selection.
- `webui/`: local dashboard with Server-Sent Events.
- `input/telegram/`: Telegram listener and owner commands.

## Docker

Docker is optional. It is useful when you want Redis Stack for vector search:

```bash
docker compose up -d redis
npx . start
```

Or run everything in containers:

```bash
docker compose up --build
```

## Roadmap

Implemented:

- [x] Local-first emotional runtime
- [x] Persistent emotion model with decay and compound state
- [x] Working, episodic, semantic, and emotional memory modules
- [x] Default-mode loop for idle thoughts and proactive impulses
- [x] Attachment, circadian rhythm, body memory, curiosity, dreams, and internal conflicts
- [x] Per-user memory/state isolation
- [x] Telegram input/output runtime
- [x] Local WebUI dashboard with live state streaming
- [x] npm/npx CLI scaffold, setup, doctor, demo, and start commands
- [x] Clean public repo with private personas, media, runtime data, and multi-AI orchestration removed
- [x] GitHub Pages site and full WebUI showcase

Next:

- [ ] One-command local model bootstrap through Ollama profiles
- [ ] Desktop app wrapper with tray controls and local service lifecycle
- [ ] Browser-based onboarding wizard for personality, boundaries, LLM provider, and memory settings
- [ ] Safer dependency detection with guided install commands per OS
- [ ] More input channels beyond Telegram
- [ ] Import/export for memories and personality snapshots
- [ ] Plugin API for new senses, skills, and output modalities
- [ ] Evaluation harness for emotional continuity, memory drift, and unhealthy attachment risk
- [ ] Optional cloud sync that preserves local-first ownership

## Important Boundaries

Alive-AI is a simulation framework. It can make agents feel more continuous, emotionally coherent, and alive, but it is not proof of consciousness.

Do not use it to manipulate emotional dependence. If you are building a companion, character, partner, or friend-like system, make the boundaries explicit and keep the operator in control.

The public repo intentionally excludes private personas, private media, runtime data, and secrets. Put those only in your local project folder.

## License

MIT

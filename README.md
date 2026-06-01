# Alive-AI

![Alive-AI logo](docs/assets/logo.svg)

Give your AI a nervous system: persistent feelings, memory, impulses, and a local dashboard.

Most agents answer a prompt and reset. Alive-AI keeps internal state alive between messages. It can be your friend, boyfriend, girlfriend, study partner, creative partner, or any local companion you configure. The experiment asks a harder question: what changes when an AI does not just respond, but carries emotional residue forward?

Alive-AI does not claim biological consciousness. It is an open-source runtime for simulated affect: mood, attachment, trust, desire, memory, inconsistency, idle thoughts, and proactive impulses.

## Install

```bash
npx alive-ai@latest init my-ai
cd my-ai
npx alive-ai setup
npx alive-ai demo
```

Start the real runtime:

```bash
npx alive-ai start
```

The local dashboard runs at:

```text
http://127.0.0.1:8080
```

## Why This Is Different

- **Emotions persist.** State does not reset after every message. Joy, trust, fear, anticipation, attachment, and vulnerability decay over time instead of disappearing.
- **Memory has weight.** Conversations become episodic memory, semantic memory, and emotional memory.
- **It thinks when idle.** A default-mode loop creates background reflections and proactive impulses.
- **It has a live nervous system.** FastAPI + SSE exposes mood, thoughts, somatic state, conflicts, memories, and uptime.
- **It is local-first.** Your config, memory, media, and dashboard are owned by the project folder you run.

## Commands

```bash
npx alive-ai init my-ai       # scaffold a clean local project
npx alive-ai setup            # create safe local config
npx alive-ai demo             # preview animated dashboard, no keys needed
npx alive-ai doctor           # check Python, uv, ffmpeg, Docker
npx alive-ai start            # install Python deps and run the runtime
```

For repeat starts after dependencies are installed:

```bash
npx alive-ai start --skip-install
```

## Setup

`npx alive-ai setup` creates:

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
- `skills/`: self-authorship, memory callbacks, relationship milestones, content scheduling, media selection.
- `webui/`: local dashboard with Server-Sent Events.
- `input/telegram/`: Telegram listener and owner commands.

## Dashboard

`npx alive-ai demo` starts a zero-config animated dashboard preview. The real dashboard uses the same idea, but streams live state from the runtime:

- emotions and mood,
- recent thoughts,
- memory counters,
- somatic state,
- attachment/inconsistency signals,
- uptime and health.

## Docker

Docker is optional. It is useful when you want Redis Stack for vector search:

```bash
docker compose up -d redis
npx alive-ai start
```

Or run everything in containers:

```bash
docker compose up --build
```

## Important Boundaries

Alive-AI is a simulation framework. It can make agents feel more continuous, emotionally coherent, and alive, but it is not proof of consciousness and should not be used to manipulate emotional dependence.

The public repo intentionally excludes private personas, private media, runtime data, and secrets. Put those only in your local project folder.

## License

MIT

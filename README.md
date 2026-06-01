<div align="center">
  <img src="docs/assets/logo.svg" alt="Alive-AI" width="96" height="96">

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
| `npx . doctor` | Check OS, Node, Python, uv, ffmpeg, Docker, and OpenMind reachability. |
| `npx . doctor --fix` | Ask `y/N` for each missing installable tool and run the platform installer if approved. |
| `npx . chat` | Start the real runtime with split-pane terminal chat and logs. |
| `npx . chat --plain` | Start raw terminal chat without the TUI. |
| `npx . demo` | Run a keyless animated dashboard demo. |
| `npx . start` | Start the runtime using the configured input channel, usually Telegram. |
| `npx . start --skip-install` | Start again without reinstalling Python dependencies. |
| `npx . update` | Refresh runtime files from the latest npm package while preserving config/data/media. |
| `npx . uninstall` | Remove Alive-AI runtime files, config, venv, cache, data, and media from the project. |

`start` and `chat` check npm for a newer Alive-AI version. You can update, skip once, or skip that specific version. Stop terminal chat with `/exit` or `Ctrl+C`.

`doctor --fix` is conservative: it prints the exact install command before running anything and asks separately for each missing tool. On macOS it uses Homebrew, on Windows it uses winget, and on Linux it supports apt, dnf, and pacman where possible.

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

The setup accepts `skip` for optional keys and `local` for Ollama.

Startup config is loaded from multiple places in this order:

```text
.env
config/secrets.env
config/settings.json
```

Shell environment variables win over `.env`/`config/secrets.env`. Runtime settings come from `config/settings.json`. Telegram uses `TELEGRAM_TOKEN` when present, otherwise `telegram_token` from `config/settings.json`.

| Setup item | Options |
| --- | --- |
| LLM | `local`/Ollama, OpenRouter, ZAI, or `skip` for demo/fallback-only mode. |
| Telegram | Bot token and owner ID are optional. Use terminal chat if you do not want Telegram. |
| Voice | `gtts` local/free default, Google TTS, VibeVoice, or `skip`. |
| Images | Fal.ai API key or `skip`. Local media folders still work without image generation. |
| Memory | Built-in local memory, OpenMind cloud, or OpenMind local. |

Minimum useful paths:

```bash
# Terminal-only local run
npx . setup
npx . chat

# Local LLM
ollama pull qwen3:4b
npx . setup
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

Alive-AI has built-in local working, episodic, semantic, and emotional memory. OpenMind is optional and works as a hybrid long-term semantic memory layer.

Modes:

| Mode | Behavior |
| --- | --- |
| Built-in only | Alive-AI uses its local project memory only. |
| OpenMind cloud | Alive-AI captures/searches long-term memories through `https://theopenmind.pro`. |
| OpenMind local | Alive-AI captures/searches a local OpenMind server, normally `http://127.0.0.1:3333`. |

OpenMind does not replace Alive-AI's emotional state. It adds durable semantic recall across tools and machines.

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

Minimum for cloud LLMs or remote Ollama:

| Requirement | Minimum |
| --- | --- |
| Node.js | 18+ |
| Python | 3.11+ |
| RAM | 8 GB |
| Disk | 2 GB free |
| LLM | OpenRouter, ZAI, remote Ollama, or local Ollama already installed |

Comfortable local setup:

| Requirement | Recommended |
| --- | --- |
| Node.js | 20+ |
| RAM | 16 GB for 3B-4B local models |
| RAM for bigger models | 32 GB for 7B+ local models, Redis, voice, and long sessions |
| Disk | 10 GB+, more if you keep local models/media |
| Optional tools | `uv`, `ffmpeg`, Docker, Ollama |

`npx . start` creates `.alive-ai/venv` and installs Python dependencies. System-level packages such as Node, Python, Ollama, Docker, and ffmpeg must already exist on the machine.

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
- attachment, circadian rhythm, body memory, dreams, curiosity, and conflicts,
- runtime health through local endpoints.

GitHub Pages cannot run the Python/FastAPI backend, so the public page includes a static export of the actual WebUI with mocked state:

```text
https://vindepemarte.github.io/alive-ai/
```

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
- [x] Terminal chat runtime with owner-style slash commands
- [x] Split-pane terminal chat with logs
- [x] Local WebUI dashboard with live state streaming
- [x] Optional hybrid OpenMind cloud/local semantic memory
- [x] npm/npx CLI scaffold, setup, doctor, demo, chat, and start commands
- [x] Update prompt and project uninstall command
- [x] `doctor --fix` guided system dependency installer
- [x] Clean public repo with private personas, media, runtime data, and multi-AI orchestration removed
- [x] GitHub Pages site and full static WebUI export

Next:

- [ ] One-command local model bootstrap through Ollama profiles
- [ ] Desktop app wrapper with tray controls and local service lifecycle
- [ ] Browser-based onboarding wizard for personality, boundaries, LLM provider, and memory settings
- [ ] Better guided system install commands per OS
- [ ] More input channels beyond terminal and Telegram
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

#!/usr/bin/env node
"use strict";

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawn, spawnSync } = require("child_process");

const PACKAGE_ROOT = path.resolve(__dirname, "..");
const DEFAULT_PORT = 8080;

const COPY_ENTRIES = [
  "alive_ai",
  "brain",
  "cli",
  "config",
  "core",
  "demo",
  "docs",
  "heart",
  "input",
  "mypics",
  "myvids",
  "output",
  "skills",
  "webui",
  "Dockerfile",
  "docker-compose.yml",
  "LICENSE",
  "main.py",
  "manifest.md",
  "package.json",
  "pyproject.toml",
  "README.md",
  "requirements.txt"
];

function usage() {
  console.log(`Alive-AI

Usage:
  alive-ai init <directory>       Create a new Alive-AI project
  alive-ai setup [--yes]          Create local config from templates
  alive-ai demo [--port 8080]     Run the animated dashboard demo
  alive-ai start [--skip-install] Install Python deps if needed and start runtime
  alive-ai chat [--skip-install]  Start runtime with terminal chat input
  alive-ai doctor                 Check local prerequisites

Quick start:
  npx alive-ai@latest init my-ai
  cd my-ai
  npx . setup
  npx . doctor
  npx . chat
  npx . demo
  npx . start`);
}

function argValue(args, name, fallback) {
  const index = args.indexOf(name);
  if (index === -1 || index === args.length - 1) return fallback;
  return args[index + 1];
}

function hasFlag(args, name) {
  return args.includes(name);
}

function ensureDir(dir) {
  fs.mkdirSync(dir, { recursive: true });
}

function copyRecursive(src, dest) {
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    ensureDir(dest);
    for (const entry of fs.readdirSync(src)) {
      if (entry === ".git" || entry === "node_modules" || entry === "__pycache__") continue;
      if (entry.endsWith(".pyc")) continue;
      copyRecursive(path.join(src, entry), path.join(dest, entry));
    }
    return;
  }
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

function initProject(args) {
  const targetArg = args.find((arg) => !arg.startsWith("-"));
  if (!targetArg) {
    console.error("Missing target directory.");
    usage();
    process.exit(1);
  }

  const target = path.resolve(process.cwd(), targetArg);
  if (fs.existsSync(target) && fs.readdirSync(target).length > 0) {
    console.error(`Refusing to initialize into a non-empty directory: ${target}`);
    process.exit(1);
  }

  ensureDir(target);
  for (const entry of COPY_ENTRIES) {
    const src = path.join(PACKAGE_ROOT, entry);
    if (!fs.existsSync(src)) continue;
    copyRecursive(src, path.join(target, entry));
  }

  ensureDir(path.join(target, "data"));
  ensureDir(path.join(target, "mypics"));
  ensureDir(path.join(target, "myvids"));

  console.log(`Created Alive-AI project at ${target}`);
  console.log("");
  console.log("Next:");
  console.log(`  cd ${target}`);
  console.log("  npx . setup");
  console.log("  npx . doctor");
  console.log("  npx . chat");
  console.log("  npx . demo");
}

function readJson(file) {
  return JSON.parse(fs.readFileSync(file, "utf8"));
}

function writeJson(file, data) {
  ensureDir(path.dirname(file));
  fs.writeFileSync(file, `${JSON.stringify(data, null, 2)}\n`);
}

function ask(question, fallback, assumeYes) {
  if (assumeYes || !process.stdin.isTTY) return Promise.resolve(fallback);
  const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
  return new Promise((resolve) => {
    const suffix = fallback ? ` (${fallback})` : "";
    rl.question(`${question}${suffix}: `, (answer) => {
      rl.close();
      resolve(answer.trim() || fallback);
    });
  });
}

function normalizeChoice(value, fallback = "") {
  return String(value || fallback).trim().toLowerCase();
}

function isSkipped(value) {
  return normalizeChoice(value) === "skip";
}

function emptyIfSkipped(value) {
  return isSkipped(value) ? "" : value;
}

function readProjectSettings() {
  const settingsPath = path.join(process.cwd(), "config", "settings.json");
  if (!fs.existsSync(settingsPath)) return {};
  try {
    return readJson(settingsPath);
  } catch {
    return {};
  }
}

async function setupProject(args) {
  const dryRun = hasFlag(args, "--dry-run");
  const assumeYes = hasFlag(args, "--yes") || hasFlag(args, "-y") || dryRun;
  const configDir = path.join(process.cwd(), "config");
  const settingsExample = path.join(configDir, "settings.example.json");
  const selfExample = path.join(configDir, "self.example.json");
  const directivesExample = path.join(configDir, "directives.example.json");
  const instructionsExample = path.join(configDir, "instructions.example.md");

  for (const file of [settingsExample, selfExample, directivesExample, instructionsExample]) {
    if (!fs.existsSync(file)) {
      console.error(`Missing template: ${path.relative(process.cwd(), file)}`);
      console.error("Run this command from an Alive-AI project directory.");
      process.exit(1);
    }
  }

  if (dryRun) {
    console.log("Setup dry run:");
    console.log("  would write config/settings.json");
    console.log("  would write config/self.json");
    console.log("  would write config/directives.json");
    console.log("  would write config/instructions.md");
    console.log("  would create data/, mypics/, and myvids/");
    return;
  }

  const displayNameAnswer = await ask("Agent display name", "Nova", assumeYes);
  const displayName = emptyIfSkipped(displayNameAnswer) || "Nova";
  const ownerId = emptyIfSkipped(await ask("Telegram owner ID (optional, use skip to leave blank)", "", assumeYes));
  const telegramToken = emptyIfSkipped(await ask("Telegram bot token (optional, use skip to leave blank)", "", assumeYes));
  const providerChoice = normalizeChoice(
    await ask("LLM provider: local, openrouter, zai, or skip", "local", assumeYes),
    "local"
  );
  const provider = providerChoice === "local" ? "ollama" : providerChoice;
  const openRouterKey = provider === "openrouter"
    ? emptyIfSkipped(await ask("OpenRouter API key (or skip)", "", assumeYes))
    : "";
  const zaiKey = provider === "zai"
    ? emptyIfSkipped(await ask("ZAI API key (or skip)", "", assumeYes))
    : "";
  const ttsChoice = normalizeChoice(
    await ask("Voice provider: gtts, google, vibe, or skip", "gtts", assumeYes),
    "gtts"
  );
  const googleTtsKey = ttsChoice === "google"
    ? emptyIfSkipped(await ask("Google TTS API key (optional, use skip for ADC)", "", assumeYes))
    : "";
  const vibeTtsUrl = ttsChoice === "vibe"
    ? emptyIfSkipped(await ask("VibeVoice URL (or skip)", "http://127.0.0.1:8088", assumeYes))
    : "";
  const falKey = emptyIfSkipped(await ask("Fal.ai image API key (optional, use skip to disable)", "", assumeYes));
  const memoryChoice = normalizeChoice(
    await ask("Memory mode: built-in, openmind-cloud, or openmind-local", "built-in", assumeYes),
    "built-in"
  );
  const openmindEnabled = memoryChoice.startsWith("openmind");
  const openmindBaseUrl = openmindEnabled
    ? memoryChoice === "openmind-local"
      ? emptyIfSkipped(await ask("OpenMind local URL", "http://127.0.0.1:3333", assumeYes))
      : emptyIfSkipped(await ask("OpenMind cloud URL", "https://theopenmind.pro", assumeYes))
    : "";
  const openmindKey = openmindEnabled
    ? emptyIfSkipped(await ask("OpenMind API key (om_..., optional for unauthenticated local dev)", "", assumeYes))
    : "";

  const settings = readJson(settingsExample);
  settings.AGENT_NAME = displayName;
  settings.INPUT_CHANNEL = "telegram";
  settings.telegram_token = telegramToken;
  settings.TELEGRAM_OWNER_ID = ownerId;
  settings.LLM_PROVIDER = provider === "skip" ? "ollama" : provider;
  settings.OPENROUTER_API_KEY = openRouterKey;
  settings.ZAI_API_KEY = zaiKey;
  settings.LLM_FALLBACK.ENABLED = provider !== "skip";
  settings.LLM_FALLBACK.ORDER = provider === "skip"
    ? ["ollama"]
    : provider === "ollama"
      ? ["ollama"]
      : [provider, "ollama"];
  settings.TTS_PROVIDER = ttsChoice === "skip" ? "none" : ttsChoice;
  settings.GOOGLE_TTS_API_KEY = googleTtsKey;
  settings.vibe_tts_url = vibeTtsUrl;
  settings.FAL_API_KEY = falKey;
  settings.OPENMIND_ENABLED = openmindEnabled;
  settings.OPENMIND_MODE = openmindEnabled ? "hybrid" : "built-in";
  settings.OPENMIND_BASE_URL = openmindBaseUrl || "https://theopenmind.pro";
  settings.OPENMIND_API_KEY = openmindKey;

  const self = readJson(selfExample);
  self.who_i_am.name = displayName;
  self.who_i_am.origin = "I am an Alive-AI local agent configured by my operator.";

  const directives = readJson(directivesExample);
  directives.OPERATOR.owner_id = ownerId;

  writeJson(path.join(configDir, "settings.json"), settings);
  writeJson(path.join(configDir, "self.json"), self);
  writeJson(path.join(configDir, "directives.json"), directives);
  fs.copyFileSync(instructionsExample, path.join(configDir, "instructions.md"));
  ensureDir(path.join(process.cwd(), "data"));
  ensureDir(path.join(process.cwd(), "mypics"));
  ensureDir(path.join(process.cwd(), "myvids"));

  console.log("Alive-AI config created.");
  console.log("Run `npx . chat` for terminal chat, `npx . demo` for the dashboard preview, or `npx . start` for Telegram/runtime mode.");
}

function findCommand(candidates) {
  for (const command of candidates) {
    const result = spawnSync(command, ["--version"], { stdio: "ignore" });
    if (result.status === 0) return command;
  }
  return null;
}

async function doctor() {
  const python = findCommand(["python3.11", "python3", "python"]);
  const uv = findCommand(["uv"]);
  const ffmpeg = findCommand(["ffmpeg"]);
  const docker = findCommand(["docker"]);
  const node = process.version;
  const settings = readProjectSettings();

  console.log("Alive-AI doctor");
  console.log(`  system: ${os.platform()} ${os.arch()}`);
  console.log(`  node:   ${node}`);
  console.log(`  python: ${python || "missing"}`);
  console.log(`  uv:     ${uv || "missing, will use venv + pip"}`);
  console.log(`  ffmpeg: ${ffmpeg || "missing, voice conversion may be limited"}`);
  console.log(`  docker: ${docker || "missing, Redis can still be external"}`);
  console.log(`  input:  ${settings.INPUT_CHANNEL || "telegram"}`);

  if (!python) {
    console.log("");
    console.log("Install Python 3.11+ first:");
    if (process.platform === "darwin") console.log("  brew install python@3.11");
    else if (process.platform === "win32") console.log("  winget install Python.Python.3.11");
    else console.log("  sudo apt install python3.11 python3.11-venv");
  }

  if (settings.OPENMIND_ENABLED) {
    const baseUrl = String(settings.OPENMIND_BASE_URL || "https://theopenmind.pro").replace(/\/$/, "");
    const headers = {};
    if (settings.OPENMIND_API_KEY) headers.authorization = `Bearer ${settings.OPENMIND_API_KEY}`;
    try {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), 4000);
      const response = await fetch(`${baseUrl}/health`, { headers, signal: controller.signal });
      clearTimeout(timer);
      console.log(`  OpenMind: ${response.ok ? "reachable" : `HTTP ${response.status}`} (${baseUrl})`);
    } catch (error) {
      console.log(`  OpenMind: unreachable (${baseUrl})`);
    }
  } else {
    console.log("  OpenMind: disabled");
  }

  if (!python) process.exitCode = 1;
}

function ensurePythonEnv(skipInstall) {
  const python = findCommand(["python3.11", "python3", "python"]);
  if (!python) {
    console.error("Python 3.11+ is required.");
    process.exit(1);
  }

  const venvDir = path.join(process.cwd(), ".alive-ai", "venv");
  const pythonBin = process.platform === "win32"
    ? path.join(venvDir, "Scripts", "python.exe")
    : path.join(venvDir, "bin", "python");

  if (skipInstall && fs.existsSync(pythonBin)) return pythonBin;

  const uv = findCommand(["uv"]);
  ensureDir(path.dirname(venvDir));

  if (!fs.existsSync(pythonBin)) {
    console.log("Creating Python environment...");
    const create = uv
      ? spawnSync("uv", ["venv", venvDir], { stdio: "inherit" })
      : spawnSync(python, ["-m", "venv", venvDir], { stdio: "inherit" });
    if (create.status !== 0) process.exit(create.status || 1);
  }

  if (!skipInstall) {
    console.log("Installing Python dependencies...");
    const install = uv
      ? spawnSync("uv", ["pip", "install", "--python", pythonBin, "-r", "requirements.txt"], { stdio: "inherit" })
      : spawnSync(pythonBin, ["-m", "pip", "install", "-r", "requirements.txt"], { stdio: "inherit" });
    if (install.status !== 0) process.exit(install.status || 1);
  }

  return pythonBin;
}

function startRuntime(args) {
  if (!fs.existsSync(path.join(process.cwd(), "config", "settings.json"))) {
    console.log("Missing config/settings.json. Starting onboarding first.");
    const setupArgs = process.stdin.isTTY ? [] : ["--yes"];
    setupProject(setupArgs).then(() => startRuntime(args));
    return;
  }
  const pythonBin = ensurePythonEnv(hasFlag(args, "--skip-install"));
  const extraArgs = [];
  const inputChannel = argValue(args, "--input", null);
  if (inputChannel) extraArgs.push("--input", inputChannel);
  const child = spawn(pythonBin, ["main.py", ...extraArgs], { stdio: "inherit", cwd: process.cwd() });
  child.on("exit", (code) => process.exit(code || 0));
}

function startTerminalChat(args) {
  return startRuntime(["--input", "terminal", ...args]);
}

function demoHtml() {
  return fs.readFileSync(path.join(PACKAGE_ROOT, "demo", "index.html"), "utf8");
}

function fakeState() {
  const t = Date.now() / 1000;
  const wave = (offset) => Math.round((0.5 + Math.sin(t / 3 + offset) * 0.35) * 100);
  return {
    mood: ["curious", "warm", "reflective", "playful"][Math.floor(t / 4) % 4],
    emotions: {
      joy: wave(0),
      trust: wave(1),
      anticipation: wave(2),
      vulnerability: wave(3),
      calm: wave(4)
    },
    thought: [
      "I keep a little emotional residue from every interaction.",
      "Memory is not a transcript here. It is context with weight.",
      "The dashboard is a window into the internal loop.",
      "I can reach out because an impulse formed, not because a cron fired."
    ][Math.floor(t / 5) % 4],
    counters: {
      memories: 128 + Math.floor(t % 17),
      impulses: 42 + Math.floor(t % 9),
      uptime: "demo"
    }
  };
}

function startDemo(args) {
  const requestedPort = Number(argValue(args, "--port", DEFAULT_PORT));
  const server = http.createServer((req, res) => {
    if (req.url === "/health") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify({ ok: true, service: "alive-ai-demo" }));
      return;
    }
    if (req.url === "/state" || req.url === "/api/soul" || req.url === "/api/aliveness") {
      res.writeHead(200, { "content-type": "application/json" });
      res.end(JSON.stringify(fakeState()));
      return;
    }
    if (req.url === "/assets/logo.svg") {
      res.writeHead(200, { "content-type": "image/svg+xml" });
      res.end(fs.readFileSync(path.join(PACKAGE_ROOT, "docs", "assets", "logo.svg")));
      return;
    }
    res.writeHead(200, { "content-type": "text/html; charset=utf-8" });
    res.end(demoHtml());
  });

  let currentPort = requestedPort;
  let attemptsLeft = 20;

  server.on("error", (error) => {
      if (error.code === "EADDRINUSE" && attemptsLeft > 0) {
        attemptsLeft -= 1;
        currentPort += 1;
        server.listen(currentPort, "127.0.0.1");
        return;
      }
      console.error(error.message);
      process.exit(1);
  });

  server.on("listening", () => {
      const actualPort = server.address().port;
      console.log(`Alive-AI demo dashboard: http://127.0.0.1:${actualPort}`);
      if (actualPort !== requestedPort) {
        console.log(`Port ${requestedPort} was busy, using ${actualPort}.`);
      }
  });

  server.listen(currentPort, "127.0.0.1");
}

async function main() {
  const [command, ...args] = process.argv.slice(2);
  if (!command || command === "--help" || command === "-h") return usage();
  if (command === "init") return initProject(args);
  if (command === "setup") return setupProject(args);
  if (command === "demo") return startDemo(args);
  if (command === "start") return startRuntime(args);
  if (command === "chat") return startTerminalChat(args);
  if (command === "doctor") return doctor();
  console.error(`Unknown command: ${command}`);
  usage();
  process.exit(1);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});

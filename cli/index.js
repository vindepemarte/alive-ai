#!/usr/bin/env node
"use strict";

const fs = require("fs");
const http = require("http");
const os = require("os");
const path = require("path");
const readline = require("readline");
const { spawn, spawnSync } = require("child_process");
const { runRuntimeTui } = require("./tui");

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
  alive-ai update [--yes]         Update this project from the latest package
  alive-ai start [--skip-install] Install Python deps if needed and start runtime
  alive-ai chat [--skip-install]  Start split-pane terminal chat and logs
  alive-ai chat --plain           Start raw terminal chat without the TUI
  alive-ai doctor [--fix]         Check local prerequisites and optionally install missing tools
  alive-ai uninstall              Remove Alive-AI runtime files from this project

Quick start:
  npx alive-ai@latest init my-ai
  cd my-ai
  npx . setup
  npx . doctor
  npx . chat
  npx . demo
  npx . start
  npx . uninstall`);
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

function readSimpleEnv(file) {
  if (!fs.existsSync(file)) return {};
  const data = {};
  for (const rawLine of fs.readFileSync(file, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const [key, ...rest] = line.split("=");
    data[key.trim()] = rest.join("=").trim();
  }
  return data;
}

function packageVersion() {
  try {
    return readJson(path.join(PACKAGE_ROOT, "package.json")).version || "0.0.0";
  } catch {
    return "0.0.0";
  }
}

function compareVersions(a, b) {
  const left = String(a || "0").split(".").map((part) => Number.parseInt(part, 10) || 0);
  const right = String(b || "0").split(".").map((part) => Number.parseInt(part, 10) || 0);
  for (let i = 0; i < Math.max(left.length, right.length); i += 1) {
    const delta = (left[i] || 0) - (right[i] || 0);
    if (delta) return delta;
  }
  return 0;
}

function npmLatestVersion() {
  const result = spawnSync("npm", ["view", "alive-ai", "version", "--silent"], {
    encoding: "utf8",
    timeout: 5000,
  });
  if (result.status !== 0) return null;
  return result.stdout.trim() || null;
}

function updatePrefsPath() {
  return path.join(os.homedir(), ".alive-ai", "update-prefs.json");
}

function readUpdatePrefs() {
  try {
    return readJson(updatePrefsPath());
  } catch {
    return {};
  }
}

function writeUpdatePrefs(data) {
  writeJson(updatePrefsPath(), data);
}

async function maybeCheckForUpdate(args) {
  if (hasFlag(args, "--no-update-check") || process.env.ALIVE_AI_SKIP_UPDATE_CHECK === "1") return;
  if (!process.stdin.isTTY) return;
  const current = packageVersion();
  const latest = npmLatestVersion();
  if (!latest || compareVersions(latest, current) <= 0) return;

  const prefs = readUpdatePrefs();
  if (prefs.skipVersion === latest) return;

  console.log("");
  console.log(`Alive-AI ${latest} is available. Current project runtime is ${current}.`);
  const answer = normalizeChoice(await ask("Update before starting? yes, skip, or never", "yes", false), "yes");
  if (answer === "never") {
    prefs.skipVersion = latest;
    writeUpdatePrefs(prefs);
    console.log(`Skipping Alive-AI ${latest}. Run \`npx . update\` whenever you want it.`);
    return;
  }
  if (answer === "skip" || answer === "no" || answer === "n") return;

  const update = spawnSync("npx", ["-y", "alive-ai@latest", "update", "--yes"], {
    stdio: "inherit",
    cwd: process.cwd(),
  });
  if (update.status !== 0) {
    console.log("Update failed, continuing with the current runtime.");
    return;
  }
  console.log("Update complete. Starting with the refreshed project files.");
}

const UPDATE_PRESERVE = new Set([
  "config/settings.json",
  "config/self.json",
  "config/directives.json",
  "config/instructions.md",
  ".env",
  "config/secrets.env",
  "data",
  "mypics",
  "myvids",
  ".alive-ai",
  ".cache",
]);

function shouldPreserve(relPath) {
  const normalized = relPath.split(path.sep).join("/");
  if (UPDATE_PRESERVE.has(normalized)) return true;
  return [...UPDATE_PRESERVE].some((prefix) => normalized.startsWith(`${prefix}/`));
}

function copyUpdateRecursive(src, dest, baseDest = dest) {
  const relPath = path.relative(baseDest, dest);
  if (relPath && shouldPreserve(relPath)) return;
  const stat = fs.statSync(src);
  if (stat.isDirectory()) {
    ensureDir(dest);
    for (const entry of fs.readdirSync(src)) {
      if (entry === ".git" || entry === "node_modules" || entry === "__pycache__") continue;
      copyUpdateRecursive(path.join(src, entry), path.join(dest, entry), baseDest);
    }
    return;
  }
  if (src.endsWith(".pyc")) return;
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

async function updateProject(args) {
  const assumeYes = hasFlag(args, "--yes") || hasFlag(args, "-y") || !process.stdin.isTTY;
  if (!fs.existsSync(path.join(process.cwd(), "config")) || !fs.existsSync(path.join(process.cwd(), "main.py"))) {
    console.error("Run `alive-ai update` from an Alive-AI project directory.");
    process.exit(1);
  }
  if (!assumeYes) {
    const answer = normalizeChoice(await ask("Update runtime files while preserving config/data? yes or no", "yes", false), "yes");
    if (!["yes", "y"].includes(answer)) return;
  }
  for (const entry of COPY_ENTRIES) {
    const src = path.join(PACKAGE_ROOT, entry);
    if (!fs.existsSync(src)) continue;
    copyUpdateRecursive(src, path.join(process.cwd(), entry), process.cwd());
  }
  console.log(`Alive-AI project updated to ${packageVersion()}.`);
  console.log("Preserved config/, data/, mypics/, myvids/, .alive-ai/, and .cache/.");
}

async function uninstallProject(args) {
  const assumeYes = hasFlag(args, "--yes") || hasFlag(args, "-y");
  const deleteProject = hasFlag(args, "--delete-project");
  const target = process.cwd();
  if (!fs.existsSync(path.join(target, "main.py")) || !fs.existsSync(path.join(target, "package.json"))) {
    console.error("Run `alive-ai uninstall` from an Alive-AI project directory.");
    process.exit(1);
  }
  if (!assumeYes) {
    const answer = normalizeChoice(await ask("Remove Alive-AI runtime files, config, venv, cache, data, and media from this project? yes or no", "no", false), "no");
    if (!["yes", "y"].includes(answer)) {
      console.log("Uninstall cancelled.");
      return;
    }
  }

  const entries = new Set([
    ...COPY_ENTRIES,
    "config",
    "data",
    "mypics",
    "myvids",
    ".alive-ai",
    ".cache",
    ".env",
  ]);
  for (const entry of entries) {
    const dest = path.join(target, entry);
    if (!fs.existsSync(dest)) continue;
    fs.rmSync(dest, { recursive: true, force: true });
    console.log(`removed ${entry}`);
  }

  try {
    fs.rmSync(updatePrefsPath(), { force: true });
  } catch {}

  if (deleteProject) {
    const parent = path.dirname(target);
    process.chdir(parent);
    fs.rmSync(target, { recursive: true, force: true });
    console.log(`Removed project directory: ${target}`);
    return;
  }

  console.log("Alive-AI local files removed. The project folder itself was kept.");
  console.log("If you installed globally, remove the global CLI with: npm uninstall -g alive-ai");
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

function majorVersion(version) {
  return Number.parseInt(String(version || "0").split(".")[0], 10) || 0;
}

function pythonVersion(command) {
  const result = spawnSync(command, ["-c", "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')"], {
    encoding: "utf8",
  });
  if (result.status !== 0) return "";
  return result.stdout.trim();
}

function hasCommand(command) {
  return spawnSync(command, ["--version"], { stdio: "ignore" }).status === 0;
}

function commandLine(command) {
  if (!command) return "";
  return command.map((part) => /[\s"']/.test(part) ? JSON.stringify(part) : part).join(" ");
}

function runInstallCommand(command) {
  const [bin, ...args] = command;
  return spawnSync(bin, args, { stdio: "inherit", shell: false });
}

function packageManager() {
  if (process.platform === "darwin" && hasCommand("brew")) return "brew";
  if (process.platform === "win32" && hasCommand("winget")) return "winget";
  if (process.platform === "linux") {
    if (hasCommand("apt-get")) return "apt";
    if (hasCommand("dnf")) return "dnf";
    if (hasCommand("pacman")) return "pacman";
  }
  return null;
}

function installPlan(tool) {
  const manager = packageManager();
  if (process.platform === "darwin") {
    if (manager !== "brew") return null;
    return {
      node: ["brew", "install", "node"],
      python: ["brew", "install", "python@3.12"],
      uv: ["brew", "install", "uv"],
      ffmpeg: ["brew", "install", "ffmpeg"],
      docker: ["brew", "install", "--cask", "docker"],
      ollama: ["brew", "install", "ollama"],
    }[tool] || null;
  }

  if (process.platform === "win32") {
    if (manager !== "winget") return null;
    return {
      node: ["winget", "install", "-e", "--id", "OpenJS.NodeJS.LTS"],
      python: ["winget", "install", "-e", "--id", "Python.Python.3.12"],
      uv: ["winget", "install", "-e", "--id", "astral-sh.uv"],
      ffmpeg: ["winget", "install", "-e", "--id", "Gyan.FFmpeg"],
      docker: ["winget", "install", "-e", "--id", "Docker.DockerDesktop"],
      ollama: ["winget", "install", "-e", "--id", "Ollama.Ollama"],
    }[tool] || null;
  }

  if (process.platform === "linux") {
    const plans = {
      apt: {
        node: ["sudo", "apt-get", "install", "-y", "nodejs", "npm"],
        python: ["sudo", "apt-get", "install", "-y", "python3", "python3-venv"],
        uv: ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
        ffmpeg: ["sudo", "apt-get", "install", "-y", "ffmpeg"],
        docker: ["sudo", "apt-get", "install", "-y", "docker.io"],
        ollama: ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
      },
      dnf: {
        node: ["sudo", "dnf", "install", "-y", "nodejs", "npm"],
        python: ["sudo", "dnf", "install", "-y", "python3"],
        uv: ["sh", "-c", "curl -LsSf https://astral.sh/uv/install.sh | sh"],
        ffmpeg: ["sudo", "dnf", "install", "-y", "ffmpeg"],
        docker: ["sudo", "dnf", "install", "-y", "docker"],
        ollama: ["sh", "-c", "curl -fsSL https://ollama.com/install.sh | sh"],
      },
      pacman: {
        node: ["sudo", "pacman", "-S", "--needed", "nodejs", "npm"],
        python: ["sudo", "pacman", "-S", "--needed", "python"],
        uv: ["sudo", "pacman", "-S", "--needed", "uv"],
        ffmpeg: ["sudo", "pacman", "-S", "--needed", "ffmpeg"],
        docker: ["sudo", "pacman", "-S", "--needed", "docker"],
        ollama: ["sudo", "pacman", "-S", "--needed", "ollama"],
      },
    };
    return plans[manager]?.[tool] || null;
  }

  return null;
}

function manualInstallHint(tool) {
  if (process.platform === "darwin" && !hasCommand("brew")) {
    return "Install Homebrew from https://brew.sh, then rerun `npx . doctor --fix`.";
  }
  if (process.platform === "win32" && !hasCommand("winget")) {
    return "Install Windows App Installer/winget, then rerun `npx . doctor --fix`.";
  }
  if (process.platform === "linux" && !packageManager()) {
    return `No supported Linux package manager detected for ${tool}. Install it manually with your distro package manager.`;
  }
  return `No automatic installer is configured for ${tool} on this system.`;
}

async function maybeInstallTool(item, assumeYes = false) {
  const command = installPlan(item.id);
  if (!command) {
    console.log(`  ${item.name}: ${manualInstallHint(item.id)}`);
    return false;
  }

  console.log("");
  console.log(`${item.name} is missing.`);
  console.log(`Command: ${commandLine(command)}`);
  const answer = assumeYes
    ? "y"
    : normalizeChoice(await ask(`Install ${item.name}? y/N`, "n", false), "n");
  if (!["y", "yes"].includes(answer)) {
    console.log(`Skipped ${item.name}.`);
    return false;
  }

  const result = runInstallCommand(command);
  if (result.status === 0) {
    console.log(`${item.name} install command completed.`);
    return true;
  }
  console.log(`${item.name} install command failed with exit code ${result.status || 1}.`);
  return false;
}

function findPython() {
  const preferred = ["python3.12", "python3.11", "python3.13", "python3", "python"];
  for (const command of preferred) {
    const result = spawnSync(command, ["--version"], { stdio: "ignore" });
    if (result.status !== 0) continue;
    const version = pythonVersion(command);
    const [major, minor] = version.split(".").map((part) => Number.parseInt(part, 10));
    if (major === 3 && minor >= 11) return { command, version };
  }
  return null;
}

function wantsOllama(settings) {
  const provider = String(settings.LLM_PROVIDER || "").toLowerCase();
  const order = Array.isArray(settings.LLM_FALLBACK?.ORDER)
    ? settings.LLM_FALLBACK.ORDER.map((item) => String(item).toLowerCase())
    : [];
  return provider === "ollama" || order.includes("ollama");
}

async function doctor(args = []) {
  const shouldFix = hasFlag(args, "--fix");
  const assumeYes = hasFlag(args, "--yes") || hasFlag(args, "-y");
  const python = findPython();
  const uv = findCommand(["uv"]);
  const ffmpeg = findCommand(["ffmpeg"]);
  const docker = findCommand(["docker"]);
  const ollama = findCommand(["ollama"]);
  const node = process.version;
  const nodeMajor = majorVersion(process.versions.node);
  const settings = readProjectSettings();
  const venvPython = process.platform === "win32"
    ? path.join(process.cwd(), ".alive-ai", "venv", "Scripts", "python.exe")
    : path.join(process.cwd(), ".alive-ai", "venv", "bin", "python");

  console.log("Alive-AI doctor");
  console.log(`  system: ${os.platform()} ${os.arch()}`);
  console.log(`  node:   ${nodeMajor >= 18 ? node : `${node} (Node 18+ required)`}`);
  console.log(`  python: ${python ? `${python.command} ${python.version}` : "missing"}`);
  if (fs.existsSync(venvPython)) {
    console.log(`  venv:   ${pythonVersion(venvPython) || "unknown"} (${path.relative(process.cwd(), venvPython)})`);
  }
  console.log(`  uv:     ${uv || "missing, will use venv + pip"}`);
  console.log(`  ffmpeg: ${ffmpeg || "missing, voice conversion may be limited"}`);
  console.log(`  docker: ${docker || "missing, Redis can still be external"}`);
  if (wantsOllama(settings)) {
    console.log(`  ollama: ${ollama || "missing, local LLM unavailable until installed"}`);
  }
  console.log(`  input:  ${settings.INPUT_CHANNEL || "telegram"}`);

  const missing = [];
  if (nodeMajor < 18) missing.push({ id: "node", name: "Node.js 18+" });
  if (!python) missing.push({ id: "python", name: "Python 3.11+" });
  if (!uv) missing.push({ id: "uv", name: "uv" });
  if (!ffmpeg) missing.push({ id: "ffmpeg", name: "ffmpeg" });
  if (!docker) missing.push({ id: "docker", name: "Docker" });
  if (wantsOllama(settings) && !ollama) missing.push({ id: "ollama", name: "Ollama" });

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

  if (shouldFix) {
    if (!missing.length) {
      console.log("");
      console.log("Nothing missing. No fixes needed.");
    } else {
      console.log("");
      console.log("Doctor fix mode: each installer is optional and will ask before running.");
      for (const item of missing) {
        await maybeInstallTool(item, assumeYes);
      }
      console.log("");
      console.log("Run `npx . doctor` again to verify the final state.");
    }
  } else if (missing.length) {
    console.log("");
    console.log("Run `npx . doctor --fix` to install missing tools one by one.");
  }

  if (!python || nodeMajor < 18) process.exitCode = 1;
}

function ensurePythonEnv(skipInstall) {
  const python = findPython();
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
      ? spawnSync("uv", ["venv", "--python", python.command, venvDir], { stdio: "inherit" })
      : spawnSync(python.command, ["-m", "venv", venvDir], { stdio: "inherit" });
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

async function startRuntime(args, options = {}) {
  if (!fs.existsSync(path.join(process.cwd(), "config", "settings.json"))) {
    console.log("Missing config/settings.json. Starting onboarding first.");
    const setupArgs = process.stdin.isTTY ? [] : ["--yes"];
    await setupProject(setupArgs);
  }
  await maybeCheckForUpdate(args);
  const settings = readProjectSettings();
  const secrets = readSimpleEnv(path.join(process.cwd(), "config", "secrets.env"));
  const requestedInputChannel = argValue(args, "--input", null);
  const effectiveInputChannel = (requestedInputChannel || settings.INPUT_CHANNEL || "telegram").toLowerCase();
  const telegramToken = process.env.TELEGRAM_TOKEN || secrets.TELEGRAM_TOKEN || settings.telegram_token;
  if (effectiveInputChannel === "telegram" && !telegramToken) {
    console.error("Telegram is selected, but no Telegram bot token is configured.");
    console.error("Run `npx . setup` to add a token, or use `npx . chat` for terminal mode.");
    process.exit(1);
  }

  const pythonBin = ensurePythonEnv(hasFlag(args, "--skip-install"));
  const extraArgs = [];
  if (requestedInputChannel) extraArgs.push("--input", requestedInputChannel);
  const dataPath = path.join(process.cwd(), "data");
  ensureDir(dataPath);
  const env = {
    ...process.env,
    ALIVE_AI_ROOT: process.cwd(),
    ALIVE_AI_DATA_PATH: dataPath,
    DATA_PATH: dataPath,
    HF_HOME: path.join(process.cwd(), ".cache", "huggingface"),
    SENTENCE_TRANSFORMERS_HOME: path.join(process.cwd(), ".cache", "sentence-transformers"),
    TRANSFORMERS_CACHE: path.join(process.cwd(), ".cache", "huggingface"),
    TOKENIZERS_PARALLELISM: process.env.TOKENIZERS_PARALLELISM || "false",
  };
  if (options.tui) env.ALIVE_AI_TUI = "1";

  const child = spawn(pythonBin, ["main.py", ...extraArgs], {
    stdio: options.tui ? ["pipe", "pipe", "pipe"] : "inherit",
    cwd: process.cwd(),
    env,
  });

  if (options.tui) {
    const code = await runRuntimeTui(child, {
      dashboard: `http://127.0.0.1:${readProjectSettings().WEBUI_PORT || DEFAULT_PORT}`,
    });
    process.exitCode = code;
    return;
  }

  await new Promise((resolve) => {
    child.on("exit", (code) => {
      process.exitCode = code || 0;
      resolve();
    });
  });
}

function startTerminalChat(args) {
  const plain = hasFlag(args, "--plain");
  const filteredArgs = args.filter((arg) => arg !== "--plain");
  return startRuntime(["--input", "terminal", ...filteredArgs], { tui: !plain });
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
  if (command === "update") return updateProject(args);
  if (command === "demo") return startDemo(args);
  if (command === "start") return startRuntime(args);
  if (command === "chat") return startTerminalChat(args);
  if (command === "doctor") return doctor(args);
  if (command === "uninstall") return uninstallProject(args);
  console.error(`Unknown command: ${command}`);
  usage();
  process.exit(1);
}

main().catch((error) => {
  console.error(error.stack || error.message || String(error));
  process.exit(1);
});

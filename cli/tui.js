"use strict";

const readline = require("readline");

const EVENT_PREFIX = "__ALIVE_AI_TUI__";

function stripAnsi(value) {
  return String(value || "").replace(/\x1B\[[0-?]*[ -/]*[@-~]/g, "");
}

function truncate(value, width) {
  const text = stripAnsi(value);
  if (width <= 1) return "";
  return text.length > width ? `${text.slice(0, Math.max(0, width - 1))}…` : text;
}

function wrap(value, width) {
  const words = stripAnsi(value).replace(/\r/g, "").split(/\s+/);
  const lines = [];
  let current = "";
  for (const word of words) {
    if (!word) continue;
    if (!current) {
      current = word;
    } else if (`${current} ${word}`.length <= width) {
      current += ` ${word}`;
    } else {
      lines.push(current);
      current = word;
    }
    while (current.length > width) {
      lines.push(current.slice(0, width));
      current = current.slice(width);
    }
  }
  if (current) lines.push(current);
  return lines.length ? lines : [""];
}

function boxLine(left, right, leftWidth, rightWidth) {
  return `│ ${truncate(left, leftWidth).padEnd(leftWidth)} │ ${truncate(right, rightWidth).padEnd(rightWidth)} │`;
}

function formatChat(entry, width) {
  const label = entry.role === "user" ? "You" : entry.role === "proactive" ? "Alice proactive" : entry.role === "assistant" ? "Alice" : "System";
  const prefix = `${label}: `;
  const lines = wrap(entry.text, Math.max(10, width - prefix.length));
  return lines.map((line, index) => `${index === 0 ? prefix : " ".repeat(prefix.length)}${line}`);
}

function runRuntimeTui(child, options = {}) {
  const state = {
    chat: [],
    logs: [],
    input: "",
    status: "starting",
    dashboard: options.dashboard || "http://127.0.0.1:8080",
    stopping: false,
  };

  let stdoutBuffer = "";
  let stderrBuffer = "";
  let renderTimer = null;
  let stopRequested = false;
  let resolved = false;
  const isTty = process.stdin.isTTY && process.stdout.isTTY;

  function childRunning() {
    return child.exitCode === null && child.signalCode === null;
  }

  function addChat(role, text) {
    state.chat.push({ role, text: String(text || "") });
    if (state.chat.length > 200) state.chat = state.chat.slice(-200);
    scheduleRender();
  }

  function addLog(text) {
    for (const rawLine of String(text || "").split(/\n/)) {
      const line = stripAnsi(rawLine).trimEnd();
      if (!line || line === ">") continue;
      state.logs.push(line);
    }
    if (state.logs.length > 400) state.logs = state.logs.slice(-400);
    scheduleRender();
  }

  function handleLine(line, stream) {
    const clean = line.trimEnd();
    if (!clean) return;
    if (clean.startsWith(EVENT_PREFIX)) {
      try {
        const event = JSON.parse(clean.slice(EVENT_PREFIX.length));
        addChat(event.role || "system", event.text || "");
        return;
      } catch {
        addLog(clean);
        return;
      }
    }
    addLog(stream === "stderr" ? `[stderr] ${clean}` : clean);
  }

  function consume(chunk, stream) {
    let buffer = stream === "stderr" ? stderrBuffer : stdoutBuffer;
    buffer += chunk.toString();
    const lines = buffer.split(/\n/);
    buffer = lines.pop() || "";
    for (const line of lines) handleLine(line, stream);
    if (stream === "stderr") stderrBuffer = buffer;
    else stdoutBuffer = buffer;
  }

  function scheduleRender() {
    if (!isTty) return;
    if (renderTimer) return;
    renderTimer = setTimeout(() => {
      renderTimer = null;
      render();
    }, 30);
  }

  function render() {
    if (!isTty) return;
    const width = Math.max(80, process.stdout.columns || 100);
    const height = Math.max(24, process.stdout.rows || 30);
    const leftWidth = Math.max(34, Math.floor((width - 7) * 0.58));
    const rightWidth = Math.max(28, width - leftWidth - 7);
    const bodyHeight = height - 7;

    const chatLines = [];
    for (const entry of state.chat) {
      chatLines.push(...formatChat(entry, leftWidth), "");
    }
    const visibleChat = chatLines.slice(-bodyHeight);
    const visibleLogs = state.logs.slice(-bodyHeight);

    const top = `┌${"─".repeat(leftWidth + 2)}┬${"─".repeat(rightWidth + 2)}┐`;
    const sep = `├${"─".repeat(leftWidth + 2)}┼${"─".repeat(rightWidth + 2)}┤`;
    const bottom = `└${"─".repeat(leftWidth + 2)}┴${"─".repeat(rightWidth + 2)}┘`;
    const inputLine = `> ${state.input}`;

    const lines = [
      top,
      boxLine("Chat", `Logs • ${state.status} • ${state.dashboard}`, leftWidth, rightWidth),
      sep,
    ];

    for (let index = 0; index < bodyHeight; index += 1) {
      lines.push(boxLine(visibleChat[index] || "", visibleLogs[index] || "", leftWidth, rightWidth));
    }

    lines.push(bottom);
    lines.push(truncate(inputLine, width - 1));
    lines.push(truncate("Enter sends • /help commands • /exit stops • Ctrl+C stops", width - 1));

    process.stdout.write("\x1b[H\x1b[2J");
    process.stdout.write(lines.join("\n"));
  }

  function restoreTerminal() {
    if (!isTty) return;
    process.stdin.setRawMode(false);
    process.stdout.write("\x1b[?25h\x1b[?1049l");
  }

  function stopChild(reason = "/exit") {
    if (stopRequested) return;
    stopRequested = true;
    state.stopping = true;
    state.status = "stopping";
    scheduleRender();
    try {
      if (child.stdin.writable && reason !== "child-exit") child.stdin.write("/exit\n");
    } catch {}
    try {
      if (child.stdin.writable) child.stdin.end();
    } catch {}
    setTimeout(() => {
      if (childRunning()) child.kill("SIGTERM");
    }, 1200).unref();
    setTimeout(() => {
      if (childRunning()) child.kill("SIGKILL");
    }, 3500).unref();
  }

  function sendLine() {
    const line = state.input.trim();
    state.input = "";
    if (!line) {
      scheduleRender();
      return;
    }
    addChat("user", line);
    if (line === "/exit" || line === "/quit" || line === "/stop") {
      stopChild(line);
      scheduleRender();
      return;
    }
    child.stdin.write(`${line}\n`);
    scheduleRender();
  }

  return new Promise((resolve) => {
    function finish(code) {
      if (resolved) return;
      resolved = true;
      if (stdoutBuffer) handleLine(stdoutBuffer, "stdout");
      if (stderrBuffer) handleLine(stderrBuffer, "stderr");
      if (isTty) {
        process.stdin.off("keypress", onKeypress);
        process.stdout.off("resize", scheduleRender);
        restoreTerminal();
      }
      console.log(`Alive-AI stopped${code ? ` with exit code ${code}` : ""}.`);
      resolve(code || 0);
    }

    if (!isTty) {
      child.stdout.on("data", (chunk) => process.stdout.write(chunk));
      child.stderr.on("data", (chunk) => process.stderr.write(chunk));
      child.on("exit", (code) => resolve(code || 0));
      return;
    }

    process.stdout.write("\x1b[?1049h\x1b[?25l");
    readline.emitKeypressEvents(process.stdin);
    process.stdin.setRawMode(true);
    process.stdin.resume();

    addChat("system", "Type a message and press Enter. The runtime logs stay on the right.");
    child.stdout.on("data", (chunk) => consume(chunk, "stdout"));
    child.stderr.on("data", (chunk) => consume(chunk, "stderr"));

    const onKeypress = (str, key = {}) => {
      if (key.ctrl && key.name === "c") {
        stopChild("ctrl-c");
        return;
      }
      if (key.name === "return") {
        sendLine();
        return;
      }
      if (key.name === "backspace") {
        state.input = state.input.slice(0, -1);
        scheduleRender();
        return;
      }
      if (key.name === "escape") {
        state.input = "";
        scheduleRender();
        return;
      }
      if (str && !key.ctrl && !key.meta) {
        state.input += str;
        scheduleRender();
      }
    };

    process.stdin.on("keypress", onKeypress);
    process.stdout.on("resize", scheduleRender);
    process.once("SIGINT", () => stopChild("sigint"));
    process.once("SIGTERM", () => stopChild("sigterm"));
    render();

    child.on("exit", (code) => finish(code || 0));
    child.on("close", (code) => finish(code || 0));
  });
}

module.exports = { runRuntimeTui };

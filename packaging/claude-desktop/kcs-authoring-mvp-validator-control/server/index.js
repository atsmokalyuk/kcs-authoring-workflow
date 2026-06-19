#!/usr/bin/env node
const fs = require("fs");
const os = require("os");
const path = require("path");
const { spawn } = require("child_process");

const PREFIX = "[kcs-authoring-mvp-validator-control]";

function fail(message) {
  console.error(`${PREFIX} ${message}`);
  process.exit(1);
}

function hasControlCharacters(value) {
  return /[\r\n\0]/.test(value);
}

function hasShellSeparators(value) {
  return /[\r\n\0\t ]/.test(value);
}

function executableFile(candidate) {
  try {
    fs.accessSync(candidate, fs.constants.X_OK);
    return true;
  } catch (_error) {
    return false;
  }
}

function findExecutable(command) {
  if (!command || hasShellSeparators(command)) {
    return null;
  }
  if (command.includes("/") || command.includes("\\")) {
    const resolved = path.resolve(command);
    return executableFile(resolved) ? resolved : null;
  }
  const pathValue = process.env.PATH || "";
  for (const directory of pathValue.split(path.delimiter)) {
    if (!directory) {
      continue;
    }
    const candidate = path.join(directory, command);
    if (executableFile(candidate)) {
      return candidate;
    }
  }
  return null;
}

function runtimeOverride(name) {
  const value = process.env[name] || "";
  if (!value) {
    return "";
  }
  if (hasShellSeparators(value)) {
    fail(`${name} must be an executable name or path without arguments.`);
  }
  return value;
}

function isKcsProjectRoot(candidateRoot) {
  const pyproject = path.join(candidateRoot, "pyproject.toml");
  const adapterPath = path.join(candidateRoot, "src", "kcs_adapters", "mcp_desktop.py");
  if (!fs.existsSync(pyproject) || !fs.existsSync(adapterPath)) {
    return false;
  }
  try {
    const pyprojectText = fs.readFileSync(pyproject, "utf8");
    return pyprojectText.includes('name = "kcs-authoring-mvp"');
  } catch (_error) {
    return false;
  }
}

function resolveProjectRoot() {
  const explicitRoot = process.env.KCS_AUTHORING_MVP_REPO_ROOT || "";
  if (explicitRoot) {
    if (hasControlCharacters(explicitRoot)) {
      fail("KCS_AUTHORING_MVP_REPO_ROOT is invalid.");
    }
    const resolved = path.resolve(explicitRoot);
    if (!isKcsProjectRoot(resolved)) {
      fail("KCS_AUTHORING_MVP_REPO_ROOT must point to the KCS Authoring MVP project.");
    }
    return resolved;
  }

  const bundledRoot = path.resolve(__dirname, "..", "python");
  if (isKcsProjectRoot(bundledRoot)) {
    return bundledRoot;
  }

  const sourceRoot = path.resolve(__dirname, "..", "..", "..", "..");
  if (isKcsProjectRoot(sourceRoot)) {
    return sourceRoot;
  }

  fail("KCS Authoring bundled Python project was not found.");
}

const projectRoot = resolveProjectRoot();
const bundledProjectRoot = path.resolve(__dirname, "..", "python");
const isBundledProject = projectRoot === bundledProjectRoot;

function resolveUvCommand() {
  const explicit = runtimeOverride("KCS_AUTHORING_MVP_UV_COMMAND");
  if (explicit) {
    const resolved = findExecutable(explicit);
    if (!resolved) {
      fail("KCS_AUTHORING_MVP_UV_COMMAND executable was not found.");
    }
    return resolved;
  }
  const home = process.env.HOME || process.env.USERPROFILE || "";
  const candidates = [
    "uv",
    home ? path.join(home, ".local", "bin", "uv") : "",
    home ? path.join(home, ".cargo", "bin", "uv") : "",
    "/opt/homebrew/bin/uv",
    "/usr/local/bin/uv",
  ];
  for (const candidate of candidates) {
    const resolved = findExecutable(candidate);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}

function resolvePythonCommand() {
  const explicit = runtimeOverride("KCS_AUTHORING_MVP_PYTHON_COMMAND");
  if (explicit) {
    const resolved = findExecutable(explicit);
    if (!resolved) {
      fail("KCS_AUTHORING_MVP_PYTHON_COMMAND executable was not found.");
    }
    return resolved;
  }
  const home = process.env.HOME || process.env.USERPROFILE || "";
  const candidates = [
    "python3.11",
    "python3",
    home ? path.join(home, ".local", "bin", "python3.11") : "",
    "/opt/homebrew/bin/python3.11",
    "/usr/local/bin/python3.11",
    "/usr/bin/python3",
  ];
  for (const candidate of candidates) {
    const resolved = findExecutable(candidate);
    if (resolved) {
      return resolved;
    }
  }
  return null;
}

function resolveRuntime() {
  const uv = resolveUvCommand();
  if (uv) {
    return {
      args: [
        "--project",
        projectRoot,
        "run",
        "kcs-desktop-mcp",
        "--tool-name-style",
        "claude_desktop_aliases",
      ],
      command: uv,
      kind: "uv",
    };
  }
  const python = resolvePythonCommand();
  if (python) {
    return {
      args: [
        "-m",
        "kcs_adapters.mcp_desktop",
        "--tool-name-style",
        "claude_desktop_aliases",
      ],
      command: python,
      kind: "python",
    };
  }
  fail("KCS Authoring requires uv or Python 3.11+ available to Claude Desktop.");
}

const runtime = resolveRuntime();

const childEnv = {
  APPDATA: process.env.APPDATA || "",
  HOME: process.env.HOME || "",
  KCS_AUTHORING_MVP_REPO_ROOT: projectRoot,
  KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT:
    process.env.KCS_AUTHORING_MVP_APPROVED_TICKET_STORE_ROOT ||
    (isBundledProject ? path.join(os.homedir(), "Documents", "KCS Authoring") : ""),
  KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_HINT:
    process.env.KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_HINT ||
    (isBundledProject ? "~/Documents/KCS Authoring" : ""),
  KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_REF:
    process.env.KCS_AUTHORING_MVP_APPROVED_TICKET_STORAGE_REF ||
    (isBundledProject ? "user_documents_kcs_authoring" : ""),
  KCS_AUTHORING_MVP_REVIEWER_BUNDLE_ROOT:
    process.env.KCS_AUTHORING_MVP_REVIEWER_BUNDLE_ROOT ||
    (isBundledProject
      ? path.join(
          os.homedir(),
          "Documents",
          "KCS Authoring",
          "local-data",
          "reviewer-bundles",
        )
      : ""),
  KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_HINT:
    process.env.KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_HINT ||
    (isBundledProject ? "~/Documents/KCS Authoring" : ""),
  KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_REF:
    process.env.KCS_AUTHORING_MVP_REVIEWER_BUNDLE_STORAGE_REF ||
    (isBundledProject ? "user_documents_kcs_authoring" : ""),
  KCS_AUTHORING_MVP_RUNTIME: runtime.kind,
  KCS_AUTHORING_MVP_UV_COMMAND: runtime.kind === "uv" ? runtime.command : "",
  KCS_AUTHORING_APPROVED_SEMANTIC_PROVIDER_REF:
    process.env.KCS_AUTHORING_APPROVED_SEMANTIC_PROVIDER_REF || "",
  KCS_AUTHORING_SEMANTIC_PROVIDER:
    process.env.KCS_AUTHORING_SEMANTIC_PROVIDER || "",
  LANG: process.env.LANG || "C.UTF-8",
  LC_ALL: process.env.LC_ALL || "",
  LOCALAPPDATA: process.env.LOCALAPPDATA || "",
  PATH: process.env.PATH || "",
  PATHEXT: process.env.PATHEXT || "",
  PYTHONPATH: path.join(projectRoot, "src"),
  SystemRoot: process.env.SystemRoot || "",
  TEMP: process.env.TEMP || "",
  TMP: process.env.TMP || "",
  TMPDIR: process.env.TMPDIR || "",
  USERPROFILE: process.env.USERPROFILE || "",
  XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || "",
};

const child = spawn(runtime.command, runtime.args, {
  cwd: projectRoot,
  env: childEnv,
  stdio: ["pipe", "pipe", "pipe"],
});

let stdoutBuffer = "";
const stdoutQueue = [];
let stdoutFlushScheduled = false;
let pendingExit = null;

function enqueueStdoutLine(line) {
  if (!line) {
    return;
  }
  stdoutQueue.push(line);
  if (!stdoutFlushScheduled) {
    stdoutFlushScheduled = true;
    setTimeout(flushStdoutQueue, 5);
  }
}

function flushStdoutQueue() {
  const line = stdoutQueue.shift();
  if (line !== undefined) {
    process.stdout.write(`${line}\n`);
  }
  if (stdoutQueue.length > 0) {
    setTimeout(flushStdoutQueue, 5);
    return;
  }
  stdoutFlushScheduled = false;
  finishIfReady();
}

function finishIfReady() {
  if (!pendingExit || stdoutFlushScheduled || stdoutQueue.length > 0 || stdoutBuffer) {
    return;
  }
  if (pendingExit.signal) {
    process.kill(process.pid, pendingExit.signal);
    return;
  }
  process.exit(pendingExit.code === null ? 1 : pendingExit.code);
}

process.stdin.pipe(child.stdin);

child.stdout.setEncoding("utf8");
child.stdout.on("data", (chunk) => {
  stdoutBuffer += chunk;
  const lines = stdoutBuffer.split(/\r?\n/);
  stdoutBuffer = lines.pop() || "";
  for (const line of lines) {
    enqueueStdoutLine(line);
  }
});

child.stdout.on("end", () => {
  enqueueStdoutLine(stdoutBuffer);
  stdoutBuffer = "";
  finishIfReady();
});

child.stderr.pipe(process.stderr);

child.stdin.on("error", (error) => {
  if (error.code !== "EPIPE") {
    console.error(`${PREFIX} child stdin error: ${error.name}`);
  }
});

child.on("error", (error) => {
  fail(`failed to start ${runtime.kind}: ${error.name}`);
});

child.on("exit", (code, signal) => {
  pendingExit = { code, signal };
  finishIfReady();
});

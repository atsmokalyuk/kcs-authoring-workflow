#!/usr/bin/env node
const fs = require("fs");
const path = require("path");
const { spawn } = require("child_process");

const PREFIX = "[kcs-authoring-mvp-validator-control]";

function fail(message) {
  console.error(`${PREFIX} ${message}`);
  process.exit(1);
}

const repoRoot = process.env.KCS_AUTHORING_MVP_REPO_ROOT;
const uvCommand = process.env.KCS_AUTHORING_MVP_UV_COMMAND || "uv";

if (!repoRoot || /[\r\n\0]/.test(repoRoot)) {
  fail("KCS_AUTHORING_MVP_REPO_ROOT is required.");
}

if (!uvCommand || /[\r\n\0\t ]/.test(uvCommand)) {
  fail("KCS_AUTHORING_MVP_UV_COMMAND must be a uv executable name or path without arguments.");
}

const pyproject = path.join(repoRoot, "pyproject.toml");
if (!fs.existsSync(pyproject)) {
  fail("repository_root must point to the KCS Authoring MVP repository.");
}

const pyprojectText = fs.readFileSync(pyproject, "utf8");
if (!pyprojectText.includes('name = "kcs-authoring-mvp"')) {
  fail("repository_root must point to the KCS Authoring MVP repository.");
}

const adapterPath = path.join(repoRoot, "src", "kcs_adapters", "mcp_desktop.py");
if (!fs.existsSync(adapterPath)) {
  fail("repository_root must point to the KCS Authoring MVP repository.");
}

const args = [
  "--project",
  repoRoot,
  "run",
  "kcs-desktop-mcp",
  "--tool-name-style",
  "claude_desktop_aliases",
];

const childEnv = {
  APPDATA: process.env.APPDATA || "",
  HOME: process.env.HOME || "",
  KCS_AUTHORING_MVP_REPO_ROOT: repoRoot,
  KCS_AUTHORING_MVP_UV_COMMAND: uvCommand,
  KCS_AUTHORING_APPROVED_SEMANTIC_PROVIDER_REF:
    process.env.KCS_AUTHORING_APPROVED_SEMANTIC_PROVIDER_REF || "",
  KCS_AUTHORING_SEMANTIC_PROVIDER:
    process.env.KCS_AUTHORING_SEMANTIC_PROVIDER || "",
  LANG: process.env.LANG || "C.UTF-8",
  LC_ALL: process.env.LC_ALL || "",
  LOCALAPPDATA: process.env.LOCALAPPDATA || "",
  PATH: process.env.PATH || "",
  PATHEXT: process.env.PATHEXT || "",
  SystemRoot: process.env.SystemRoot || "",
  TEMP: process.env.TEMP || "",
  TMP: process.env.TMP || "",
  TMPDIR: process.env.TMPDIR || "",
  USERPROFILE: process.env.USERPROFILE || "",
  XDG_CACHE_HOME: process.env.XDG_CACHE_HOME || "",
};

const child = spawn(uvCommand, args, {
  cwd: repoRoot,
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
  fail(`failed to start uv: ${error.name}`);
});

child.on("exit", (code, signal) => {
  pendingExit = { code, signal };
  finishIfReady();
});

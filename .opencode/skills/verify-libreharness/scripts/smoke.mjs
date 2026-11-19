#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// One honest smoke path for the plugin and the queue. It owns its state
// directory, drives the real hooks and CLI, and leaves a machine-readable report.
import { execFileSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "../../../..");
const TASKS = join(ROOT, "bin/tasks.py");
const REPORT_DIR = "/tmp/opencode/verify-libreharness";
const REPORT = join(REPORT_DIR, "latest.json");

const verified = [];
const unverified = [
  "OpenCode TUI transport",
  "remote Jev endpoint responses",
  "GitHub Actions auto-merge gate",
];

let state = "";
let taskId = "";
let failure = "";

function queue(args) {
  return execFileSync("python3", [TASKS, ...args], {
    encoding: "utf8",
    env: {
      PATH: process.env.PATH ?? "/usr/bin:/bin",
      HOME: process.env.HOME ?? "",
      HARNESS_STATE: state,
      PYTHONDONTWRITEBYTECODE: "1",
    },
  }).trim();
}

function check(condition, message) {
  if (!condition) throw new Error(message);
}

function writeReport(verdict) {
  mkdirSync(REPORT_DIR, { recursive: true });
  writeFileSync(
    REPORT,
    `${JSON.stringify(
      {
        verdict,
        stateDir: state,
        stateRemoved: state !== "" && !existsSync(state),
        taskId,
        verified,
        unverified,
        ...(failure ? { failure } : {}),
      },
      null,
      2,
    )}\n`,
  );
}

let cleanup = null;

try {
  state = mkdtempSync(join(tmpdir(), "verify-libreharness-"));
  const hooks = [];
  let promptHook = null;
  const ctx = {
    options: { state },
    location: { directory: ROOT },
    command: { transform: (callback) => callback({ add: () => {} }) },
    agent: {
      transform: (callback) => callback({ get: () => undefined, update: () => {} }),
    },
    skill: { transform: (callback) => callback({ add: () => {} }) },
    session: {
      hook: async (name, callback) => {
        hooks.push(name);
        if (name === "prompt") promptHook = callback;
      },
      prompt: async () => {},
    },
    event: { subscribe: () => (async function* () {})() },
  };

  const { default: plugin } = await import(
    new URL("../../../../src/plugin.js", import.meta.url)
  );
  cleanup = await plugin.setup(ctx);
  check(typeof cleanup === "function", "plugin.setup did not return a cleanup function");
  check((statSync(state).mode & 0o777) === 0o700, "state directory is not mode 0700");
  check(hooks.includes("context"), "context hook is not registered");
  check(hooks.includes("prompt"), "prompt hook is not registered");
  verified.push("plugin.setup", "state mode 0700", "context and prompt hooks");

  const event = {
    sessionID: "smoke",
    prompt: { text: "Fix the login redirect bug" },
  };
  await promptHook(event);
  const match = event.prompt.text.match(/Task ([^\s]+)/);
  check(match, "intake notice did not name a task");
  taskId = match[1];
  verified.push("auto-intake prompt hook");

  const taskPath = join(state, "work/tasks", `${taskId}.md`);
  check(existsSync(taskPath), `task file missing: ${taskPath}`);
  const task = readFileSync(taskPath, "utf8");
  check(task.includes("status: inbox"), "task is not inbox");
  const accepted = task.replace(
    /^- \[ \] TBD.*$/m,
    "- [x] tasks.py validate exits 0",
  );
  check(accepted !== task, "acceptance placeholder missing");
  writeFileSync(taskPath, accepted);

  queue(["claim", taskId, "--owner", "smoke"]);
  queue(["status", taskId, "review"]);
  queue(["validate"]);
  verified.push("queue claim, review, validate");

  queue([
    "status",
    taskId,
    "done",
    "--evidence",
    "python3 bin/tasks.py validate: exit 0",
  ]);
  check(
    readFileSync(taskPath, "utf8").includes("status: done"),
    "task did not reach done",
  );
  check(existsSync(join(state, "work/BOARD.md")), "board was not written");
  check(
    existsSync(join(state, "metrics/workflow-log.csv")),
    "workflow log was not written",
  );
  verified.push("queue done with evidence", "board and workflow log");
} catch (error) {
  failure = error?.message ?? String(error);
}

if (cleanup) {
  try {
    cleanup();
  } catch {
    // A failed cleanup must not hide the drive result.
  }
}
if (state) rmSync(state, { recursive: true, force: true });

const verdict = failure === "" && state !== "" && !existsSync(state) ? "PASS" : "FAIL";
if (failure === "" && verdict === "FAIL") failure = "state directory survived cleanup";
writeReport(verdict);

if (verdict === "PASS") {
  console.log(`verify-libreharness: PASS (${taskId})`);
  console.log(`report: ${REPORT}`);
} else {
  console.error(`verify-libreharness: FAIL: ${failure}`);
  console.error(`report: ${REPORT}`);
  process.exit(1);
}

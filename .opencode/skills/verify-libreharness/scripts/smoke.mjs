#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// One honest smoke path for the plugin and the queue. It owns its state
// directory, drives the real hooks and CLI, and leaves a machine-readable report.
import { execFileSync, spawnSync } from "node:child_process";
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
  "GitHub Actions auto-merge gate",
];

let state = "";
let taskId = "";
let head = "";
let checks = [];
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
        head,
        verdict,
        checks,
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
  check(hooks.includes("prompt"), "prompt hook is not registered");
  check(!hooks.includes("context"), "the plugin must not inject instructions");
  verified.push("plugin.setup", "state mode 0700", "native instruction ownership");

  const event = {
    sessionID: "smoke",
    prompt: { text: "Fix the login redirect bug" },
  };
  await promptHook(event);
  const match = event.prompt.text.match(/Task ([^\s]+)/);
  check(match, "intake notice did not name a task");
  taskId = match[1];
  verified.push("auto-intake prompt hook", "session-task usage mapping");

  const taskPath = join(state, "work/tasks", `${taskId}.md`);
  check(existsSync(taskPath), `task file missing: ${taskPath}`);
  check(
    existsSync(join(state, "metrics/session-tasks.jsonl")),
    "session-task usage mapping was not written",
  );
  const task = readFileSync(taskPath, "utf8");
  check(task.includes("status: inbox"), "task is not inbox");
  const premature = spawnSync(
    "python3",
    [TASKS, "claim", taskId, "--owner", "smoke", "--repo", ROOT],
    {
      encoding: "utf8",
      env: {
        PATH: process.env.PATH ?? "/usr/bin:/bin",
        HOME: process.env.HOME ?? "",
        HARNESS_STATE: state,
        PYTHONDONTWRITEBYTECODE: "1",
      },
    },
  );
  check(premature.status !== 0, "placeholder intake task was claimable");
  check(
    premature.stderr.includes("concrete Scope"),
    "premature claim failure did not name the scope boundary",
  );
  const scoped = task.replace(/^Auto-captured prompt;.*$/m, "Fix the login redirect.");
  check(scoped !== task, "scope placeholder missing");
  const accepted = scoped.replace(
    /^- \[ \] TBD.*$/m,
    "- [x] review artifact records a PASS at HEAD",
  );
  check(accepted !== scoped, "acceptance placeholder missing");
  const planned = accepted.replace(
    /## Plan\n\n/,
    `## Plan\n\nData shape: {"task":"string","status":"string"}\n` +
      "Verify: node tests/harness-ratchets.test.mjs\n\n",
  );
  check(planned !== accepted, "task Plan section missing");
  writeFileSync(taskPath, planned);

  head = execFileSync("git", ["-C", ROOT, "rev-parse", "HEAD"], {
    encoding: "utf8",
  }).trim();

  queue(["claim", taskId, "--owner", "smoke", "--repo", ROOT]);
  queue([
    "review",
    taskId,
    "--repo",
    ROOT,
    "--run",
    "node tests/harness-ratchets.test.mjs",
  ]);
  const artifactPath = join(state, "work/reviews", `${taskId}.json`);
  check(existsSync(artifactPath), "review artifact was not written");
  const artifact = JSON.parse(readFileSync(artifactPath, "utf8"));
  check(artifact.head === head, "review artifact head does not match git HEAD");
  check(
    typeof artifact.diff_sha256 === "string" && artifact.diff_sha256.length === 64,
    "review artifact has no diff fingerprint",
  );
  check(artifact.verdict === "PASS", "review artifact is not PASS");
  check(
    Array.isArray(artifact.checks) && artifact.checks.length > 0,
    "review artifact has no observed checks",
  );
  checks = artifact.checks;
  check(
    artifact.checks.some(
      (item) =>
        item.command === "node tests/harness-ratchets.test.mjs" &&
        item.exit === 0,
    ),
    "review artifact is missing the required ratchet check",
  );
  verified.push("review artifact at HEAD with observed checks");

  queue(["status", taskId, "review", "--repo", ROOT]);
  queue(["validate"]);
  verified.push("queue claim, review, validate");

  queue([
    "status",
    taskId,
    "done",
    "--evidence",
    `review artifact ${artifactPath} PASS at ${head}; tasks.py validate exit 0`,
    "--repo",
    ROOT,
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

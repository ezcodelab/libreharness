// SPDX-License-Identifier: MIT
import { copyFileSync, mkdirSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(tmpdir(), `goal-watch-${process.pid}`);
rmSync(root, { recursive: true, force: true });
mkdirSync(join(root, "bin"), { recursive: true });
mkdirSync(join(root, "work/tasks"), { recursive: true });
copyFileSync(
  join(here, "..", "bin", "tasks.py"),
  join(root, "bin/tasks.py"),
);
process.env.GOAL_WATCH_TASKS = join(root, "bin", "tasks.py");
const tasks = (...args) =>
  execFileSync("python3", [join(root, "bin/tasks.py"), ...args], {
    encoding: "utf8",
    env: {
      ...process.env,
      HARNESS_STATE: root,
      PYTHONDONTWRITEBYTECODE: "1",
    },
  }).trim();
const goal = tasks(
  "goal",
  "Demo goal",
  "--project",
  "demo",
  "--session",
  "s1",
  "--autorun",
  "--max-continuations",
  "3",
);
tasks("new", "Child one", "--project", "demo", "--parent", goal);
if (!goal) throw new Error("goal not created");

process.env.GOAL_WATCH_ROOT = root;
const { default: plugin, maxContinuations } = await import(
  new URL(`../plugins/goal-watch.js?test=${process.pid}`, import.meta.url)
);
if (maxContinuations("abc") !== 12 || maxContinuations("") !== 12 || maxContinuations("0") !== 0) {
  throw new Error("malformed continuation bound is not handled");
}

const prompts = [];
const queue = [];
let waiter = null;
const emit = (event) => {
  if (waiter) { const r = waiter; waiter = null; r(event); }
  else queue.push(event);
};
const ctx = {
  event: {
    subscribe: async function* () {
      while (true) {
        const event = queue.length
          ? queue.shift()
          : await new Promise((resolve) => { waiter = resolve; });
        yield event;
      }
    },
  },
  session: {
    prompt: async (input) => { prompts.push(input); },
  },
};

const cleanup = await plugin.setup(ctx);
await new Promise((r) => setTimeout(r, 1));
emit({ type: "session.idle", data: { sessionID: "s2" } });
await new Promise((r) => setTimeout(r, 100));
if (prompts.length !== 0) throw new Error("nudged an unrelated session");

for (let i = 0; i < 3; i += 1) {
  emit({ type: "session.idle", data: { sessionID: "s1" } });
  await new Promise((r) => setTimeout(r, 300));
}
if (prompts.length !== 3) throw new Error("per-goal budget was not exhausted");
emit({ type: "session.idle", data: { sessionID: "s1" } });
await new Promise((r) => setTimeout(r, 300));
if (prompts.length !== 3) throw new Error("nudged past max_continuations");

tasks("goal", "Second goal", "--project", "demo", "--session", "s1", "--unattended");
emit({ type: "session.idle", data: { sessionID: "s1" } });
await new Promise((r) => setTimeout(r, 250));
if (prompts.length !== 3) throw new Error("nudged with two active goals");

const closeGoal = tasks("goal", "Close me", "--project", "demo", "--session", "s1");
const closeChild = tasks("new", "Done child", "--project", "demo", "--parent", closeGoal);
tasks("claim", closeChild, "--owner", "test");
tasks("status", closeChild, "done", "--evidence", "node: done");
emit({ type: "session.idle", data: { sessionID: "s1" } });
await new Promise((r) => setTimeout(r, 300));
if (prompts.length !== 4) throw new Error("closable goal was not reminded");
if (!prompts[3].text.includes(closeGoal) || !prompts[3].text.includes("ready to close")) {
  throw new Error("close reminder does not name the goal");
}
if (!prompts[3].text.includes("close now") || !prompts[3].text.includes("later")) {
  throw new Error("close reminder does not offer close now/later");
}
emit({ type: "session.idle", data: { sessionID: "s1" } });
await new Promise((r) => setTimeout(r, 300));
if (prompts.length !== 4) throw new Error("close reminder repeated in the same session");

emit({ type: "session.idle", data: { sessionID: "s2" } });
await new Promise((r) => setTimeout(r, 300));
if (prompts.length !== 5) throw new Error("closable goal was not reminded in another session");
if (!prompts[4].text.includes(closeGoal) || !prompts[4].text.includes("ignore this reminder")) {
  throw new Error("cross-session reminder is not scoped");
}
emit({ type: "session.idle", data: { sessionID: "s2" } });
await new Promise((r) => setTimeout(r, 300));
if (prompts.length !== 5) throw new Error("close reminder repeated in the same second session");
cleanup();

if (!prompts[0].text.includes(`Continue the active goal ${goal}`)) {
  throw new Error("continuation prompt does not name the goal");
}
if (!prompts[0].text.includes("Next ready child")) {
  throw new Error("continuation prompt does not name the next child");
}
rmSync(root, { recursive: true, force: true });
console.log("goal-watch: PASS");

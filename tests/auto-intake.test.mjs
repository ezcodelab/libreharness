// SPDX-License-Identifier: MIT
import { copyFileSync, mkdirSync, readFileSync, rmSync } from "node:fs";

import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { execFileSync } from "node:child_process";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(tmpdir(), `auto-intake-${process.pid}`);
const taskCli = (...args) =>
  execFileSync("python3", [join(root, "bin/tasks.py"), ...args], {
    encoding: "utf8",
    env: {
      ...process.env,
      HARNESS_STATE: root,
      PYTHONDONTWRITEBYTECODE: "1",
    },
  }).trim();
rmSync(root, { recursive: true, force: true });
mkdirSync(join(root, "bin"), { recursive: true });
mkdirSync(join(root, "work/tasks"), { recursive: true });
copyFileSync(
  join(here, "..", "bin", "tasks.py"),
  join(root, "bin/tasks.py"),
);

process.env.AUTO_INTAKE_ROOT = root;
process.env.AUTO_INTAKE_TASKS = join(root, "bin", "tasks.py");
process.env.AUTO_INTAKE = "on";
const { default: plugin } = await import(
  new URL(`../plugins/auto-intake.js?test=${process.pid}`, import.meta.url)
);

let hook;
const ctx = {
  location: { directory: "/tmp/example-project" },
  session: { hook: async (_name, callback) => { hook = callback; } },
};
await plugin.setup(ctx);
if (!hook) throw new Error("prompt hook not registered");

const first = { sessionID: "s1", prompt: { text: "Fix the login redirect bug" } };
hook(first);
if (!first.prompt.text.includes("[queue] Task ")) {
  throw new Error("task note was not injected");
}
if (!first.prompt.text.includes("goal skill") || first.prompt.text.includes("/intake")) {
  throw new Error("queue notice does not route to the goal skill");
}
const id = first.prompt.text.match(/Task ([^\s]+)/)?.[1];
if (!id) throw new Error("task id missing");
const task = readFileSync(join(root, "work/tasks", `${id}.md`), "utf8");
if (!task.includes("status: inbox")) throw new Error("task not inbox");
if (!task.includes("example-project")) throw new Error("project not inferred");

const second = { sessionID: "s1", prompt: { text: "Add another endpoint" } };
hook(second);
if (second.prompt.text.includes("[queue] Task ")) {
  throw new Error("duplicate task created for one session");
}

const otherSession = {
  sessionID: "s4",
  prompt: { text: "Fix the login redirect bug" },
};
hook(otherSession);
if (!otherSession.prompt.text.includes("Existing task")) {
  throw new Error("same prompt in a new session did not reuse the task");
}
const afterOther = readFileSync(join(root, "work/tasks", `${id}.md`), "utf8");
if (!afterOther.includes("status: inbox")) throw new Error("task changed");

taskCli("claim", id, "--owner", "test");
taskCli("status", id, "done", "--evidence", "unit: pass");
const closed = {
  sessionID: "s10",
  prompt: { text: "Fix the login redirect bug" },
};
hook(closed);
if (closed.prompt.text.includes("Existing task")) {
  throw new Error("closed task was reused");
}
if (!closed.prompt.text.includes("[queue] Task ")) {
  throw new Error("closed task did not get a fresh task");
}

const question = { sessionID: "s2", prompt: { text: "What does rotate.py do?" } };
hook(question);
if (question.prompt.text.includes("[queue] Task ")) {
  throw new Error("question was queued as a task");
}

const secret = {
  sessionID: "s3",
  prompt: { text: 'Fix it with api_key = "abcdefgh1234"' },
};
hook(secret);
if (secret.prompt.text.includes("[queue] Task ")) {
  throw new Error("secret-shaped prompt was written to a task");
}

const unquotedSecret = {
  sessionID: "s5",
  prompt: { text: "Fix it with STRIPE_KEY=sk_live_abcdefghijklmnop" },
};
hook(unquotedSecret);
if (unquotedSecret.prompt.text.includes("[queue] Task ")) {
  throw new Error("unquoted secret-shaped prompt was written to a task");
}

const quotedSecret = {
  sessionID: "s7",
  prompt: { text: 'Fix login with password: "P@ssw0rd123"' },
};
hook(quotedSecret);
if (quotedSecret.prompt.text.includes("[queue] Task ")) {
  throw new Error("quoted secret-shaped prompt was written to a task");
}

const closeNudge = {
  sessionID: "s8",
  prompt: {
    text: "Task may be complete. Run /close when you are done: final /review if needed, Jev triage, one project lesson.",
  },
};
hook(closeNudge);
if (closeNudge.prompt.text.includes("[queue] Task ")) {
  throw new Error("close-reminder prompt was queued");
}

const delegation = {
  sessionID: "s6",
  prompt: {
    text: "You are a subagent spawned by another session. Read-only audit.",
  },
};
hook(delegation);
if (delegation.prompt.text.includes("[queue] Task ")) {
  throw new Error("subagent prompt was queued");
}

const role = {
  sessionID: "s9",
  prompt: { text: "Role: independent reviewer. Find material defects in the diff." },
};
hook(role);
if (role.prompt.text.includes("[queue] Task ")) {
  throw new Error("role-prompt was queued");
}

const close = { sessionID: "s1", prompt: { text: "/close 20261028-test" } };
hook(close);
const afterClose = { sessionID: "s1", prompt: { text: "Fix the next bug" } };
hook(afterClose);
if (!afterClose.prompt.text.includes("[queue] Task ")) {
  throw new Error("close did not reset the session task marker");
}

rmSync(root, { recursive: true, force: true });
console.log("auto-intake: PASS");

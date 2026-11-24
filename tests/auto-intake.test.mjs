// SPDX-License-Identifier: MIT
import {
  copyFileSync,
  cpSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";

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
const repo = join(root, "repo");
mkdirSync(join(repo, "tests"), { recursive: true });
writeFileSync(
  join(repo, "tests/test_ok.py"),
  "import unittest\n\nclass Ok(unittest.TestCase):\n    def test_ok(self):\n        self.assertTrue(True)\n",
);
writeFileSync(join(repo, ".gitignore"), "__pycache__/\n*.pyc\n");
execFileSync("git", ["init", "-q", "-b", "main", repo]);
execFileSync("git", ["-C", repo, "config", "user.email", "test@example.com"]);
execFileSync("git", ["-C", repo, "config", "user.name", "Test"]);
execFileSync("git", ["-C", repo, "add", "-A"]);
execFileSync("git", ["-C", repo, "commit", "-q", "-m", "base"]);
copyFileSync(
  join(here, "..", "bin", "tasks.py"),
  join(root, "bin/tasks.py"),
);

process.env.HARNESS_HOME = join(here, "..");
process.env.AUTO_INTAKE_ROOT = root;
process.env.AUTO_INTAKE_TASKS = join(root, "bin", "tasks.py");
process.env.AUTO_INTAKE = "on";
const { default: plugin, PLAYBOOK_IDS, routePrompt, validateWorkflow } =
  await import(
    new URL(`../plugins/auto-intake.js?test=${process.pid}`, import.meta.url)
  );

function taskFiles() {
  return readdirSync(join(root, "work/tasks")).filter((name) =>
    name.endsWith(".md"),
  );
}

function tempHome(label) {
  const home = join(root, `home-${label}`);
  mkdirSync(join(home, "skills"), { recursive: true });
  cpSync(
    join(here, "..", "skills", "engineering-loop"),
    join(home, "skills", "engineering-loop"),
    { recursive: true },
  );
  return home;
}

async function hookFor(home) {
  const previous = process.env.HARNESS_HOME;
  process.env.HARNESS_HOME = home;
  let callback;
  await plugin.setup({
    location: { directory: "/tmp/example-project" },
    session: { hook: async (_name, registered) => { callback = registered; } },
  });
  process.env.HARNESS_HOME = previous;
  if (!callback) throw new Error(`prompt hook not registered for ${home}`);
  return callback;
}

function assertBlocked(text, label) {
  if (!text.includes("[workflow] BLOCKED")) {
    throw new Error(`${label}: blocked workflow notice missing`);
  }
  if (!text.includes("no task was created")) {
    throw new Error(`${label}: blocked notice does not say no task was created`);
  }
  if (text.includes("[queue] Task ")) {
    throw new Error(`${label}: blocked notice created or claimed a task`);
  }
  for (const id of PLAYBOOK_IDS) {
    if (new RegExp(`\\b${id}\\b`).test(text)) {
      throw new Error(`${label}: blocked notice claimed playbook ${id}`);
    }
  }
}

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
if (
  !first.prompt.text.includes("engineering-loop") ||
  !first.prompt.text.includes("playbook: bug-fix") ||
  !first.prompt.text.includes("Data shape") ||
  !first.prompt.text.includes("work in this turn") ||
  !first.prompt.text.includes("ship") ||
  !first.prompt.text.includes("human gates") ||
  first.prompt.text.includes("/intake")
) {
  throw new Error("queue notice does not route through the loop to the human gates");
}
if (first.prompt.text.includes("goal")) {
  throw new Error("single-step route preloaded the goal skill");
}
const id = first.prompt.text.match(/Task ([^\s]+)/)?.[1];
if (!id) throw new Error("task id missing");
const task = readFileSync(join(root, "work/tasks", `${id}.md`), "utf8");
if (!task.includes("status: inbox")) throw new Error("task not inbox");
if (!task.includes("example-project")) throw new Error("project not inferred");
if (task.includes("use /goal")) throw new Error("task scope still requires /goal");
if (!task.includes("confirm scope and acceptance")) {
  throw new Error("task scope does not state the acceptance confirmation");
}


const cases = [
  ["How does auto-intake route prompts?", "investigation", false, false, ["engineering-loop"]],
  ["Investigate why the cache entry survives logout, do not edit code", "investigation", false, false, ["engineering-loop"]],
  ["Fix the login redirect bug", "bug-fix", false, false, ["engineering-loop"]],
  ["Correct the login redirect bug", "bug-fix", false, false, ["engineering-loop"]],
  ["Explain why cache expires and fix the refresh bug", "bug-fix", false, false, ["engineering-loop"]],
  ["Explain how lock contention works and add a retry flag", "feature", false, false, ["engineering-loop"]],
  ["Refactor the parser into pure functions without changing behavior", "refactoring", false, false, ["engineering-loop"]],
  ["Board generation takes 2 seconds on 100 tasks, profile and speed it up", "perf", false, false, ["engineering-loop"]],
  ["Hillclimb parser throughput toward 50k lines/sec, commit only measured wins", "hillclimb", false, false, ["engineering-loop"]],
  ["Going to bed, run a multi-phase migration until done", "autonomous-multiphase", false, true, ["engineering-loop", "goal"]],
  ["Use the refactoring playbook to simplify the parser", "refactoring", true, false, ["engineering-loop"]],
  ["Run the correct playbook on repeated mistakes", "correct", true, false, ["engineering-loop"]],
  ["Use the banana playbook to fix login", "bug-fix", false, false, ["engineering-loop"]],
  ["Investigate why the login redirect fails", "investigation", false, false, ["engineering-loop"]],
  ["Fix the login bug; the goal is to make it fast", "bug-fix", false, false, ["engineering-loop"]],
  ["Write a report on the phases of the moon", "feature", false, false, ["engineering-loop"]],
  ["Refactor the parser to fix the crash", "bug-fix", false, false, ["engineering-loop"]],
  ["Investigate the slow login and fix it", "bug-fix", false, false, ["engineering-loop"]],
  ["Repair the broken login", "bug-fix", false, false, ["engineering-loop"]],
  ["Debug the login failure", "bug-fix", false, false, ["engineering-loop"]],
  ["Investigate the slow login", "investigation", false, false, ["engineering-loop"]],
  ["Investigate the parser refactoring options", "investigation", false, false, ["engineering-loop"]],
  ["Move the parser into a separate module", "refactoring", false, false, ["engineering-loop"]],
  ["Extract the helper function", "refactoring", false, false, ["engineering-loop"]],
  ["Inline the accessor", "refactoring", false, false, ["engineering-loop"]],
  ["Consolidate the two parsers", "refactoring", false, false, ["engineering-loop"]],
  ["Refactoring the parser", "refactoring", false, false, ["engineering-loop"]],
  ["What is the bug in the parser?", "investigation", false, false, ["engineering-loop"]],
  ["Investigate the parser and extract the helper", "refactoring", false, false, ["engineering-loop"]],
  ["Investigate the parser and move the code", "refactoring", false, false, ["engineering-loop"]],
  ["Investigate the parser to extract the helper", "refactoring", false, false, ["engineering-loop"]],
];
for (const [prompt, playbook, userNamed, multiStep, skills] of cases) {
  const decision = routePrompt(prompt);
  const want = { playbook, userNamed, multiStep, skills };
  for (const [key, value] of Object.entries(want)) {
    if (JSON.stringify(decision[key]) !== JSON.stringify(value)) {
      throw new Error(`${prompt}: ${key}=${JSON.stringify(decision[key])}, want ${JSON.stringify(value)}`);
    }
  }
}
if (routePrompt("Going to bed, run a multi-phase migration until done").skills.includes("goal") !== true) {
  throw new Error("multi-step route did not load the goal skill");
}

const second = { sessionID: "s1", prompt: { text: "Add another endpoint" } };
hook(second);
if (second.prompt.text.includes("[queue] Task ")) {
  throw new Error("duplicate task created for one session");
}

const beforeReuse = taskFiles().length;
const otherSession = {
  sessionID: "s4",
  prompt: { text: "Fix the login redirect bug" },
};
hook(otherSession);
if (!otherSession.prompt.text.includes("Existing task")) {
  throw new Error("same prompt in a new session did not reuse the task");
}
if (!otherSession.prompt.text.includes("engineering-loop")) {
  throw new Error("reused-task notice did not route through engineering-loop");
}
if (!otherSession.prompt.text.includes("playbook: bug-fix")) {
  throw new Error("reused-task notice did not name the validated playbook");
}
if (taskFiles().length !== beforeReuse) {
  throw new Error("reused-task notice created a duplicate task");
}
const afterOther = readFileSync(join(root, "work/tasks", `${id}.md`), "utf8");
if (!afterOther.includes("status: inbox")) throw new Error("task changed");

// A queue-helper failure is route-only: no task id, no playbook id.
const helperBefore = taskFiles().length;
rmSync(join(root, "bin/tasks.py"));
const helperFailure = {
  sessionID: "s-helper-failure",
  prompt: { text: "Fix the broken helper path" },
};
hook(helperFailure);
if (!helperFailure.prompt.text.includes("[workflow]")) {
  throw new Error("helper failure did not append a workflow notice");
}
if (!helperFailure.prompt.text.includes("engineering-loop")) {
  throw new Error("helper failure did not name engineering-loop");
}
if (!helperFailure.prompt.text.includes("no task was created")) {
  throw new Error("helper failure did not say no task was created");
}
if (helperFailure.prompt.text.includes("[queue] Task ")) {
  throw new Error("helper failure claimed a task");
}
for (const playbookId of PLAYBOOK_IDS) {
  if (new RegExp(`\\b${playbookId}\\b`).test(helperFailure.prompt.text)) {
    throw new Error(`helper failure named playbook ${playbookId}`);
  }
}
if (taskFiles().length !== helperBefore) {
  throw new Error("helper failure created a task file");
}
copyFileSync(join(here, "..", "bin", "tasks.py"), join(root, "bin/tasks.py"));

// Invalid setup fails closed before creating a task or naming a playbook.
const invalidCases = [];

const missingHome = join(root, "home-missing");
mkdirSync(missingHome, { recursive: true });
invalidCases.push(["missing skill", missingHome]);

const renamedHome = tempHome("renamed");
writeFileSync(
  join(renamedHome, "skills/engineering-loop/SKILL.md"),
  readFileSync(join(renamedHome, "skills/engineering-loop/SKILL.md"), "utf8")
    .replace(/^name: engineering-loop$/m, "name: engineering-loop-broken"),
);
invalidCases.push(["wrong skill name", renamedHome]);

const sectionHome = tempHome("section");
const playbookPath = join(
  sectionHome,
  "skills/engineering-loop/references/playbooks.md",
);
const playbookText = readFileSync(playbookPath, "utf8");
const sectionEnd = playbookText.indexOf("\n## ", playbookText.indexOf("## feature"));
const withoutFeature =
  playbookText.slice(0, playbookText.indexOf("## feature")) +
  playbookText.slice(sectionEnd + 1);
writeFileSync(playbookPath, withoutFeature);
invalidCases.push(["missing playbook section", sectionHome]);

for (const [label, home] of invalidCases) {
  const before = taskFiles().length;
  const workflow = validateWorkflow(home);
  if (workflow.ok) throw new Error(`${label}: validation unexpectedly passed`);
  const invalidHook = await hookFor(home);
  const event = {
    sessionID: `s-invalid-${label.replaceAll(" ", "-")}`,
    prompt: { text: "Fix the login redirect bug" },
  };
  invalidHook(event);
  assertBlocked(event.prompt.text, label);
  if (taskFiles().length !== before) {
    throw new Error(`${label}: invalid setup created a task file`);
  }
}

// The inbox template starts with an unchecked acceptance. A finishing agent
// must replace it with the concrete, checked criterion before `done`.
const taskPath = join(root, "work/tasks", `${id}.md`);
writeFileSync(
  taskPath,
  readFileSync(taskPath, "utf8")
    .replace(/^- \[ \] TBD.*$/m, "- [x] login redirect is fixed")
    .replace(
      /## Plan\n\n/,
      '## Plan\n\nData shape: {"state":"idle|running"}\n' +
        "Verify: python3 -m unittest tests.test_ok -v\n\n",
    ),
);
taskCli("claim", id, "--owner", "test");
taskCli(
  "review",
  id,
  "--repo",
  repo,
  "--run",
  "python3 -m unittest tests.test_ok -v",
);
taskCli(
  "status",
  id,
  "done",
  "--evidence",
  "python3 -m unittest: PASS",
  "--repo",
  repo,
);
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
    text: "Task may be complete. Run /close when you are done: final /review if needed, review artifact, evidence.",
  },
};
hook(closeNudge);
if (closeNudge.prompt.text.includes("[queue] Task ")) {
  throw new Error("close nudge was queued as a task");
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

// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import {
  appendFileSync,
  chmodSync,
  existsSync,
  mkdtempSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const state = mkdtempSync(join(tmpdir(), "libreharness-plugin-"));
const work = mkdtempSync(join(tmpdir(), "libreharness-tools-"));
const slowRepo = mkdtempSync(join(tmpdir(), "libreharness-slow-"));
chmodSync(state, 0o755);
const commands = [];
const skills = [];
const tools = [];
const prompts = [];
const hooks = [];
const subscriptions = [];
const agentIds = ["explore", "implementer", "integrator", "devils-advocate"];
const baseAgents = new Map(
  agentIds.map((id) => [
    id,
    {
      id,
      name: id,
      description: "",
      system: "",
      mode: "subagent",
      permissions: [],
      hidden: false,
      request: { settings: {}, headers: {}, body: {} },
      model: { providerID: "commandcode", id: "deepseek-v4-flash" },
    },
  ]),
);
const updatedAgents = new Map();

const ctx = {
  options: {
    state,
    agentModels: { explore: "example/workhorse#high" },
  },
  location: { directory: process.cwd() },
  tool: {
    transform: (callback) => callback({ add: (tool) => tools.push(tool) }),
  },
  command: {
    transform: (callback) => callback({ add: (command) => commands.push(command) }),
  },
  agent: {
    transform: (callback) =>
      callback({
        // Config-defined agents are not visible to get(), but update(id) still
        // applies. Do not gate updates on get().
        get: () => undefined,
        update: (id, update) => {
          const agent = baseAgents.get(id);
          assert.ok(agent, `unexpected agent update: ${id}`);
          update(agent);
          updatedAgents.set(id, agent);
        },
      }),
  },
  skill: {
    transform: (callback) => callback({ add: (skill) => skills.push(skill) }),
  },
  session: {
    hook: (name, callback) => {
      hooks.push(name);
    },
    prompt: async (prompt) => prompts.push(prompt),
  },
  event: {
    subscribe: (options) => {
      subscriptions.push(options?.types ?? []);
      return (async function* () {})();
    },
  },
};

const { default: plugin, modelRef, statePath } = await import(
  "../src/plugin.js"
);
assert.equal(plugin.id, "libreharness");
assert.deepEqual(modelRef("provider/model"), {
  providerID: "provider",
  id: "model",
});
assert.deepEqual(modelRef("provider/model#high"), {
  providerID: "provider",
  id: "model",
  variant: "high",
});
assert.equal(modelRef("model-only"), null);
assert.equal(modelRef("provider/"), null);
assert.equal(modelRef("provider/model#"), null);

const previousState = process.env.HARNESS_STATE;
process.env.HARNESS_STATE = "/tmp/ignored-by-default";
assert.equal(
  statePath(undefined),
  join(process.env.HOME, ".local/state/libreharness"),
  "the plugin must default to a normal state directory, not HARNESS_STATE",
);
assert.equal(statePath("~/custom"), join(process.env.HOME, "custom"));
if (previousState === undefined) delete process.env.HARNESS_STATE;
else process.env.HARNESS_STATE = previousState;
const cleanup = await plugin.setup(ctx);
for (const name of ["comment_audit", "tasks", "pr_guard"]) {
  assert.ok(tools.some((tool) => tool.name === name), `missing tool ${name}`);
}

const audit = tools.find((tool) => tool.name === "comment_audit");
writeFileSync(join(work, "dirty.py"), "# TODO: remove\n");
await assert.rejects(() => audit.execute({ paths: ["dirty.py"], cwd: work }));
writeFileSync(join(work, "clean.py"), "# SPDX-License-Identifier: MIT\n");
const clean = await audit.execute({ paths: ["clean.py"], cwd: work });
assert.match(clean.content, /PASS/);
execFileSync("git", ["init", "-q"], { cwd: work });
execFileSync("git", ["add", "clean.py", "dirty.py"], { cwd: work });
writeFileSync(join(work, "new.py"), "# TODO: new\n");
await assert.rejects(() => audit.execute({ untracked: true, cwd: work }));

const taskTool = tools.find((tool) => tool.name === "tasks");
const listed = await taskTool.execute({ args: ["list"], cwd: process.cwd() });
assert.equal(typeof listed.content, "string");

const guard = tools.find((tool) => tool.name === "pr_guard");
const help = await guard.execute({ args: ["--help"], cwd: process.cwd() });
assert.match(help.content, /usage/i);

writeFileSync(
  join(slowRepo, "slow_test.py"),
  "import time\nimport unittest\n\nclass Slow(unittest.TestCase):\n    def test_slow(self):\n        time.sleep(1)\n        self.assertTrue(True)\n",
);
execFileSync("git", ["init", "-q"], { cwd: slowRepo });
execFileSync("git", ["add", "slow_test.py"], { cwd: slowRepo });
execFileSync(
  "git",
  ["-c", "user.name=Test", "-c", "user.email=test@example.test", "commit", "-qm", "base"],
  { cwd: slowRepo },
);
const created = await taskTool.execute({
  args: [
    "new",
    "Slow check",
    "--project",
    "demo",
    "--status",
    "ready",
    "--scope",
    "Prove the tool does not block the event loop.",
    "--acceptance",
    "- [ ] slow check",
  ],
  cwd: slowRepo,
});
const slowId = created.content.trim();
appendFileSync(
  join(state, "work", "tasks", `${slowId}.md`),
  '\n## Plan\n\nData shape: {"slow":"string"}\nVerify: python3 -m unittest slow_test\n',
);
await taskTool.execute({ args: ["claim", slowId, "--owner", "test"], cwd: slowRepo });
let ticks = 0;
const timer = setInterval(() => {
  ticks += 1;
}, 20);
const started = Date.now();
const reviewed = await taskTool.execute({
  args: ["review", slowId, "--run", "python3 -m unittest slow_test"],
  cwd: slowRepo,
});
const elapsed = Date.now() - started;
clearInterval(timer);
assert.ok(elapsed >= 900, `slow review returned too quickly: ${elapsed}ms`);
assert.ok(ticks >= 5, `tool call blocked the event loop (${ticks} ticks in ${elapsed}ms)`);
assert.match(reviewed.content, /PASS/);

const controller = new AbortController();
setTimeout(() => controller.abort(), 100);
await assert.rejects(
  taskTool.execute(
    { args: ["review", slowId, "--run", "python3 -m unittest slow_test"], cwd: slowRepo },
    { signal: controller.signal },
  ),
  /abort/i,
);

const commandNames = commands.map((command) => command.name);
for (const name of ["goal", "review", "state-audit", "tune", "close", "unslop-ui"]) {
  assert.ok(commandNames.includes(name), `missing command ${name}`);
}

const stateAudit = commands.find((command) => command.name === "state-audit");
await stateAudit.execute({
  sessionID: "ses_test",
  prompt: { text: "src/" },
  delivery: "steer",
});
assert.equal(prompts.length, 1);
assert.equal(prompts[0].sessionID, "ses_test");
assert.match(prompts[0].text, /src\//);
assert.match(prompts[0].text, /state-audit/);
// SessionApi.prompt takes SessionPromptInput: a flat { sessionID, text,
// delivery }, not a nested { prompt } object.
assert.equal(prompts[0].prompt, undefined);
assert.equal(prompts[0].delivery, "steer");

const unslop = commands.find((command) => command.name === "unslop-ui");
await unslop.execute({
  sessionID: "ses_test",
  prompt: { text: "Apps" },
  delivery: "steer",
});
assert.equal(prompts.length, 2);
assert.match(prompts[1].text, /Apps/);
assert.match(prompts[1].text, /only operator stop is choosing A or B/);
assert.match(prompts[1].text, /Reply A or B/);

for (const id of agentIds) {
  assert.ok(updatedAgents.has(id), `agent was not updated: ${id}`);
}
const explore = updatedAgents.get("explore");
assert.match(explore.description, /Read-only repository scout/);
assert.ok(explore.system.length > 100);
assert.ok(explore.permissions.length > 0);
assert.ok(
  explore.permissions.some(
    (rule) =>
      rule.action === "read" && rule.resource === "*" && rule.effect === "allow",
  ),
  "explore must allow reads",
);
assert.deepEqual(explore.model, {
  providerID: "example",
  id: "workhorse",
  variant: "high",
});
assert.deepEqual(updatedAgents.get("implementer").model, {
  providerID: "commandcode",
  id: "deepseek-v4-flash",
});

const engineeringLoop = skills.find((skill) => skill.id === "engineering-loop");
assert.ok(engineeringLoop, "engineering-loop must load through ctx.skill.transform");
assert.equal(engineeringLoop.name, "engineering-loop");
assert.ok(engineeringLoop.content.length > 0, "engineering-loop body is empty");
assert.ok(existsSync(engineeringLoop.path), "engineering-loop path is missing");

for (const id of ["state-audit", "verification", "engineering-loop"]) {
  assert.ok(skills.some((skill) => skill.id === id), `missing skill ${id}`);
}

for (const id of ["implementer", "integrator", "devils-advocate"]) {
  const agent = updatedAgents.get(id);
  assert.ok(
    agent.permissions.some(
      (rule) =>
        rule.action === "shell" &&
        rule.resource === "*" &&
        rule.effect === "allow",
    ),
    `${id} must allow shell commands without a prompt`,
  );
}
const devils = updatedAgents.get("devils-advocate");
assert.ok(
  devils.permissions.some(
    (rule) => rule.action === "edit" && rule.effect === "deny",
  ),
  "devils-advocate must remain read-only",
);
assert.ok(
  devils.permissions.some(
    (rule) =>
      rule.action === "edit" &&
      rule.resource === "/tmp/*" &&
      rule.effect === "allow",
  ),
  "devils-advocate must write review artifacts under /tmp without a prompt",
);
assert.ok(
  devils.permissions.some(
    (rule) =>
      rule.action === "webfetch" &&
      rule.resource === "*" &&
      rule.effect === "allow",
  ),
  "devils-advocate must fetch references without a prompt",
);
for (const resource of [
  "rm -rf*",
  "sudo *",
  "git reset --hard*",
  "git clean*",
  "git checkout*",
  "npm publish*",
  "pnpm publish*",
]) {
  assert.ok(
    devils.permissions.some(
      (rule) =>
        rule.action === "shell" &&
        rule.resource === resource &&
        rule.effect === "deny",
    ),
    `devils-advocate must deny ${resource}`,
  );
}

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
assert.equal(process.env.HARNESS_HOME, root);
assert.equal(process.env.HARNESS_STATE, state);
assert.equal(
  statSync(state).mode & 0o777,
  0o700,
  "setup must tighten an existing state directory to mode 700",
);

assert.ok(
  !hooks.includes("context"),
  "native instruction discovery owns AGENTS.md; the plugin must not register a context hook",
);

assert.ok(hooks.includes("prompt"), "auto-intake prompt hook missing");
assert.ok(
  subscriptions.some((types) => types.includes("session.idle")),
  "goal-watch subscription missing",
);

cleanup();
rmSync(state, { recursive: true, force: true });
rmSync(work, { recursive: true, force: true });
rmSync(slowRepo, { recursive: true, force: true });
console.log("plugin: PASS");

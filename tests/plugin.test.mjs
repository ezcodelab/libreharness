// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { chmodSync, existsSync, mkdtempSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const state = mkdtempSync(join(tmpdir(), "libreharness-plugin-"));
chmodSync(state, 0o755);
const commands = [];
const skills = [];
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

const commandNames = commands.map((command) => command.name);
for (const name of ["goal", "review", "state-audit", "tune", "close"]) {
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
console.log("plugin: PASS");

// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const state = mkdtempSync(join(tmpdir(), "libreharness-plugin-"));
const commands = [];
const agents = [];
const skills = [];
const prompts = [];
let contextHook;

const ctx = {
  options: { state },
  command: {
    transform: (callback) => callback({ add: (command) => commands.push(command) }),
  },
  agent: {
    transform: (callback) =>
      callback({
        get: () => undefined,
        add: (agent) => agents.push(agent),
        update: () => {},
      }),
  },
  skill: {
    transform: (callback) => callback({ add: (skill) => skills.push(skill) }),
  },
  session: {
    hook: (name, callback) => {
      if (name === "context") contextHook = callback;
    },
    prompt: async (prompt) => prompts.push(prompt),
  },
};

const { default: plugin } = await import("../src/plugin.js");
assert.equal(plugin.id, "libreharness");
await plugin.setup(ctx);

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

for (const id of ["explore", "implementer", "integrator", "devils-advocate"]) {
  assert.ok(agents.some((agent) => agent.id === id), `missing agent ${id}`);
}
const explore = agents.find((agent) => agent.id === "explore");
assert.match(explore.description, /Read-only repository scout/);
assert.ok(explore.system.length > 100);
assert.ok(explore.permissions.length > 0);

for (const id of ["state-audit", "verification", "engineering-loop"]) {
  assert.ok(skills.some((skill) => skill.id === id), `missing skill ${id}`);
}

const root = resolve(fileURLToPath(new URL("..", import.meta.url)));
assert.equal(process.env.HARNESS_HOME, root);
assert.equal(process.env.HARNESS_STATE, state);

const system = [];
contextHook({ system });
assert.ok(system.some((part) => part.text.includes("## Task scale")));

rmSync(state, { recursive: true, force: true });
console.log("plugin: PASS");

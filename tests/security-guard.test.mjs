// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const { default: plugin, scanText } = await import(
  new URL(`../plugins/security-guard.js?test=${process.pid}`, import.meta.url)
);

const bad = [
  ["yaml-unsafe-load", "config = yaml.load(stream)\n"],
  ["pickle-load", "obj = cPickle.loads(blob)\n"],
  ["torch-load", "model = torch.load('checkpoint.pt')\n"],
  ["html-assignment", "element.innerHTML=userInput;\n"],
  ["child-process-exec", "child_process.exec(command)\n"],
  [
    "actions-injection",
    "jobs:\n  test:\n    steps:\n      - run: echo ${{ github.event.issue.title }}\n",
  ],
];
for (const [id, text] of bad) {
  const found = scanText(text);
  assert.ok(found.includes(id), `${id} not found: ${JSON.stringify(found)}`);
}

const safe = [
  "yaml.safe_load(stream)",
  "pickle.dump(obj, file)",
  "torch.load('checkpoint.pt', weights_only = True)",
  "element.textContent = 'innerHTML'",
  "child_process.execFile('git', args)",
  "on:\n  pull_request:\n    steps:\n      - run: echo ${{ github.sha }}\n",
];
for (const text of safe) {
  assert.deepEqual(scanText(text), [], `false positive: ${text}`);
}

assert.deepEqual(
  scanText("config = yaml.load(stream) # security-guard: allow because trusted"),
  [],
  "blanket allow escape did not suppress",
);
assert.deepEqual(
  scanText(
    "a = yaml.load(stream)\nb = pickle.loads(blob)\n# security-guard: allow yaml-unsafe-load because trusted\n",
  ),
  ["pickle-load"],
  "rule-specific allow did not narrow the suppression",
);

let handler;
const disposers = [];
const ctx = {
  tool: {
    hook: async (name, callback) => {
      assert.equal(name, "execute.after");
      handler = callback;
      return { dispose: () => disposers.push("disposed") };
    },
  },
};
const dispose = await plugin.setup(ctx);
assert.equal(typeof handler, "function", "execute.after not registered");
assert.equal(typeof dispose, "function", "setup did not return a dispose function");

const badEvent = {
  tool: "edit",
  input: {
    path: "app.py",
    oldString: "",
    newString: "import yaml\nconfig = yaml.load(stream)\n",
  },
  result: {
    output: { operation: "write", target: "app.py" },
    content: [{ type: "text", text: "Created file successfully: app.py" }],
  },
};
await handler(badEvent);
const warningText = badEvent.result.content.map((part) => part.text).join("\n");
assert.match(warningText, /\[security-guard\]/);
assert.match(warningText, /yaml-unsafe-load/);
assert.match(warningText, /security-guard: allow <rule-id> because/);
assert.deepEqual(badEvent.result.output, { operation: "write", target: "app.py" });

await handler(badEvent);
assert.equal(
  badEvent.result.content.filter((part) => part.text?.includes("[security-guard]")).length,
  1,
  "warning duplicated",
);

// Shape captured from OpenCode 2.2.1 execute.after on a real write call.
const fixture = JSON.parse(
  readFileSync(new URL("./fixtures/security-guard-event.json", import.meta.url), "utf8"),
);
const fixtureEvent = JSON.parse(JSON.stringify(fixture));
await handler(fixtureEvent);
assert.match(
  fixtureEvent.result.content.map((part) => part.text).join("\n"),
  /\[security-guard\].*yaml-unsafe-load/,
  "real-shape fixture did not produce a warning",
);

const cleanEvent = {
  tool: "write",
  input: { path: "safe.py", content: "value = yaml.safe_load(stream)\n" },
  result: {
    output: { operation: "write", target: "safe.py" },
    content: [{ type: "text", text: "Created file successfully: safe.py" }],
  },
};
const cleanBefore = JSON.stringify(cleanEvent.result);
await handler(cleanEvent);
assert.equal(JSON.stringify(cleanEvent.result), cleanBefore, "clean result changed");

const shellEvent = {
  tool: "bash",
  args: { command: "python -c 'import pickle; pickle.loads(blob)'" },
  result: { title: "Shell", output: "ok", metadata: {} },
};
const shellBefore = JSON.stringify(shellEvent.result);
await handler(shellEvent);
assert.equal(JSON.stringify(shellEvent.result), shellBefore, "non-mutating tool changed");

const stringEvent = {
  tool: "patch",
  args: { patch: "--- a/x\n+++ b/x\n+element.innerHTML = value\n" },
  result: "Applied patch",
};
await handler(stringEvent);
assert.match(stringEvent.result, /\[security-guard\].*html-assignment/);

const broken = {
  tool: {
    hook: async () => {
      throw new Error("hooks unavailable");
    },
  },
};
await plugin.setup(broken);

dispose();
assert.deepEqual(disposers, ["disposed"]);

console.log("security-guard: PASS");

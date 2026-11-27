// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import {
  appendFileSync,
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const state = mkdtempSync(join(tmpdir(), "libreharness-mcp-state-"));
const repo = mkdtempSync(join(tmpdir(), "libreharness-mcp-repo-"));
mkdirSync(join(repo, "tests"), { recursive: true });
writeFileSync(
  join(repo, "tests", "test_slow.py"),
  "import time\nimport unittest\n\nclass Slow(unittest.TestCase):\n    def test_slow(self):\n        time.sleep(5)\n",
);
const child = spawn(process.execPath, [join(ROOT, "bin", "libreharness.js"), "mcp"], {
  cwd: repo,
  env: {
    ...process.env,
    HARNESS_STATE: state,
    PYTHONDONTWRITEBYTECODE: "1",
  },
  stdio: ["pipe", "pipe", "pipe"],
});
child.stdout.setEncoding("utf8");
child.stderr.setEncoding("utf8");
let stderr = "";
let buffer = "";
let nextId = 1;
const pending = new Map();
child.stderr.on("data", (chunk) => {
  stderr += chunk;
});
child.stdout.on("data", (chunk) => {
  buffer += chunk;
  let newline = buffer.indexOf("\n");
  while (newline >= 0) {
    const line = buffer.slice(0, newline).trim();
    buffer = buffer.slice(newline + 1);
    newline = buffer.indexOf("\n");
    if (!line) continue;
    let message;
    try {
      message = JSON.parse(line);
    } catch {
      throw new Error(`MCP wrote non-JSON stdout: ${line}`);
    }
    if (message.id !== undefined && pending.has(message.id)) {
      const { resolve, reject } = pending.get(message.id);
      pending.delete(message.id);
      if (message.error) reject(new Error(JSON.stringify(message.error)));
      else resolve(message.result);
    }
  }
});
child.on("exit", (code) => {
  for (const { reject } of pending.values()) {
    reject(new Error(`MCP exited ${code}: ${stderr.trim()}`));
  }
  pending.clear();
});

function send(message) {
  child.stdin.write(`${JSON.stringify(message)}\n`);
}

function request(method, params = {}) {
  const id = nextId++;
  const result = new Promise((resolve, reject) => {
    pending.set(id, { resolve, reject });
  });
  send({ jsonrpc: "2.0", id, method, params });
  return result;
}

function notify(method, params = {}) {
  send({ jsonrpc: "2.0", method, params });
}

try {
  const initialized = await request("initialize", {
    protocolVersion: "2025-11-25",
    capabilities: {},
    clientInfo: { name: "libreharness-test", version: "1" },
  });
  assert.equal(initialized.serverInfo.name, "libreharness");
  notify("notifications/initialized");

  const listed = await request("tools/list");
  assert.deepEqual(
    listed.tools.map((tool) => tool.name).sort(),
    ["comment_audit", "pr_guard", "tasks"],
  );

  const tasks = await request("tools/call", {
    name: "tasks",
    arguments: { args: ["list"], cwd: repo },
  });
  assert.equal(tasks.isError, undefined);
  assert.match(tasks.content[0].text, /^(no tasks|id\s+status)/);

  const missing = await request("tools/call", {
    name: "comment_audit",
    arguments: { paths: ["missing.py"], cwd: repo },
  });
  assert.equal(missing.isError, true);
  assert.match(missing.content[0].text, /not a file|missing/i);

  const created = await request("tools/call", {
    name: "tasks",
    arguments: {
      args: [
        "new",
        "Cancelable review",
        "--project",
        "mcp",
        "--status",
        "ready",
        "--scope",
        "Prove MCP cancellation.",
        "--acceptance",
        "- [ ] review is canceled",
      ],
      cwd: repo,
    },
  });
  const id = created.content[0].text.trim();
  appendFileSync(
    join(state, "work", "tasks", `${id}.md`),
    '\n## Plan\n\nData shape: {"state":"idle"}\nVerify: python3 -m unittest tests.test_slow -v\n',
  );
  await request("tools/call", {
    name: "tasks",
    arguments: { args: ["claim", id, "--owner", "mcp-test"], cwd: repo },
  });

  const requestId = nextId;
  const started = Date.now();
  let outcome;
  request("tools/call", {
    name: "tasks",
    arguments: {
      args: ["review", id, "--run", "python3 -m unittest tests.test_slow -v"],
      cwd: repo,
    },
  }).then(
    (value) => {
      outcome = { value };
    },
    (error) => {
      outcome = { error };
    },
  );
  await new Promise((resolve) => setTimeout(resolve, 100));
  notify("notifications/cancelled", {
    requestId,
    reason: "test cancellation",
  });
  await new Promise((resolve) => setTimeout(resolve, 500));

  const ping = await request("ping");
  assert.deepEqual(ping, {});
  assert.ok(outcome, "cancelled request left the operation running");
  assert.ok(Date.now() - started < 4000, "cancelled request waited for the slow check");
  assert.ok(
    outcome.error || outcome.value?.isError,
    "cancelled request reported success",
  );
  console.log("mcp-server: PASS");
} finally {
  child.kill();
  rmSync(state, { recursive: true, force: true });
  rmSync(repo, { recursive: true, force: true });
}

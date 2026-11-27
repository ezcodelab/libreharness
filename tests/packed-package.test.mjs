// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { spawn, spawnSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const root = mkdtempSync(join(tmpdir(), "libreharness-packed-"));
const install = join(root, "install");
const workspace = join(root, "workspace");
const state = join(root, "state");
mkdirSync(install);
mkdirSync(workspace);

function npm(args, options = {}) {
  const result = spawnSync(process.platform === "win32" ? "npm.cmd" : "npm", args, {
    encoding: "utf8",
    ...options,
  });
  assert.equal(result.status, 0, result.stderr || result.stdout);
  return result.stdout;
}

try {
  const packed = Object.values(
    JSON.parse(npm(["pack", "--json", "--pack-destination", root], { cwd: ROOT })),
  )[0];
  const tarball = join(root, packed.filename);
  assert.ok(existsSync(tarball), "npm pack did not produce a tarball");
  npm(
    [
      "install",
      "--ignore-scripts",
      "--no-audit",
      "--no-fund",
      "--no-package-lock",
      tarball,
    ],
    { cwd: install },
  );
  const packageRoot = join(install, "node_modules", "libreharness");
  for (const path of [
    "bin/libreharness.js",
    "bin/tasks.py",
    "bin/comment_audit.py",
    "src/runtime.js",
    "src/tools.js",
    "src/mcp.js",
  ]) {
    assert.ok(existsSync(join(packageRoot, path)), `packed package is missing ${path}`);
  }

  const child = spawn(
    process.execPath,
    [join(packageRoot, "bin", "libreharness.js"), "mcp"],
    {
      cwd: workspace,
      env: {
        ...process.env,
        HARNESS_STATE: state,
        PYTHONDONTWRITEBYTECODE: "1",
      },
      stdio: ["pipe", "pipe", "pipe"],
    },
  );
  child.stdout.setEncoding("utf8");
  let stderr = "";
  let buffer = "";
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
      const message = JSON.parse(line);
      const waiter = pending.get(message.id);
      if (waiter) {
        pending.delete(message.id);
        if (message.error) waiter.reject(new Error(JSON.stringify(message.error)));
        else waiter.resolve(message.result);
      }
    }
  });
  child.on("exit", (code) => {
    for (const waiter of pending.values()) {
      waiter.reject(new Error(`packed MCP exited ${code}: ${stderr.trim()}`));
    }
  });
  let nextId = 1;
  const request = (method, params = {}) => {
    const id = nextId++;
    const result = new Promise((resolve, reject) => {
      pending.set(id, { resolve, reject });
    });
    child.stdin.write(`${JSON.stringify({ jsonrpc: "2.0", id, method, params })}\n`);
    return result;
  };
  try {
    const initialized = await request("initialize", {
      protocolVersion: "2025-11-25",
      capabilities: {},
      clientInfo: { name: "packed-test", version: "1" },
    });
    assert.equal(initialized.serverInfo.name, "libreharness");
    child.stdin.write(
      `${JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" })}\n`,
    );
    const listed = await request("tools/list");
    assert.deepEqual(
      listed.tools.map((tool) => tool.name).sort(),
      ["comment_audit", "pr_guard", "tasks"],
    );
    const called = await request("tools/call", {
      name: "tasks",
      arguments: { args: ["list"] },
    });
    assert.equal(called.isError, undefined);
    assert.match(called.content[0].text, /^no tasks/);
    assert.ok(
      !existsSync(join(workspace, "bin")),
      "packed runtime wrote into or resolved from the workspace",
    );
    console.log("packed-package: PASS");
  } finally {
    child.kill();
  }
} finally {
  rmSync(root, { recursive: true, force: true });
}

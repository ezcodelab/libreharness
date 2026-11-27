#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import { spawnSync } from "node:child_process";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT, resolvePython } from "../src/runtime.js";

JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const python = resolvePython();
const scripts = [
  "src/plugin.js",
  "src/runtime.js",
  "src/tools.js",
  "src/mcp.js",
  "plugins/auto-intake.js",
  "plugins/goal-watch.js",
  "plugins/usage-ledger.js",
  "bin/libreharness.js",
  "bin/sync-plugin-version.mjs",
];
const pythonCheck = spawnSync(
  python.command,
  [...python.prefixArgs, "-m", "compileall", "-q", "bin", "tests"],
  { cwd: ROOT, stdio: "inherit" },
);
if (pythonCheck.status !== 0) process.exit(pythonCheck.status ?? 1);
for (const script of scripts) {
  const result = spawnSync(process.execPath, ["--check", script], {
    cwd: ROOT,
    stdio: "inherit",
  });
  if (result.status !== 0) process.exit(result.status ?? 1);
}
console.log("syntax: PASS");

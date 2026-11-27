#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import { spawn } from "node:child_process";
import { join } from "node:path";
import { ROOT, resolvePython } from "../src/runtime.js";

const COMMANDS = {
  tasks: "tasks.py",
  "comment-audit": "comment_audit.py",
  "pr-guard": "pr_guard.py",
};

async function runMcp() {
  const { main } = await import("../src/mcp.js");
  await main();
}

async function runScript(script, args) {
  const python = resolvePython();
  const child = spawn(
    python.command,
    [...python.prefixArgs, join(ROOT, "bin", script), ...args],
    {
      stdio: "inherit",
      env: {
        ...process.env,
        HARNESS_HOME: ROOT,
        PYTHONDONTWRITEBYTECODE: "1",
      },
    },
  );
  child.on("error", (error) => {
    console.error(`libreharness: ${error.message}`);
    process.exitCode = 1;
  });
  child.on("close", (code, signal) => {
    if (code !== null) process.exitCode = code;
    else console.error(`libreharness: ${script} stopped by ${signal}`);
  });
}

const [command, ...args] = process.argv.slice(2);
if (command === "mcp") {
  runMcp().catch((error) => {
    console.error(`libreharness mcp: ${error?.message ?? error}`);
    process.exitCode = 1;
  });
} else if (COMMANDS[command]) {
  await runScript(COMMANDS[command], args);
} else {
  console.error(
    "usage: libreharness <mcp|tasks|comment-audit|pr-guard> [args...]",
  );
  process.exitCode = 2;
}

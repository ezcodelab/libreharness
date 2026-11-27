#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import { spawn } from "node:child_process";
import { resolvePython } from "../src/runtime.js";

const python = resolvePython();
const child = spawn(python.command, [...python.prefixArgs, ...process.argv.slice(2)], {
  stdio: "inherit",
  env: process.env,
});
child.on("error", (error) => {
  console.error(`libreharness: ${error.message}`);
  process.exitCode = 1;
});
child.on("close", (code, signal) => {
  if (code !== null) process.exitCode = code;
  else console.error(`libreharness: python stopped by ${signal}`);
});

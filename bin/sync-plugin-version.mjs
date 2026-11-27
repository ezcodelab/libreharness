#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import { readFileSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { ROOT } from "../src/runtime.js";

const check = process.argv.includes("--check");
const packageData = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const version = packageData.version;
const manifestPaths = ["plugin.json", ".claude-plugin/plugin.json"];
const mcpPaths = ["mcp.json", ".mcp.json"];

function render(path, update) {
  const absolute = join(ROOT, path);
  const data = JSON.parse(readFileSync(absolute, "utf8"));
  update(data);
  return { absolute, text: `${JSON.stringify(data, null, 2)}\n` };
}

const targets = [];
for (const path of manifestPaths) {
  targets.push(
    render(path, (data) => {
      data.version = version;
    }),
  );
}
for (const path of mcpPaths) {
  targets.push(
    render(path, (data) => {
      const server = data.mcpServers?.libreharness;
      if (!server || !Array.isArray(server.args)) {
        throw new Error(`${path}: missing libreharness MCP server args`);
      }
      server.args = server.args.map((argument) =>
        argument.startsWith("libreharness@") ? `libreharness@${version}` : argument,
      );
    }),
  );
}

const drift = targets.filter(
  (target) => readFileSync(target.absolute, "utf8") !== target.text,
);
if (check) {
  if (drift.length) {
    console.error(
      `plugin version drift: expected ${version} in ${drift
        .map((target) => target.absolute.slice(ROOT.length + 1))
        .join(", ")}`,
    );
    process.exitCode = 1;
  } else {
    console.log(`plugin versions: PASS (${version})`);
  }
} else {
  for (const target of targets) writeFileSync(target.absolute, target.text);
  console.log(`plugin versions synchronized: ${version}`);
}

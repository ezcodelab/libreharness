// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const read = (path) => JSON.parse(readFileSync(join(ROOT, path), "utf8"));
const pkg = read("package.json");
const plugin = read("plugin.json");
const claude = read(".claude-plugin/plugin.json");
const claudeMarket = read(".claude-plugin/marketplace.json");
const cursorMarket = read(".cursor-plugin/marketplace.json");
const mcp = read("mcp.json");
const claudeMcp = read(".mcp.json");

assert.equal(
  plugin.$schema,
  "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json",
);
assert.equal(plugin.name, "libreharness");
assert.equal(mcp.$schema, "https://agent-plugins.org/schemas/1.0.0/mcp.schema.json");
assert.equal(plugin.version, pkg.version);
assert.equal(claude.version, pkg.version);
for (const config of [mcp, claudeMcp]) {
  assert.deepEqual(config.mcpServers.libreharness.args.slice(0, 4), [
    "--yes",
    "--package",
    `libreharness@${pkg.version}`,
    "libreharness",
  ]);
  assert.equal(config.mcpServers.libreharness.command, "npx");
}
assert.deepEqual(mcp.mcpServers, {
  libreharness: {
    type: "stdio",
    ...claudeMcp.mcpServers.libreharness,
  },
});
assert.equal(claude.commands.length, 0);
assert.equal(claude.agents.length, 0);

for (const [name, data] of [
  ["plugin", plugin],
  ["claude", claude],
]) {
  assert.equal(data.name, "libreharness", `${name} manifest name`);
  assert.ok(data.description, `${name} manifest description`);
  assert.ok(data.license, `${name} manifest license`);
  assert.ok(data.repository, `${name} manifest repository`);
}
for (const market of [claudeMarket, cursorMarket]) {
  assert.equal(market.name, "libreharness");
  assert.equal(market.plugins.length, 1);
  assert.equal(market.plugins[0].name, "libreharness");
}
assert.equal(claudeMarket.plugins[0].source, "./");
assert.equal(cursorMarket.plugins[0].source, ".");

const skills = readdirSync(join(ROOT, "skills"), { withFileTypes: true })
  .filter((entry) => entry.isDirectory())
  .map((entry) => entry.name)
  .sort();
for (const name of skills) {
  assert.ok(
    existsSync(join(ROOT, "skills", name, "SKILL.md")),
    `${name} is missing SKILL.md`,
  );
  assert.ok(
    existsSync(join(ROOT, "skills", name, "agents/openai.yaml")),
    `${name} is missing agents/openai.yaml`,
  );
}
for (const name of ["goal", "review", "close"]) {
  assert.ok(skills.includes(name), `missing canonical skill ${name}`);
}
for (const path of [
  "plugin.json",
  "mcp.json",
  ".mcp.json",
  ".claude-plugin/plugin.json",
  ".claude-plugin/marketplace.json",
  ".cursor-plugin/marketplace.json",
  "skills/review/SKILL.md",
  "skills/close/SKILL.md",
]) {
  assert.ok(
    pkg.files.some(
      (entry) => path === entry || path.startsWith(`${entry}/`),
    ),
    `package files do not include ${path}`,
  );
}
console.log("plugin-manifests: PASS");

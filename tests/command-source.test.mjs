// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
for (const name of readdirSync(join(ROOT, "commands"))) {
  if (!name.endsWith(".md")) continue;
  const id = name.slice(0, -3);
  const text = readFileSync(join(ROOT, "commands", name), "utf8");
  assert.match(text, /^---\n[\s\S]*?^skill: ([a-z0-9-]+)$/m, `${name}: missing skill`);
  const skill = text.match(/^skill: ([a-z0-9-]+)$/m)[1];
  assert.equal(skill, id, `${name}: skill must match command name`);
  const body = text.split(/\n---\r?\n/)[1].trim();
  assert.equal(
    body,
    `<!-- SPDX-License-Identifier: MIT -->\nUse the \`${id}\` skill.`,
    `${name}: command contains a divergent procedure`,
  );
  const canonical = readFileSync(join(ROOT, "skills", skill, "SKILL.md"), "utf8");
  assert.ok(canonical.length > 500, `${skill}: canonical procedure is missing`);
}
const plugin = readFileSync(join(ROOT, "src", "plugin.js"), "utf8");
assert.match(plugin, /data\.skill/);
assert.match(plugin, /join\(SKILLS, data\.skill, "SKILL\.md"\)/);
console.log("command-source: PASS");

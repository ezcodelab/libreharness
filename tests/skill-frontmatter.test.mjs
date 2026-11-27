// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const base = join(ROOT, "skills");
const names = new Set();
for (const entry of readdirSync(base, { withFileTypes: true })) {
  if (!entry.isDirectory()) continue;
  const file = join(base, entry.name, "SKILL.md");
  const text = readFileSync(file, "utf8");
  assert.ok(text.startsWith("---\n"), `${file}: missing frontmatter`);
  const end = text.indexOf("\n---", 4);
  assert.ok(end > 0, `${file}: unterminated frontmatter`);
  const data = {};
  for (const line of text.slice(4, end).split(/\r?\n/)) {
    const match = line.match(/^([a-z-]+):\s*(.+)$/);
    if (match) data[match[1]] = match[2].trim();
  }
  assert.match(
    data.name ?? "",
    /^[a-z0-9]+(?:-[a-z0-9]+)*$/,
    `${file}: invalid name`,
  );
  assert.equal(data.name, entry.name, `${file}: name must match directory`);
  assert.ok(data.description, `${file}: missing description`);
  assert.ok(data.description.length <= 1024, `${file}: description is too long`);
  assert.equal(
    data["disable-model-invocation"],
    undefined,
    `${file}: LibreHarness skills must remain model-invoked`,
  );
  assert.ok(!names.has(data.name), `${file}: duplicate skill name`);
  names.add(data.name);

  const metadata = readFileSync(
    join(base, entry.name, "agents", "openai.yaml"),
    "utf8",
  );
  assert.match(metadata, /^interface:\n/m, `${file}: missing Codex interface`);
  assert.match(
    metadata,
    /^ {2}display_name: ".+"$/m,
    `${file}: missing Codex display_name`,
  );
  assert.match(
    metadata,
    /^ {2}short_description: ".+"$/m,
    `${file}: missing Codex short_description`,
  );
}
assert.ok(names.has("engineering-loop"));
console.log("skill-frontmatter: PASS");

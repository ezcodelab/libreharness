#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { existsSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const directory = join(ROOT, "docs", "certification");
const output = join(directory, "SUPPORT.md");
const hosts = ["opencode", "claude", "codex", "cursor", "copilot"];
const systems = ["linux", "darwin", "win32"];
const labels = {
  opencode: "OpenCode",
  claude: "Claude Code",
  codex: "Codex",
  cursor: "Cursor",
  copilot: "GitHub Copilot",
};
const osLabels = { linux: "Linux", darwin: "macOS", win32: "Windows" };
const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const certificates = new Map();

for (const file of readdirSync(directory)) {
  if (!file.endsWith(".json")) continue;
  const path = join(directory, file);
  const data = JSON.parse(readFileSync(path, "utf8"));
  assert.equal(data.schema, 1, `${file}: schema`);
  assert.ok(hosts.includes(data.host), `${file}: host`);
  assert.ok(systems.includes(data.os), `${file}: os`);
  assert.equal(file, `${data.host}-${data.os}.json`, `${file}: filename`);
  assert.ok(data.hostVersion, `${file}: hostVersion`);
  assert.equal(data.libreharnessVersion, pkg.version, `${file}: version`);
  assert.match(data.commit, /^[0-9a-f]{40}$/, `${file}: commit`);
  assert.equal(data.install, "PASS", `${file}: install`);
  assert.deepEqual(data.discovery, { skills: "PASS", tools: "PASS" }, `${file}: discovery`);
  assert.equal(data.toolRoundTrip, "PASS", `${file}: tool round trip`);
  assert.ok(["PASS", "NOT_RUN"].includes(data.journey), `${file}: journey`);
  assert.ok(Array.isArray(data.limitations), `${file}: limitations`);
  if (data.host === "opencode") {
    assert.equal(data.journey, "PASS", `${file}: OpenCode needs a full journey`);
  }
  if (data.journey === "NOT_RUN") {
    assert.ok(
      data.limitations.some((item) =>
        /full engineering workflow has not been certified/i.test(item),
      ),
      `${file}: missing journey limitation`,
    );
  }
  certificates.set(`${data.host}-${data.os}`, data);
}

const lines = [
  "<!-- SPDX-License-Identifier: MIT -->",
  "",
  "# Support matrix",
  "",
  "This file is generated from certificates under `docs/certification/`.",
  "A host and operating-system pair is supported only when its row says",
  "Certified. Standards compatibility alone is not a support claim.",
  "",
  `| Host | ${systems.map((system) => osLabels[system]).join(" | ")} |`,
  `|---|${systems.map(() => "---").join("|")}|`,
];
for (const host of hosts) {
  const cells = systems.map((system) => {
    const certificate = certificates.get(`${host}-${system}`);
    if (!certificate) return "Not certified";
    if (certificate.journey === "PASS") {
      return "Certified: discovery, tool round-trip, full journey";
    }
    return "Certified: discovery, tool round-trip; full journey not certified";
  });
  lines.push(`| ${labels[host]} | ${cells.join(" | ")} |`);
}
lines.push("", "## Recorded limits", "");
let limits = 0;
for (const [key, certificate] of [...certificates.entries()].sort()) {
  const [host, system] = key.split("-");
  for (const limitation of certificate.limitations) {
    lines.push(`- ${labels[host]} ${osLabels[system]}: ${limitation}`);
    limits += 1;
  }
}
if (!limits) lines.push("None.");
lines.push("");
const expected = `${lines.join("\n")}\n`;

if (process.argv.includes("--write")) {
  writeFileSync(output, expected);
  console.log(`support-matrix: wrote docs/certification/SUPPORT.md`);
} else {
  assert.ok(existsSync(output), "docs/certification/SUPPORT.md is missing");
  assert.equal(
    readFileSync(output, "utf8"),
    expected,
    "support matrix is stale; run node tests/support-matrix.test.mjs --write",
  );
  console.log("support-matrix: PASS");
}

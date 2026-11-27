// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
const root = mkdtempSync(join(tmpdir(), "libreharness-certificate-"));
const script = join(ROOT, "tests", "certify-host.mjs");

function run(evidence, output) {
  return spawnSync(
    process.execPath,
    [script, "--evidence", evidence, "--output", output],
    { cwd: ROOT, encoding: "utf8" },
  );
}

function evidence(host, journey = "NOT_RUN") {
  return {
    host,
    hostVersion: "test-version",
    os: process.platform,
    manualProcedure: "docs/certification/manual-procedure.md",
    install: "PASS",
    discovery: { skills: "PASS", tools: "PASS" },
    toolRoundTrip: "PASS",
    journey,
    limitations:
      journey === "NOT_RUN"
        ? ["The full engineering workflow has not been certified on this host."]
        : [],
    commandLog: [
      { command: "native install command", result: "plugin installed" },
      { command: "host tool call", result: "tasks listed" },
    ],
  };
}

try {
  const validEvidence = join(root, "valid.json");
  const validOutput = join(root, "certificate.json");
  writeFileSync(validEvidence, JSON.stringify(evidence("claude")));
  const valid = run(validEvidence, validOutput);
  assert.equal(valid.status, 0, valid.stderr);
  const certificate = JSON.parse(readFileSync(validOutput, "utf8"));
  assert.equal(certificate.schema, 1);
  assert.equal(certificate.host, "claude");
  assert.equal(certificate.os, process.platform);
  assert.equal(certificate.libreharnessVersion, pkg.version);
  assert.match(certificate.commit, /^[0-9a-f]{40}$/);
  assert.equal(certificate.journey, "NOT_RUN");

  const openCodeEvidence = join(root, "opencode.json");
  writeFileSync(openCodeEvidence, JSON.stringify(evidence("opencode")));
  const noJourney = run(openCodeEvidence, join(root, "opencode-certificate.json"));
  assert.equal(noJourney.status, 2);
  assert.match(noJourney.stderr, /requires a passing full journey/);

  const failed = evidence("codex");
  failed.discovery.tools = "FAIL";
  const failedEvidence = join(root, "failed.json");
  writeFileSync(failedEvidence, JSON.stringify(failed));
  const rejected = run(failedEvidence, join(root, "failed-certificate.json"));
  assert.equal(rejected.status, 2);
  assert.match(rejected.stderr, /tool discovery must pass/);

  const missing = run(join(root, "missing.json"), join(root, "missing-certificate.json"));
  assert.equal(missing.status, 2);
  assert.match(missing.stderr, /evidence file is missing/);
  console.log("certificate: PASS");
} finally {
  rmSync(root, { recursive: true, force: true });
}

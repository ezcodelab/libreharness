#!/usr/bin/env node
// SPDX-License-Identifier: MIT
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL("..", import.meta.url));
const HOSTS = new Set(["opencode", "claude", "codex", "cursor", "copilot"]);
const OS = new Set(["linux", "darwin", "win32"]);
const STATUS = new Set(["PASS", "FAIL"]);
const JOURNEY = new Set(["PASS", "FAIL", "NOT_RUN"]);

function argument(name) {
  const index = process.argv.indexOf(name);
  return index >= 0 ? process.argv[index + 1] : undefined;
}

function fail(message) {
  console.error(`certify-host: ${message}`);
  process.exit(2);
}

function oneLine(value, name) {
  if (typeof value !== "string" || !value.trim() || /[\r\n]/.test(value)) {
    fail(`${name} must be a non-empty single line`);
  }
  return value.trim();
}

const evidencePath = argument("--evidence");
if (!evidencePath) fail("--evidence <file> is required");
if (!existsSync(evidencePath)) fail(`evidence file is missing: ${evidencePath}`);
const evidence = JSON.parse(readFileSync(evidencePath, "utf8"));

const host = oneLine(evidence.host, "host");
if (!HOSTS.has(host)) fail(`unknown host: ${host}`);
const hostVersion = oneLine(evidence.hostVersion, "hostVersion");
const client = evidence.client ? oneLine(evidence.client, "client") : undefined;
const os = oneLine(evidence.os, "os");
if (!OS.has(os)) fail(`unknown os: ${os}`);
if (os !== process.platform) {
  fail(`evidence os ${os} does not match this machine ${process.platform}`);
}
if (
  evidence.manualProcedure !== "docs/certification/manual-procedure.md"
) {
  fail("manualProcedure must name docs/certification/manual-procedure.md");
}
if (!STATUS.has(evidence.install)) fail("install must be PASS or FAIL");
if (evidence.install !== "PASS") fail("a failing install cannot be certified");
if (!STATUS.has(evidence.discovery?.skills)) {
  fail("discovery.skills must be PASS or FAIL");
}
if (!STATUS.has(evidence.discovery?.tools)) {
  fail("discovery.tools must be PASS or FAIL");
}
if (evidence.discovery.skills !== "PASS" || evidence.discovery.tools !== "PASS") {
  fail("skill and tool discovery must pass before certification");
}
if (!STATUS.has(evidence.toolRoundTrip)) {
  fail("toolRoundTrip must be PASS or FAIL");
}
if (evidence.toolRoundTrip !== "PASS") {
  fail("a host-driven tool round-trip must pass before certification");
}
const journey = evidence.journey ?? "NOT_RUN";
if (!JOURNEY.has(journey)) fail("journey must be PASS, FAIL, or NOT_RUN");
if (journey === "FAIL") fail("a failing journey cannot be certified");
if (host === "opencode" && journey !== "PASS") {
  fail("OpenCode certification requires a passing full journey");
}
if (!Array.isArray(evidence.limitations)) fail("limitations must be an array");
for (const limitation of evidence.limitations) {
  oneLine(limitation, "limitation");
}
if (
  journey === "NOT_RUN" &&
  !evidence.limitations.some((item) =>
    /full engineering workflow has not been certified/i.test(item),
  )
) {
  fail("a non-journey certificate must record that the full workflow is uncertified");
}
if (!Array.isArray(evidence.commandLog) || evidence.commandLog.length < 2) {
  fail("commandLog must record the install and host tool-call commands");
}
for (const entry of evidence.commandLog) {
  oneLine(entry?.command, "commandLog.command");
  oneLine(entry?.result, "commandLog.result");
}

const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));
let commit;
try {
  commit = execFileSync("git", ["rev-parse", "HEAD"], {
    cwd: ROOT,
    encoding: "utf8",
  }).trim();
} catch {
  fail("certification requires a Git checkout with a recorded commit");
}
if (!/^[0-9a-f]{40}$/.test(commit)) fail("cannot resolve the reviewed commit");

const certificate = {
  schema: 1,
  host,
  hostVersion,
  ...(client ? { client } : {}),
  os,
  libreharnessVersion: pkg.version,
  commit,
  install: "PASS",
  discovery: { skills: "PASS", tools: "PASS" },
  toolRoundTrip: "PASS",
  journey,
  limitations: evidence.limitations,
};
const directory = join(ROOT, "docs", "certification");
mkdirSync(directory, { recursive: true });
const output = argument("--output") ?? join(directory, `${host}-${os}.json`);
mkdirSync(dirname(output), { recursive: true });
writeFileSync(output, `${JSON.stringify(certificate, null, 2)}\n`);
console.log(`certificate: ${output}`);
console.log(
  `host=${host} os=${os} version=${pkg.version} journey=${journey}`,
);

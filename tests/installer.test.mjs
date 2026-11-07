// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import {
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const cli = new URL("../bin/libreharness.js", import.meta.url).pathname;
const root = join(tmpdir(), `libreharness-installer-${process.pid}`);
rmSync(root, { recursive: true, force: true });

function run(args, env = {}) {
  return spawnSync(process.execPath, [cli, ...args], {
    encoding: "utf8",
    env: { ...process.env, ...env },
  });
}

const help = run(["--help"]);
assert.equal(help.status, 0);
assert.match(help.stdout, /npx libreharness init/);

const version = run(["--version"]);
assert.equal(version.status, 0);
assert.match(version.stdout, /1\.0\.0/);

// A dry run must not create the target.
const dryHome = join(root, "dry-home");
const dry = run([
  "init",
  "--home",
  dryHome,
  "--state",
  join(root, "dry-state"),
  "--yes",
  "--dry-run",
]);
assert.equal(dry.status, 0, dry.stderr);
assert.equal(existsSync(dryHome), false, "dry run created the home");

// Clean install.
const home = join(root, "home");
const state = join(root, "state");
const clean = run([
  "init",
  "--home",
  home,
  "--state",
  state,
  "--yes",
]);
assert.equal(clean.status, 0, clean.stderr);
assert.match(clean.stdout, /doctor: OK/);
for (const path of [
  "AGENTS.md",
  "LICENSE",
  "NOTICE",
  "opencode.example.json",
  "opencode.json",
  "agents/devils-advocate.md",
  "commands/goal.md",
  "commands/state-audit.md",
  "skills/engineering-loop/SKILL.md",
  "skills/state-audit/SKILL.md",
  "plugins/security-guard.js",
  "bin/tasks.py",
  "bin/doctor.py",
  "bin/libreharness.js",
]) {
  assert.ok(existsSync(join(home, path)), `missing ${path}`);
}
assert.ok(existsSync(state), "state root missing");

// A second install must not change an existing user file.
const marker = "# user AGENTS\n";
writeFileSync(join(home, "AGENTS.md"), marker);
const repeat = run(["init", "--home", home, "--state", state, "--yes"]);
assert.equal(repeat.status, 0, repeat.stderr);
assert.equal(readFileSync(join(home, "AGENTS.md"), "utf8"), marker);

// --force backs up the conflict before replacing it.
const forced = run(["init", "--home", home, "--state", state, "--yes", "--force"]);
assert.equal(forced.status, 0, forced.stderr);
assert.match(readFileSync(join(home, "AGENTS.md"), "utf8"), /Agent rules/);
const backups = readdirSync(home).filter((name) => name.startsWith(".libreharness-backup-"));
assert.ok(backups.length > 0, "no backup directory");
assert.ok(
  readdirSync(join(home, backups[0])).includes("AGENTS.md"),
  "AGENTS.md was not backed up",
);

// The package metadata exposes the command and runtime.
const pkg = JSON.parse(readFileSync(new URL("../package.json", import.meta.url), "utf8"));
assert.equal(pkg.bin.libreharness, "bin/libreharness.js");
assert.equal(pkg.private, false);
assert.ok(pkg.files.includes("bin/*.py"));
assert.ok(pkg.files.includes("bin/libreharness.js"));
assert.ok(pkg.files.includes("agents"));

rmSync(root, { recursive: true, force: true });
console.log("installer: PASS");

#!/usr/bin/env node
// SPDX-License-Identifier: MIT
// LibreHarness installer. Copies the runtime into an OpenCode config root and
// creates a state root. Existing files are preserved unless --force.

import { spawnSync } from "node:child_process";
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
   renameSync,
  statSync,
} from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { createInterface } from "node:readline/promises";
import { fileURLToPath } from "node:url";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const VERSION = "1.0.0-rc.1";
const RUNTIME_DIRS = ["agents", "commands", "skills", "plugins", "bin"];
const RUNTIME_FILES = ["AGENTS.md", "LICENSE", "NOTICE", "opencode.example.json"];

function usage() {
  console.log(`LibreHarness ${VERSION}

Usage:
  npx libreharness init [options]
  npx libreharness init --yes
  npx libreharness --help

Options:
  --home <dir>    OpenCode config root (default: ~/.config/opencode)
  --state <dir>   Runtime state root (default: ~/.local/state/libreharness)
  --yes           Use defaults and skip prompts
  --dry-run       Print the plan without writing
  --force         Overwrite conflicting files after backing them up
  --version       Print the version
  --help          Print this help

The installer copies agents, commands, skills, plugins, and bin helpers. It
creates opencode.json from the example only when none exists. It never copies
state, docs, tests, or benchmark data.`);
}

function parse(argv) {
  const first = argv[0] ?? "";
  const args = { command: first.startsWith("-") || !first ? "help" : first };
  for (let i = first.startsWith("-") ? 0 : 1; i < argv.length; i += 1) {
    const item = argv[i];
    if (item === "--help" || item === "-h") args.help = true;
    else if (item === "--version" || item === "-v") args.version = true;
    else if (item === "--yes" || item === "-y") args.yes = true;
    else if (item === "--force") args.force = true;
    else if (item === "--dry-run") args.dryRun = true;
    else if (item === "--home") args.home = argv[++i];
    else if (item === "--state") args.state = argv[++i];
    else throw new Error(`unknown argument: ${item}`);
  }
  return args;
}

async function guided(args) {
  if (args.yes || !process.stdin.isTTY) return args;
  const rl = createInterface({ input: process.stdin, output: process.stdout });
  try {
    const home = await rl.question(
      `Install into [${args.home ?? "~/.config/opencode"}]: `,
    );
    if (home.trim()) args.home = home.trim();
    const state = await rl.question(
      `State directory [${args.state ?? "~/.local/state/libreharness"}]: `,
    );
    if (state.trim()) args.state = state.trim();
    const confirm = await rl.question("Proceed? [Y/n]: ");
    if (confirm.trim().toLowerCase() === "n") args.cancelled = true;
    return args;
  } finally {
    rl.close();
  }
}

function stamp() {
  return new Date().toISOString().replace(/[:.]/g, "-");
}

function sameFile(source, target) {
  try {
    return readFileSync(source).equals(readFileSync(target));
  } catch {
    return false;
  }
}

function backup(home, relative, backupRoot) {
  const source = join(home, relative);
  const target = join(backupRoot, relative);
  mkdirSync(dirname(target), { recursive: true });
  renameSync(source, target);
}

function copyTree(source, target, relative, plan, home, backupRoot) {
  const info = statSync(source);
  if (info.isDirectory()) {
    if (!plan.dryRun) mkdirSync(target, { recursive: true });
    for (const name of readdirSync(source)) {
      copyTree(
        join(source, name),
        join(target, name),
        join(relative, name),
        plan,
        home,
        backupRoot,
      );
    }
    return;
  }
  if (existsSync(target)) {
    if (sameFile(source, target)) {
      plan.skipped += 1;
      return;
    }
    if (!plan.force) {
      plan.conflicts.push(relative);
      return;
    }
    plan.backups.push(relative);
    if (!plan.dryRun) backup(home, relative, backupRoot);
  }
  plan.copied += 1;
  if (!plan.dryRun) {
    mkdirSync(dirname(target), { recursive: true });
    cpSync(source, target);
  }
}

function installFile(relative, plan, home) {
  const source = join(ROOT, relative);
  const target = join(home, relative);
  copyTree(source, target, relative, plan, home, plan.backupRoot);
}

function main() {
  let args;
  try {
    args = parse(process.argv.slice(2));
  } catch (error) {
    console.error(`error: ${error.message}`);
    return 1;
  }
  if (args.version) {
    console.log(VERSION);
    return 0;
  }
  if (args.help || args.command === "help") {
    usage();
    return 0;
  }
  if (args.command !== "init") {
    console.error(`error: unknown command ${args.command}`);
    usage();
    return 1;
  }

  return guided(args).then((next) => {
    if (next.cancelled) {
      console.log("cancelled");
      return 0;
    }
    const home = resolve((next.home ?? join(homedir(), ".config/opencode")).replace(/^~/, homedir()));
    const state = resolve((next.state ?? join(homedir(), ".local/state/libreharness")).replace(/^~/, homedir()));
    const plan = {
      dryRun: Boolean(next.dryRun),
      force: Boolean(next.force),
      copied: 0,
      skipped: 0,
      conflicts: [],
      backups: [],
      backupRoot: join(home, `.libreharness-backup-${stamp()}`),
    };

    if (!existsSync(join(ROOT, "AGENTS.md")) || !existsSync(join(ROOT, "bin/tasks.py"))) {
      console.error("error: this package does not contain the runtime files");
      return 1;
    }
    if (!plan.dryRun) {
      mkdirSync(home, { recursive: true });
      mkdirSync(state, { recursive: true, mode: 0o700 });
    }

    for (const dir of RUNTIME_DIRS) installFile(dir, plan, home);
    for (const file of RUNTIME_FILES) installFile(file, plan, home);

    const config = join(home, "opencode.json");
    if (!existsSync(config)) {
      plan.copied += 1;
      if (!plan.dryRun) cpSync(join(ROOT, "opencode.example.json"), config);
      console.log("config: created opencode.json from the example");
    } else {
      console.log("config: kept existing opencode.json");
    }

    console.log(`home:  ${home}`);
    console.log(`state: ${state}`);
    console.log(
      `files: ${plan.copied} copied, ${plan.skipped} unchanged, ${plan.conflicts.length} conflicts`,
    );
    for (const file of plan.conflicts) console.log(`  kept existing: ${file}`);
    for (const file of plan.backups) console.log(`  backed up: ${file}`);
    if (plan.conflicts.length > 0 && !plan.force) {
      console.log("Re-run with --force to replace conflicts after a backup.");
    }
    if (plan.dryRun) {
      console.log("dry run: nothing written");
      return 0;
    }
    if (plan.backups.length > 0) console.log(`backup: ${plan.backupRoot}`);

    const doctor = spawnSync(
      "python3",
      [join(home, "bin/doctor.py"), "--root", home],
      {
        env: { ...process.env, HARNESS_HOME: home, HARNESS_STATE: state },
        stdio: "inherit",
      },
    );
    if (doctor.error) {
      console.error(`doctor: could not run python3: ${doctor.error.message}`);
      return 1;
    }
    if (doctor.status !== 0) {
      console.error("doctor: failed; fix the reported item before starting OpenCode");
      return doctor.status ?? 1;
    }
    console.log("next: start OpenCode, choose a provider/model, then run /goal");
    return 0;
  }).catch((error) => {
    console.error(`error: ${error.message}`);
    return 1;
  });
}

process.exitCode = await main();

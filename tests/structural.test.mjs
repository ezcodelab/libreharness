// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { execFileSync, spawnSync } from "node:child_process";
import { mkdtempSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const WRAPPER = join(ROOT, "bin", "sg.py");

test("sg wrapper matches a structural pattern", () => {
  const directory = mkdtempSync(join(tmpdir(), "libreharness-sg-"));
  try {
    const file = join(directory, "fixture.js");
    writeFileSync(file, "const value = console.log(1);\n");
    const output = execFileSync(
      "python3",
      [WRAPPER, "run", "-p", "console.log($A)", "-l", "js", file],
      { cwd: ROOT, encoding: "utf8" },
    );
    assert.match(output, /console\.log\(1\)/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("sg wrapper reports a missing binary", () => {
  const result = spawnSync("python3", [WRAPPER, "--version"], {
    cwd: ROOT,
    encoding: "utf8",
    env: { ...process.env, SG_BIN: join(tmpdir(), "missing-ast-grep") },
  });
  assert.equal(result.status, 127);
  assert.match(result.stderr, /ast-grep failed/);
});

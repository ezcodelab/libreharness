// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  lstatSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readlinkSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join, resolve } from "node:path";
import test from "node:test";
import { fileURLToPath } from "node:url";

const ROOT = resolve(fileURLToPath(new URL("..", import.meta.url)));
const WRAPPER = join(ROOT, "bin", "comment-audit");

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: ROOT,
    encoding: "utf8",
    ...options,
  });
}

test("the comment-audit wrapper is executable and answers --help", () => {
  assert.ok(existsSync(WRAPPER), "bin/comment-audit is missing");
  assert.ok(statSync(WRAPPER).mode & 0o111, "bin/comment-audit is not executable");

  const result = run(WRAPPER, ["--help"]);

  assert.equal(result.status, 0, result.stderr);
  for (const flag of ["--diff", "--baseline", "--strict"]) {
    assert.match(result.stdout, new RegExp(flag));
  }
});

test("package.json exposes the entrypoint and ships it", () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));

  assert.equal(pkg.bin?.["comment-audit"], "bin/comment-audit");
  assert.ok(
    pkg.files?.some((entry) => entry === "bin/comment-audit" || entry === "bin/*"),
    "package files must include the wrapper",
  );
});

test("plugin setup installs the stable config-bin symlink", async () => {
  const { installCommentAuditEntrypoint } = await import("../src/plugin.js");
  const configHome = mkdtempSync(join(tmpdir(), "comment-audit-entrypoint-"));
  try {
    const installed = installCommentAuditEntrypoint(configHome);
    const expected = join(configHome, "opencode", "bin", "comment-audit");

    assert.equal(installed, expected);
    assert.ok(lstatSync(expected).isSymbolicLink(), "the entrypoint must be a symlink");
    assert.equal(readlinkSync(expected), WRAPPER);

    const result = run(expected, ["--help"]);
    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /--strict/);
  } finally {
    rmSync(configHome, { recursive: true, force: true });
  }
});

test("plugin setup leaves an unrelated entrypoint alone", async () => {
  const { installCommentAuditEntrypoint } = await import("../src/plugin.js");
  const configHome = mkdtempSync(join(tmpdir(), "comment-audit-entrypoint-"));
  try {
    const bin = join(configHome, "opencode", "bin");
    mkdirSync(bin, { recursive: true });
    const custom = join(bin, "comment-audit");
    writeFileSync(custom, "#!/bin/sh\nexit 0\n");

    assert.equal(installCommentAuditEntrypoint(configHome), null);
    assert.equal(readFileSync(custom, "utf8"), "#!/bin/sh\nexit 0\n");
  } finally {
    rmSync(configHome, { recursive: true, force: true });
  }
});

test("review and no-comments invoke the stable entrypoint", () => {
  const review = readFileSync(join(ROOT, "commands", "review.md"), "utf8");
  const skill = readFileSync(join(ROOT, "skills", "no-comments", "SKILL.md"), "utf8");

  for (const text of [review, skill]) {
    assert.match(text, /opencode\/bin\/comment-audit/);
    assert.match(text, /--diff/);
    assert.doesNotMatch(text, /HARNESS_HOME[^\n]*comment_audit|bin\/comment_audit\.py/);
  }
  assert.match(skill, /--strict/);
  assert.match(skill, /"\$audit" \./);
});

test("reference docs name the three invocations", () => {
  const reference = readFileSync(join(ROOT, "docs", "reference.md"), "utf8");

  assert.match(reference, /comment-audit \./);
  assert.match(reference, /comment-audit --diff/);
  assert.match(reference, /comment-audit --strict/);
});

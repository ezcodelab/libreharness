// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  existsSync,
  readFileSync,
  readdirSync,
  statSync,
} from "node:fs";
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

function markdownFiles(directory) {
  const files = [];
  for (const entry of readdirSync(directory, { withFileTypes: true })) {
    const path = join(directory, entry.name);
    if (entry.isDirectory()) files.push(...markdownFiles(path));
    else if (entry.name.endsWith(".md")) files.push(path);
  }
  return files;
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

test("package.json exposes the package CLI and ships it", () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, "package.json"), "utf8"));

  assert.equal(pkg.bin?.["comment-audit"], "bin/comment-audit");
  assert.ok(
    pkg.files?.some((entry) => entry === "bin/comment-audit" || entry === "bin/*"),
    "package files must include the wrapper",
  );
});

test("commands and skills call plugin tools, not filesystem paths", () => {
  const files = [
    ...markdownFiles(join(ROOT, "commands")),
    ...markdownFiles(join(ROOT, "skills")),
  ];
  for (const file of files) {
    const text = readFileSync(file, "utf8");
    assert.doesNotMatch(
      text,
      /HARNESS_HOME|\/home\/[^/\s]+\/|opencode\/bin\/comment-audit/,
      `${file} has a filesystem fallback`,
    );
    assert.doesNotMatch(
      text,
      /python3\s+["']?[^\n]*bin\/(tasks|pr_guard)\.py/,
      `${file} shells out to a harness script`,
    );
  }
  assert.match(
    readFileSync(join(ROOT, "commands", "review.md"), "utf8"),
    /comment_audit/,
  );
  assert.match(
    readFileSync(join(ROOT, "skills", "no-comments", "SKILL.md"), "utf8"),
    /comment_audit/,
  );
  assert.match(
    readFileSync(join(ROOT, "skills", "work-queue", "SKILL.md"), "utf8"),
    /`tasks` tool/,
  );
  assert.match(
    readFileSync(join(ROOT, "skills", "shipping", "SKILL.md"), "utf8"),
    /`pr_guard`/,
  );
});

test("reference docs name the plugin tools", () => {
  const reference = readFileSync(join(ROOT, "docs", "reference.md"), "utf8");

  assert.match(reference, /`comment_audit`/);
  assert.match(reference, /`tasks` tool/);
  assert.match(reference, /`pr_guard`/);
  assert.doesNotMatch(reference, /opencode\/bin\/comment-audit/);
});

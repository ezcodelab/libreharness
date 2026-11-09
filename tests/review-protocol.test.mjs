// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const root = new URL("..", import.meta.url);
const devil = readFileSync(new URL("agents/devils-advocate.md", root), "utf8");
const review = readFileSync(new URL("commands/review.md", root), "utf8");

for (const token of [
  "CONFIRMED",
  "REFUTED",
  "UNVERIFIED",
  "Source:",
  "Sink or failure point:",
  "Guard:",
  "empty catch",
  "only logs and continues",
  "null, undefined, or default return",
  "optional chaining",
  "fallback chain",
  "retry logic",
]) {
  assert.ok(devil.includes(token), `devils-advocate is missing ${token}`);
}

const reviewPlain = review.replaceAll("*", "");
for (const token of [
  "CONFIRMED",
  "REFUTED",
  "UNVERIFIED",
  "opposite-lens",
  "silent-failure",
  "UNVERIFIED is a warning",
  "Only a CONFIRMED devils P0/P1 blocks",
  "REFUTED is dropped from the blocking list",
  "state-audit",
]) {
  assert.ok(reviewPlain.includes(token), `review command is missing ${token}`);
}

for (const file of ["commands/state-audit.md", "skills/state-audit/SKILL.md"]) {
  const text = readFileSync(new URL(file, root), "utf8");
  for (const token of [
    "docs/state-machines.md",
    "states",
    "invariants",
    "transition",
    "retries",
    "concurrency",
    "regression test",
  ]) {
    assert.ok(text.includes(token), `${file} is missing ${token}`);
  }
}

console.log("review-protocol: PASS");

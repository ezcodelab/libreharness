// SPDX-License-Identifier: MIT
import { packageTool, untracked } from "./runtime.js";

export const ARGS_INPUT = {
  type: "object",
  properties: {
    args: { type: "array", items: { type: "string" } },
    cwd: { type: "string" },
  },
  required: ["args"],
  additionalProperties: false,
};

export const AUDIT_INPUT = {
  type: "object",
  properties: {
    diff: { type: "string" },
    paths: { type: "array", items: { type: "string" } },
    untracked: { type: "boolean" },
    strict: { type: "boolean" },
    baseline: { type: "string" },
    write_baseline: { type: "string" },
    cwd: { type: "string" },
  },
  additionalProperties: false,
};

async function runAudit(input, state, defaultCwd, signal) {
  const cwd = input.cwd ?? defaultCwd;
  const flags = [];
  if (input.strict) flags.push("--strict");
  if (input.baseline) flags.push("--baseline", input.baseline);
  if (input.write_baseline) flags.push("--write-baseline", input.write_baseline);
  const runs = [];
  if (input.diff) runs.push(["--diff", input.diff, ...flags]);
  const paths = [...(input.paths ?? [])];
  if (input.untracked) paths.push(...(await untracked(cwd, signal)));
  if (paths.length) runs.push([...paths, ...flags]);
  const requested =
    Boolean(input.diff) ||
    Boolean(input.paths?.length) ||
    Boolean(input.untracked);
  if (!runs.length && !requested) runs.push([".", ...flags]);
  const outputs = [];
  for (const args of runs) {
    const output = await packageTool(
      "comment_audit.py",
      args,
      cwd,
      { HARNESS_STATE: state },
      signal,
    );
    if (output) outputs.push(output);
  }
  return outputs.join("\n") || "comment audit: PASS";
}

async function runArgs(script, input, state, defaultCwd, signal) {
  const output = await packageTool(
    script,
    input.args,
    input.cwd ?? defaultCwd,
    { HARNESS_STATE: state },
    signal,
  );
  return output || `${script}: PASS`;
}

export const TOOLS = [
  {
    name: "comment_audit",
    description:
      "Run the deterministic LibreHarness comment audit on a diff, paths, or untracked files.",
    input: AUDIT_INPUT,
    async execute(input, context) {
      return runAudit(
        input,
        context.state,
        context.cwd ?? process.cwd(),
        context.signal,
      );
    },
  },
  {
    name: "tasks",
    description:
      "Run the LibreHarness task queue CLI against the current repository.",
    input: ARGS_INPUT,
    async execute(input, context) {
      return runArgs(
        "tasks.py",
        input,
        context.state,
        context.cwd ?? process.cwd(),
        context.signal,
      );
    },
  },
  {
    name: "pr_guard",
    description: "Run the LibreHarness PR guard for shipping.",
    input: ARGS_INPUT,
    async execute(input, context) {
      return runArgs(
        "pr_guard.py",
        input,
        context.state,
        context.cwd ?? process.cwd(),
        context.signal,
      );
    },
  },
];

export function toolByName(name) {
  return TOOLS.find((tool) => tool.name === name);
}

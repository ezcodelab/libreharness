// SPDX-License-Identifier: MIT
import { spawn } from "node:child_process";
import { chmodSync, mkdirSync, readFileSync, readdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { Plugin } from "@opencode/plugin";

const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));
const COMMANDS = join(ROOT, "commands");
const AGENTS = join(ROOT, "agents");
const SKILLS = join(ROOT, "skills");

function scalar(value) {
  const text = value.trim();
  if (text === "true") return true;
  if (text === "false") return false;
  if (/^\d+$/.test(text)) return Number(text);
  return text.replace(/^["']|["']$/g, "");
}

function frontmatter(text) {
  if (!text.startsWith("---\n")) return { data: {}, body: text };
  const end = text.indexOf("\n---", 4);
  if (end === -1) return { data: {}, body: text };
  const data = {};
  let list = null;
  let item = null;
  for (const line of text.slice(4, end).split(/\r?\n/)) {
    if (!line.trim()) continue;
    const entry = line.match(/^\s*-\s+([\w-]+):\s*(.*)$/);
    if (entry && list) {
      item = { [entry[1]]: scalar(entry[2]) };
      data[list].push(item);
      continue;
    }
    const prop = line.match(/^\s+([\w-]+):\s*(.*)$/);
    if (prop && item) {
      item[prop[1]] = scalar(prop[2]);
      continue;
    }
    const top = line.match(/^([\w-]+):\s*(.*)$/);
    if (!top) continue;
    list = top[2] === "" ? top[1] : null;
    item = null;
    data[top[1]] = list ? [] : scalar(top[2]);
  }
  return { data, body: text.slice(end + 4).replace(/^\r?\n/, "") };
}

function commandFiles() {
  return readdirSync(COMMANDS)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .map((name) => {
      const { data, body } = frontmatter(
        readFileSync(join(COMMANDS, name), "utf8"),
      );
      return {
        name: name.slice(0, -3),
        description: data.description ?? "",
        template: body,
      };
    });
}

function agentFiles() {
  return readdirSync(AGENTS)
    .filter((name) => name.endsWith(".md"))
    .sort()
    .map((name) => {
      const { data, body } = frontmatter(
        readFileSync(join(AGENTS, name), "utf8"),
      );
      const id = name.slice(0, -3);
      const agent = {
        id,
        name: id,
        description: data.description ?? "",
        mode: data.mode ?? "subagent",
        system: body.trim(),
        hidden: false,
        permissions: Array.isArray(data.permissions) ? data.permissions : [],
        request: { settings: {}, headers: {}, body: {} },
      };
      if (data.steps) agent.steps = data.steps;
      return agent;
    });
}

function skillFiles() {
  return readdirSync(SKILLS)
    .filter((name) => {
      try {
        readFileSync(join(SKILLS, name, "SKILL.md"));
        return true;
      } catch {
        return false;
      }
    })
    .sort()
    .map((name) => {
      const path = join(SKILLS, name, "SKILL.md");
      const { data, body } = frontmatter(readFileSync(path, "utf8"));
      return {
        id: data.name ?? name,
        name: data.name ?? name,
        description: data.description ?? "",
        path,
        content: body,
      };
    });
}

export function statePath(value) {
  const chosen = value ?? join(homedir(), ".local/state/libreharness");
  return resolve(chosen.replace(/^~/, homedir()));
}

export function modelRef(value) {
  if (typeof value !== "string" || !value.trim()) return null;
  const text = value.trim();
  const slash = text.indexOf("/");
  if (slash <= 0 || slash === text.length - 1) return null;
  const providerID = text.slice(0, slash);
  const rest = text.slice(slash + 1);
  const hash = rest.lastIndexOf("#");
  if (hash <= 0) return { providerID, id: rest };
  if (hash === rest.length - 1) return null;
  return {
    providerID,
    id: rest.slice(0, hash),
    variant: rest.slice(hash + 1),
  };
}

function applyAgentModels(agent, agentModels) {
  if (!agentModels || typeof agentModels !== "object") return;
  const value = agentModels[agent.id];
  if (value === undefined) return;
  const model = modelRef(value);
  if (!model) {
    console.warn(
      `libreharness: agentModels.${agent.id} must be provider/model#variant`,
    );
    return;
  }
  agent.model = model;
}

function runProcess(command, args, cwd, env, signal) {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      cwd,
      env,
      signal,
      stdio: ["ignore", "pipe", "pipe"],
    });
    let stdout = "";
    let stderr = "";
    child.stdout.setEncoding("utf8");
    child.stderr.setEncoding("utf8");
    child.stdout.on("data", (chunk) => {
      stdout += chunk;
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk;
    });
    child.on("error", reject);
    child.on("close", (code, signalName) => {
      const output = [stdout, stderr].filter(Boolean).join("\n").trim();
      if (code === 0) {
        resolve(output);
        return;
      }
      reject(
        new Error(
          `${command} exited ${code ?? signalName}${output ? `:\n${output}` : ""}`,
        ),
      );
    });
  });
}

async function packageTool(script, args, cwd, env, signal) {
  const childEnv = { ...process.env, ...env };
  delete childEnv.HARNESS_HOME;
  return runProcess(
    "python3",
    [join(ROOT, "bin", script), ...args],
    cwd,
    childEnv,
    signal,
  );
}

async function untracked(cwd, signal) {
  const output = await runProcess(
    "git",
    ["ls-files", "-z", "--others", "--exclude-standard"],
    cwd,
    process.env,
    signal,
  );
  return output.split("\0").filter(Boolean);
}

const ARGS_INPUT = {
  type: "object",
  properties: {
    args: { type: "array", items: { type: "string" } },
    cwd: { type: "string" },
  },
  required: ["args"],
  additionalProperties: false,
};

const AUDIT_INPUT = {
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
    Boolean(input.diff) || Boolean(input.paths?.length) || Boolean(input.untracked);
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

const plugin = Plugin.define({
  id: "libreharness",
  async setup(ctx) {
    const home = ROOT;
    const state = statePath(ctx.options?.state);
    process.env.HARNESS_HOME = home;
    process.env.HARNESS_STATE = state;
    mkdirSync(state, { recursive: true, mode: 0o700 });
    // mkdir's mode only applies to a new directory; fix an existing one too.
    chmodSync(state, 0o700);
    const defaultCwd = ctx.location?.directory ?? process.cwd();
    await ctx.tool.transform((editor) => {
      editor.add({
        name: "comment_audit",
        description:
          "Run the deterministic LibreHarness comment audit on a diff, paths, or untracked files.",
        input: AUDIT_INPUT,
        execute: async (input, context) => ({
          content: await runAudit(input, state, defaultCwd, context?.signal),
        }),
      });
      editor.add({
        name: "tasks",
        description:
          "Run the LibreHarness task queue CLI against the current repository.",
        input: ARGS_INPUT,
        execute: async (input, context) => ({
          content: await runArgs(
            "tasks.py",
            input,
            state,
            defaultCwd,
            context?.signal,
          ),
        }),
      });
      editor.add({
        name: "pr_guard",
        description: "Run the LibreHarness PR guard for shipping.",
        input: ARGS_INPUT,
        execute: async (input, context) => ({
          content: await runArgs(
            "pr_guard.py",
            input,
            state,
            defaultCwd,
            context?.signal,
          ),
        }),
      });
    });

    const commands = commandFiles();
    await ctx.command.transform((editor) => {
      for (const command of commands) {
        editor.add({
          name: command.name,
          description: command.description,
          execute: async ({ sessionID, prompt, delivery }) => {
            const args = prompt.text ?? "";
            const text = command.template.includes("$ARGUMENTS")
              ? command.template.replaceAll("$ARGUMENTS", args)
              : args
                ? `${command.template}\n\nArguments: ${args}`
                : command.template;
            await ctx.session.prompt({ ...prompt, sessionID, text, delivery });
          },
        });
      }
    });

    const agents = agentFiles();
    await ctx.agent.transform((editor) => {
      for (const agent of agents) {
        editor.update(agent.id, (current) => {
          current.description = agent.description;
          current.system = agent.system;
          current.mode = agent.mode;
          current.permissions = agent.permissions;
          if (agent.steps) current.steps = agent.steps;
          applyAgentModels(current, ctx.options?.agentModels);
        });
      }
    });

    const skills = skillFiles();
    await ctx.skill.transform((editor) => {
      for (const skill of skills) editor.add(skill);
    });

    const cleanups = [];
    for (const featurePath of [
      "../plugins/auto-intake.js",
      "../plugins/goal-watch.js",
      "../plugins/usage-ledger.js",
    ]) {
      try {
        const { default: feature } = await import(featurePath);
        const cleanup = await feature.setup(ctx);
        if (typeof cleanup === "function") cleanups.push(cleanup);
      } catch (error) {
        console.warn(
          `libreharness: ${featurePath} failed: ${error?.message ?? error}`,
        );
      }
    }

    return () => {
      for (const cleanup of cleanups) {
        try {
          cleanup();
        } catch {
          // A feature cleanup must not prevent the rest from unloading.
        }
      }
    };
  },
});

export default plugin;

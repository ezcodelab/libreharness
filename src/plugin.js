// SPDX-License-Identifier: MIT
import { readFileSync, readdirSync } from "node:fs";
import { join } from "node:path";
import { Plugin } from "@opencode/plugin";
import {
  ROOT,
  ensureStateDirectory,
  statePath,
} from "./runtime.js";
import { TOOLS } from "./tools.js";

export { statePath };

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
      const skillPath =
        typeof data.skill === "string"
          ? join(SKILLS, data.skill, "SKILL.md")
          : null;
      const template = skillPath
        ? frontmatter(readFileSync(skillPath, "utf8")).body
        : body;
      return {
        name: name.slice(0, -3),
        description: data.description ?? "",
        template,
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

const plugin = Plugin.define({
  id: "libreharness",
  async setup(ctx) {
    const home = ROOT;
    const state = statePath(ctx.options?.state);
    process.env.HARNESS_HOME = home;
    process.env.HARNESS_STATE = state;
    ensureStateDirectory(state);
    const defaultCwd = ctx.location?.directory ?? process.cwd();
    await ctx.tool.transform((editor) => {
      for (const tool of TOOLS) {
        editor.add({
          name: tool.name,
          description: tool.description,
          input: tool.input,
          execute: async (input, context) => ({
            content: await tool.execute(input, {
              state,
              cwd: defaultCwd,
              signal: context?.signal,
            }),
          }),
        });
      }
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

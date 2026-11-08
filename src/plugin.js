// SPDX-License-Identifier: MIT
import { mkdirSync, readFileSync, readdirSync } from "node:fs";
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

const plugin = Plugin.define({
  id: "libreharness",
  async setup(ctx) {
    const home = ROOT;
    const state = statePath(ctx.options?.state);
    process.env.HARNESS_HOME = home;
    process.env.HARNESS_STATE = state;
    mkdirSync(state, { recursive: true, mode: 0o700 });

    const instructions = readFileSync(join(ROOT, "AGENTS.md"), "utf8");
    await ctx.session.hook("context", (event) => {
      const present = event.system.some(
        (part) => part.type === "text" && part.text.includes("## Task scale"),
      );
      if (!present) event.system.push({ type: "text", text: instructions });
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
      "../plugins/close-reminder.js",
      "../plugins/goal-watch.js",
      "../plugins/security-guard.js",
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

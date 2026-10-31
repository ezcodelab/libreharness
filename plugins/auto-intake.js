// SPDX-License-Identifier: MIT
// auto-intake: turn a nontrivial prompt into an inbox task before the model
// answers. It never blocks admission on failure and never stores a prompt that
// looks like it contains a secret. Opt out with AUTO_INTAKE=off.
import { execFileSync } from "node:child_process";
import { readFileSync, readdirSync } from "node:fs";
import { basename } from "node:path";

const HOME =
  process.env.HARNESS_HOME ?? `${process.env.HOME}/.config/opencode`;
const ROOT =
  process.env.AUTO_INTAKE_ROOT ??
  process.env.HARNESS_STATE ??
  `${process.env.HOME}/.local/state/libreharness`;
const TASKS = process.env.AUTO_INTAKE_TASKS ?? `${HOME}/bin/tasks.py`;
const DISABLED = process.env.AUTO_INTAKE === "off";

const ACTION =
  /\b(fix|add|implement|build|refactor|investigate|debug|review|design|migrate|test|document|deploy|update|remove|rename|optimi[sz]e|audit|release|create|write|change|make|repair|verify)\b/i;
const QUESTION_ONLY =
  /^\s*(how|what|why|when|where|who|is|are|do|does|did)\b/i;
const CONTINUE =
  /^\s*(continue|go on|keep going|yes|ok|okay|proceed|retry|again|done)\b/i;
const DELEGATION =
  /^\s*(you are|act as|role:|read-only|independent|focused|re-?review|implement one explicitly|task may be complete)/i;
// Keep this list at least as strict as bin/jev_review.py SECRET_PATTERNS.
const SECRET =
  /(AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|sk[_-](live|test)?[_-]?[A-Za-z0-9]{10,}|xox[baprs]-[A-Za-z0-9-]{10,}|Bearer\s+eyJ[A-Za-z0-9._-]{10,}|-----BEGIN [A-Z ]*PRIVATE KEY-----|(api[_-]?key|secret|password|token|access[_-]?key)\s*[:=]\s*(?:"[^"]{8,}"|'[^']{8,}'|\S{8,}))/i;
const PII =
  /([A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}|https?:\/\/\S+|\b\d{3}[-.]?\d{3}[-.]?\d{4}\b)/gi;

const seen = new Map();

function sanitize(text) {
  return text.replace(SECRET, "[redacted]").replace(PII, "[redacted]");
}

function nontrivial(text) {
  if (!text || text.length < 12) return false;
  if (text.startsWith("/") || text.startsWith("@")) return false;
  if (DELEGATION.test(text) || CONTINUE.test(text)) return false;
  if (QUESTION_ONLY.test(text)) return false;
  return ACTION.test(text) || text.length > 160;
}

function titleOf(text) {
  return sanitize(text.split("\n")[0]).trim().slice(0, 72);
}

function slugOf(text) {
  return titleOf(text)
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 48);
}

function existingTask(text) {
  const suffix = `-${slugOf(text)}`;
  try {
    const file = readdirSync(`${ROOT}/work/tasks`).find(
      (name) => name.endsWith(".md") && name.includes(suffix),
    );
    if (!file) return null;
    const body = readFileSync(`${ROOT}/work/tasks/${file}`, "utf8");
    return /^status:\s*(inbox|ready)\s*$/m.test(body) ? file.slice(0, -3) : null;
  } catch {
    return null;
  }
}

function createTask(text, directory) {
  const title = titleOf(text);
  const project = basename(directory || "") || "general";
  const output = execFileSync(
    "python3",
    [
      TASKS,
      "new",
      "--project",
      project,
      "--status",
      "inbox",
      "--scope",
      "Auto-captured prompt; use /goal to confirm scope and acceptance.",
      "--acceptance",
      "- [ ] TBD — confirm before claiming.",
      "--",
      title,
    ],
    {
      encoding: "utf8",
      timeout: 2500,
      // Do not hand the queue helper the provider/session environment.
      env: {
        PATH: process.env.PATH ?? "/usr/bin:/bin",
        HOME: process.env.HOME ?? "",
        HARNESS_STATE: ROOT,
        PYTHONDONTWRITEBYTECODE: "1",
      },
    },
  );
  return output.trim().split("\n").pop();
}

export default {
  id: "auto-intake",
  async setup(ctx) {
    if (DISABLED || !ctx?.session?.hook) return;
    await ctx.session.hook("prompt", (event) => {
      const text = event?.prompt?.text ?? "";
      const sessionID = event?.sessionID ?? event?.session?.id ?? "unknown";
      if (text.startsWith("/close")) {
        seen.delete(sessionID);
        return;
      }
      if (!nontrivial(text) || SECRET.test(text)) return;
      if (seen.has(sessionID)) return;
      const existing = existingTask(text);
      if (existing) {
        seen.set(sessionID, existing);
        event.prompt.text =
          text +
          `\n\n[queue] Existing task ${existing} matches this request. ` +
          `Use it; do not create a duplicate.`;
        return;
      }
      try {
        const id = createTask(text, ctx.location?.directory);
        seen.set(sessionID, id);
        event.prompt.text =
          text +
          `\n\n[queue] Task ${id} was created for this request. ` +
          `Continue with the goal skill now: confirm scope/acceptance, execute a ` +
          `small task directly, or stop at the plan for a large one. Do not ask the ` +
          `operator to retype a command.`;
      } catch {
        // Never block a prompt because the queue helper is unavailable.
      }
    });
  },
};

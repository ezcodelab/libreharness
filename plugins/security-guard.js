// SPDX-License-Identifier: MIT
// security-guard: local, advisory scan of edit tool input for six dangerous
// patterns. It appends one warning after the tool runs; it never blocks a
// tool, calls a model, or uses the network. ESM.
const TOOLS = new Set(["edit", "write", "patch", "apply_patch"]);
const MARK = "[security-guard]";
// Real OpenCode 2.2.1 execute.after event: { tool, input, result } with
// edit/write text in result.content, not a string result.output.
const ALLOW = /security-guard:\s*allow\b([^\n]*)/gi;

const RULES = [
  {
    id: "yaml-unsafe-load",
    test: (text) => /\byaml\.(?:unsafe_load|load)\s*\(/.test(text),
    risk: "unsafe YAML can instantiate arbitrary objects",
  },
  {
    id: "pickle-load",
    test: (text) => /\b(?:c)?[Pp]ickle\.loads?\s*\(/.test(text),
    risk: "unpickling untrusted data can run arbitrary code",
  },
  {
    id: "torch-load",
    line: true,
    test: (line) =>
      /\btorch\.load\s*\(/.test(line) && !/weights_only\s*=\s*True/.test(line),
    risk: "torch.load on untrusted data can execute pickle code",
  },
  {
    id: "html-assignment",
    test: (text) => /\b(?:inner|outer)HTML\s*=(?!=)/.test(text),
    risk: "HTML assignment can inject markup or script",
  },
  {
    id: "child-process-exec",
    test: (text) => /(?:child_process\.exec\s*\(|\bexecSync\s*\()/.test(text),
    risk: "shell exec with untrusted input can run commands",
  },
  {
    id: "actions-injection",
    line: true,
    test: (line) =>
      /\brun\s*:/.test(line) &&
      /\$\{\{\s*github\.(?:event\.|head_ref\s*\}\}|base_ref\s*\}\})/.test(line),
    risk: "untrusted event data in run: can inject shell commands",
  },
];

function allowedRules(text) {
  const ids = new Set();
  let blanket = false;
  for (const match of text.matchAll(ALLOW)) {
    const known = (match[1].match(/\b[a-z][a-z-]+\b/g) ?? []).filter((id) =>
      RULES.some((rule) => rule.id === id),
    );
    if (known.length === 0) blanket = true;
    else for (const id of known) ids.add(id);
  }
  return { blanket, ids };
}

export function scanText(text) {
  if (typeof text !== "string" || text.length === 0) return [];
  const allowed = allowedRules(text);
  if (allowed.blanket) return [];
  // JSON.stringify escapes newlines, so split those too for line-scoped rules.
  const lines = text.split(/\r?\n|\\n/);
  return RULES.filter(
    (rule) =>
      !allowed.ids.has(rule.id) &&
      (rule.line ? lines.some((line) => rule.test(line)) : rule.test(text)),
  ).map((rule) => rule.id);
}

function warningFor(ids) {
  const details = ids.map((id) => {
    const rule = RULES.find((item) => item.id === id);
    return `${id}: ${rule?.risk ?? "risky pattern"}`;
  });
  return `${MARK} ${details.join("; ")}. If intentional, add "security-guard: allow <rule-id> because ..." to the edit.`;
}

function inspect(event) {
  if (!TOOLS.has(event?.tool)) return;
  const ids = scanText(JSON.stringify(event.args ?? event.input ?? {}));
  if (ids.length === 0) return;
  const warning = warningFor(ids);
  const result = event.result;

  if (typeof result === "string") {
    if (!result.includes(MARK)) event.result = `${result}\n\n${warning}`;
    return;
  }
  if (!result || typeof result !== "object") return;
  if (typeof result.output === "string") {
    if (!result.output.includes(MARK)) {
      result.output = `${result.output}\n\n${warning}`;
    }
  }
  // edit/write return an object output plus a content part array; the model
  // reads content, not the object.
  if (Array.isArray(result.content)) {
    if (!result.content.some((part) => part?.text?.includes(MARK))) {
      result.content.push({ type: "text", text: warning });
    }
  } else if (result.output == null) {
    result.content = [{ type: "text", text: warning }];
  }
}

export default {
  id: "security-guard",
  async setup(ctx) {
    try {
      if (!ctx?.tool?.hook) return;
      const registration = await ctx.tool.hook("execute.after", (event) => {
        try {
          inspect(event);
        } catch {
          // Advisory only; a scan failure must not affect the tool result.
        }
      });
      return () => {
        try {
          registration?.dispose?.();
        } catch {}
      };
    } catch {
      // Hook registration is optional; never take OpenCode down.
      return;
    }
  },
};

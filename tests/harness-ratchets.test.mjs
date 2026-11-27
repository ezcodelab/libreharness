// SPDX-License-Identifier: MIT
import assert from "node:assert/strict";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), "..");

export const ASCII_IGNORE_GLOBS = [
  "CHANGELOG.md",
  "src/generated/**",
  "plugins/generated/**",
  ".opencode/node_modules/**",
];

const ASCII_SCOPE_FILES = [
  "AGENTS.md",
  "README.md",
  "CONTRIBUTING.md",
  "docs/reference.md",
];
const ASCII_SCOPE_DIRS = ["skills", ".opencode", "commands", "agents", "src", "plugins"];
const ASCII_EXTENSIONS = new Set([".md", ".js", ".mjs", ".py"]);

const FORBIDDEN_CHARACTERS = [
  ["\u2014", "em dash (U+2014)"],
  ["\u2013", "en dash (U+2013)"],
  ["\u2018", "curly single quote (U+2018)"],
  ["\u2019", "curly single quote (U+2019)"],
  ["\u201c", "curly double quote (U+201C)"],
  ["\u201d", "curly double quote (U+201D)"],
];

const PLAYBOOKS = [
  "investigation",
  "bug-fix",
  "feature",
  "refactoring",
  "perf",
  "hillclimb",
  "autonomous-multiphase",
  "correct",
];

function rel(root, path) {
  return relative(root, path).split("\\").join("/");
}

function frontmatter(text) {
  if (!text.startsWith("---\n")) return null;
  const end = text.indexOf("\n---", 4);
  if (end < 0) return null;
  const meta = {};
  for (const line of text.slice(4, end).split("\n")) {
    const match = line.match(/^([\w-]+):\s*(.*)$/);
    if (match && match[1] !== "") meta[match[1]] = match[2].trim();
  }
  return meta;
}

function ignored(relPath, globs) {
  return globs.some((glob) => {
    if (glob.endsWith("/**")) return relPath === glob.slice(0, -3) || relPath.startsWith(glob.slice(0, -2));
    return relPath === glob;
  });
}

function walk(dir, files = []) {
  if (!existsSync(dir)) return files;
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    const path = join(dir, entry.name);
    if (entry.isDirectory()) walk(path, files);
    else if (entry.isFile()) files.push(path);
  }
  return files;
}

function hasHeading(path, heading) {
  if (!existsSync(path)) return false;
  const padded = `\n${readFileSync(path, "utf8")}`;
  return padded.includes(`\n${heading}\n`) || padded.includes(`\n${heading}\r\n`);
}

function has(file, needle) {
  return existsSync(file) && readFileSync(file, "utf8").includes(needle);
}

function push(problems, rule, file, message, line) {
  problems.push(line ? { rule, file, line, message } : { rule, file, message });
}

export function formatProblem(problem) {
  const location = problem.line ? `${problem.file}:${problem.line}` : problem.file;
  return `${problem.rule}: ${location}: ${problem.message}`;
}

export function checkSkillStructure(root) {
  const problems = [];
  for (const base of [join(root, "skills"), join(root, ".opencode", "skills")]) {
    if (!existsSync(base)) continue;
    for (const entry of readdirSync(base, { withFileTypes: true })) {
      if (!entry.isDirectory()) continue;
      const directory = join(base, entry.name);
      const file = join(directory, "SKILL.md");
      const relDir = rel(root, directory);
      if (!existsSync(file)) {
        push(problems, "skill-structure", relDir, "missing SKILL.md");
        continue;
      }
      const relFile = rel(root, file);
      const text = readFileSync(file, "utf8");
      const meta = frontmatter(text);
      if (!meta) {
        push(problems, "skill-structure", relFile, "missing YAML frontmatter");
        continue;
      }
      if (!meta.name) push(problems, "skill-structure", relFile, "frontmatter needs a name");
      else if (meta.name !== entry.name) {
        push(problems, "skill-structure", relFile, `frontmatter name "${meta.name}" must match the directory "${entry.name}"`);
      }
      if (!meta.description) push(problems, "skill-structure", relFile, "frontmatter needs a description");
    }
  }
  return problems;
}

export function checkAsciiProse(root) {
  const problems = [];
  const files = [];
  for (const name of ASCII_SCOPE_FILES) {
    const path = join(root, name);
    if (existsSync(path)) files.push(path);
  }
  for (const name of ASCII_SCOPE_DIRS) {
    for (const path of walk(join(root, name))) {
      if (ASCII_EXTENSIONS.has(path.slice(path.lastIndexOf(".")))) files.push(path);
    }
  }
  for (const path of files) {
    const relPath = rel(root, path);
    if (ignored(relPath, ASCII_IGNORE_GLOBS)) continue;
    const lines = readFileSync(path, "utf8").split("\n");
    lines.forEach((line, index) => {
      for (const [character, label] of FORBIDDEN_CHARACTERS) {
        if (!line.includes(character)) continue;
        push(problems, "ascii-prose", relPath, `replace ${label} with ASCII punctuation`, index + 1);
        break;
      }
    });
  }
  return problems;
}

export function checkAgentsContract(root) {
  const problems = [];
  const file = join(root, "AGENTS.md");
  if (!existsSync(file)) return [{ rule: "agents-contract", file: "AGENTS.md", message: "missing AGENTS.md" }];
  if (hasHeading(file, "## Task scale")) {
    push(problems, "agents-contract", "AGENTS.md", "routing belongs in skills/engineering-loop, not always-on AGENTS.md");
  }
  for (const heading of ["## Commands", "## Boundaries", "## Rule enforcement"]) {
    if (!hasHeading(file, heading)) push(problems, "agents-contract", "AGENTS.md", `missing ${heading}`);
  }
  return problems;
}

export function checkInstructionOwners(root) {
  const problems = [];
  const owner = "skills/README.md";
  const header = "| Skill | Use |";
  const ownerPath = join(root, owner);
  if (!existsSync(ownerPath)) {
    push(problems, "instruction-owners", owner, "missing the skill-map owner");
  } else if (!readFileSync(ownerPath, "utf8").includes(header)) {
    push(problems, "instruction-owners", owner, "the skill map must own the Skill | Use table");
  }
  for (const name of ["AGENTS.md", "README.md", "docs/reference.md"]) {
    const path = join(root, name);
    if (!existsSync(path)) {
      push(problems, "instruction-owners", name, "missing file");
      continue;
    }
    const text = readFileSync(path, "utf8");
    if (!/\]\([^)]*skills\/README\.md(?:#[^)]*)?\)/.test(text)) {
      push(problems, "instruction-owners", name, `must link to ${owner}`);
    }
  }
  const scope = [
    join(root, "AGENTS.md"),
    join(root, "README.md"),
    ...walk(join(root, "docs")),
    ...walk(join(root, "commands")),
    ...walk(join(root, "agents")),
    ...walk(join(root, "skills")),
    ...walk(join(root, ".opencode", "skills")),
  ].filter((path) => path.endsWith(".md"));
  for (const path of scope) {
    const relPath = rel(root, path);
    if (relPath === owner) continue;
    if (ignored(relPath, ["CHANGELOG.md", "skills/correct/references/rule-ledger.md"])) continue;
    if (readFileSync(path, "utf8").includes(header)) {
      push(problems, "instruction-owners", relPath, `the skill map has one owner: ${owner}`);
    }
  }
  return problems;
}

export function checkRelativeLinks(root) {
  const problems = [];
  const scope = [
    "AGENTS.md",
    "README.md",
    "CONTRIBUTING.md",
    "docs/reference.md",
    ...walk(join(root, "skills")).map((path) => rel(root, path)),
    ...walk(join(root, "commands")).map((path) => rel(root, path)),
    ...walk(join(root, "agents")).map((path) => rel(root, path)),
    ...walk(join(root, ".opencode", "skills")).map((path) => rel(root, path)),
  ].filter((name) => name.endsWith(".md"));
  for (const name of scope) {
    const path = join(root, name);
    if (!existsSync(path)) continue;
    readFileSync(path, "utf8")
      .split("\n")
      .forEach((line, index) => {
        for (const match of line.matchAll(/!?\[[^\]]*\]\(([^)\s]+)\)/g)) {
          const target = match[1];
          if (/^[a-z][a-z0-9+.-]*:/i.test(target) || target.startsWith("#")) continue;
          const clean = decodeURI(target.split("#")[0].split("?")[0]);
          if (!clean) continue;
          if (!existsSync(resolve(dirname(path), clean))) {
            push(problems, "relative-link", name, `link target does not exist: ${target}`, index + 1);
          }
        }
      });
  }
  return problems;
}

export function checkRouterWiring(root) {
  const problems = [];
  const router = join(root, "skills/engineering-loop/SKILL.md");
  const index = join(root, "skills/engineering-loop/references/playbooks.md");
  const playbooks = join(root, "skills/engineering-loop/references/playbooks");

  for (const heading of ["## Playbook router", "## Fallback"]) {
    if (!hasHeading(router, heading)) push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", `missing ${heading}`);
  }
  if (!has(router, "references/playbooks/")) {
    push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", "must load references/playbooks/<id>.md");
  }
  for (const name of PLAYBOOKS) {
    if (!has(router, `\`${name}\``)) {
      push(problems, "router-wiring", "skills/engineering-loop/SKILL.md", `router table is missing \`${name}\``);
    }
  }
  if (!existsSync(index)) {
    push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", "missing playbook index");
  } else {
    const text = readFileSync(index, "utf8");
    for (const name of PLAYBOOKS) {
      if (!text.includes(`playbooks/${name}.md`)) {
        push(problems, "router-wiring", "skills/engineering-loop/references/playbooks.md", `index is missing ${name}`);
      }
    }
  }
  for (const name of PLAYBOOKS) {
    const file = `skills/engineering-loop/references/playbooks/${name}.md`;
    const path = join(root, file);
    if (!existsSync(path)) {
      push(problems, "router-wiring", file, "missing playbook file");
      continue;
    }
    const lines = readFileSync(path, "utf8").split("\n").filter((line) => line.trim() !== "");
    const steps = lines.filter((line) => /^\s*(?:\d+\.|-)\s+\S/.test(line));
    if (steps.length === 0) {
      push(problems, "router-wiring", file, "playbook needs at least one numbered step");
    }
  }
  return problems;
}

const POLICY_PHRASES = [
  "independent verifier PASS",
  "opposite-lens",
  "gate cannot certify",
];
const POLICY_IGNORE = [
  "CHANGELOG.md",
  "skills/correct/references/rule-ledger.md",
];

export function checkPolicyWiring(root) {
  const problems = [];
  const files = [];
  for (const base of ["commands", "agents", ".github/workflows"]) {
    for (const path of walk(join(root, base))) {
      const extension = path.slice(path.lastIndexOf("."));
      if ([".md", ".yml", ".yaml"].includes(extension)) files.push(path);
    }
  }
  for (const base of ["skills", ".opencode/skills"]) {
    for (const path of walk(join(root, base))) {
      if (path.endsWith("SKILL.md")) files.push(path);
    }
  }
  for (const name of ["README.md", "docs/reference.md", "SECURITY.md", "CONTRIBUTING.md"]) {
    const path = join(root, name);
    if (existsSync(path)) files.push(path);
  }
  for (const path of files) {
    const relPath = rel(root, path);
    if (ignored(relPath, POLICY_IGNORE)) continue;
    readFileSync(path, "utf8")
      .split("\n")
      .forEach((line, index) => {
        for (const phrase of POLICY_PHRASES) {
          if (line.includes(phrase)) {
            push(
              problems,
              "policy-wiring",
              relPath,
              `remove "${phrase}"; policy is recorded in the review artifact`,
              index + 1,
            );
          }
        }
      });
  }
  return problems;
}

export function checkIntakeWiring(root) {
  const file = "plugins/auto-intake.js";
  const path = join(root, file);
  if (!existsSync(path)) return [{ rule: "intake-wiring", file, message: "missing file" }];
  const text = readFileSync(path, "utf8");
  const problems = [];
  if (!text.includes("export function routePrompt")) {
    push(problems, "intake-wiring", file, "missing export function routePrompt");
  }
  const list = text.match(/export const PLAYBOOK_IDS = \[([\s\S]*?)\];/);
  const ids = list ? [...list[1].matchAll(/"([^"]+)"/g)].map((match) => match[1]) : [];
  for (const id of PLAYBOOKS) {
    if (!ids.includes(id)) push(problems, "intake-wiring", file, `PLAYBOOK_IDS is missing ${id}`);
  }
  for (const id of ids) {
    if (!PLAYBOOKS.includes(id)) push(problems, "intake-wiring", file, `PLAYBOOK_IDS has unregistered id ${id}`);
  }
  return problems;
}

export function checkCommentAuditWiring(root) {
  const problems = [];
  const reusable = ".github/workflows/comment-audit.yml";
  const path = join(root, reusable);
  if (!existsSync(path)) {
    push(problems, "comment-audit-wiring", reusable, "missing reusable comment audit workflow");
  } else {
    const text = readFileSync(path, "utf8");
    for (const [needle, message] of [
      ["workflow_call", "missing workflow_call trigger"],
      ["harness_ref", "missing pinned harness_ref input"],
      ["bin/comment_audit.py --diff", "missing the diff audit command"],
    ]) {
      if (!text.includes(needle)) push(problems, "comment-audit-wiring", reusable, message);
    }
  }
  for (const [file, needle, message] of [
    [".github/workflows/ci.yml", "bin/comment_audit.py --diff", "CI must audit the PR diff"],
    [
      ".github/workflows/auto-merge.yml",
      "base/bin/comment_audit.py --diff",
      "auto-merge must run the trusted base audit on the PR diff",
    ],
  ]) {
    const target = join(root, file);
    if (!existsSync(target)) {
      push(problems, "comment-audit-wiring", file, "missing workflow");
    } else if (!readFileSync(target, "utf8").includes(needle)) {
      push(problems, "comment-audit-wiring", file, message);
    }
  }
  return problems;
}

export function checkPrContract(root) {
  const problems = [];
  const workflow = join(root, ".github/workflows/auto-merge.yml");
  const guard = join(root, "bin/pr_guard.py");
  if (!existsSync(workflow)) {
    push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing auto-merge workflow");
  } else {
    const text = readFileSync(workflow, "utf8");
    if (!text.includes("(feat|fix|docs|refactor|perf|test|build|ci|chore|revert)")) {
      push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing conventional title check");
    }
    if (!text.includes("Why|What changed|Scope|Blast Radius|Verification")) {
      push(problems, "pr-contract", ".github/workflows/auto-merge.yml", "missing ordered body headings");
    }
  }
  if (!existsSync(guard)) {
    push(problems, "pr-contract", "bin/pr_guard.py", "missing local PR guard");
  }
  return problems;
}

export function checkWorkflowWiring(root) {
  return [
    ...checkRouterWiring(root),
    ...checkIntakeWiring(root),
    ...checkPolicyWiring(root),
    ...checkPrContract(root),
  ];
}

const CHECKS = [
  checkSkillStructure,
  checkAsciiProse,
  checkAgentsContract,
  checkInstructionOwners,
  checkRelativeLinks,
  checkRouterWiring,
  checkIntakeWiring,
  checkPolicyWiring,
  checkCommentAuditWiring,
  checkPrContract,
];

function selfTests() {
  const tmp = mkdtempSync(join(tmpdir(), "harness-ratchets-"));
  try {
    mkdirSync(join(tmp, "skills/short"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/short/SKILL.md"),
      `---\nname: short\ndescription: valid\n---\n\n# Short\n`,
    );
    assert.deepEqual(checkSkillStructure(tmp), [], "a valid short skill must pass");

    mkdirSync(join(tmp, "skills/renamed"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/renamed/SKILL.md"),
      `---\nname: other\ndescription: mismatch\n---\n\n# Other\n`,
    );
    assert.ok(
      checkSkillStructure(tmp).some((problem) => problem.message.includes("must match the directory")),
      "a mismatched frontmatter name must fail",
    );

    mkdirSync(join(tmp, "agents"), { recursive: true });
    writeFileSync(join(tmp, "agents/dash.md"), "# A\n\none \u2014 two\n");
    assert.ok(
      checkAsciiProse(tmp).some((problem) => problem.rule === "ascii-prose" && problem.file === "agents/dash.md"),
      "an em dash must fail",
    );
    writeFileSync(join(tmp, "agents/dash.md"), "# A\n\none - two\n");
    assert.deepEqual(checkAsciiProse(tmp), [], "ASCII punctuation must pass");

    writeFileSync(join(tmp, "CHANGELOG.md"), "artifact \u2014 allowed\n");
    assert.deepEqual(checkAsciiProse(tmp), [], "ignored history must pass");

    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    assert.deepEqual(checkAgentsContract(tmp), [], "a small enforced AGENTS.md must pass");
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Task scale\n\nlong prose\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n");
    assert.ok(
      checkAgentsContract(tmp).some((problem) => problem.message.includes("routing belongs in skills/engineering-loop")),
      "task-scale routing in AGENTS.md must fail",
    );

    mkdirSync(join(tmp, "commands"), { recursive: true });
    writeFileSync(join(tmp, "commands/ok.md"), "[ref](../AGENTS.md) and [ext](https://example.com) and [anchor](#top)\n");
    assert.deepEqual(checkRelativeLinks(tmp), [], "external and anchor links must be ignored");
    writeFileSync(join(tmp, "commands/ok.md"), "[gone](../missing.md)\n");
    assert.ok(
      checkRelativeLinks(tmp).some((problem) => problem.rule === "relative-link"),
      "a broken relative link must fail",
    );

    mkdirSync(join(tmp, "skills/engineering-loop/references/playbooks"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/engineering-loop/SKILL.md"),
      `# Router\n\n## Playbook router\n\n${PLAYBOOKS.map((name) => `| \`${name}\` | use |`).join("\n")}\n\nSee references/playbooks/<id>.md.\n\n## Fallback\n\nUse feature.\n`,
    );
    writeFileSync(
      join(tmp, "skills/engineering-loop/references/playbooks.md"),
      PLAYBOOKS.map((name) => `- [${name}](playbooks/${name}.md)`).join("\n"),
    );
    for (const name of PLAYBOOKS) {
      writeFileSync(
        join(tmp, "skills/engineering-loop/references/playbooks", `${name}.md`),
        "1. one\n2. two\n3. three\n",
      );
    }
    mkdirSync(join(tmp, "plugins"), { recursive: true });
    writeFileSync(join(tmp, "plugins/auto-intake.js"), `export const PLAYBOOK_IDS = ${JSON.stringify(PLAYBOOKS)};\nexport function routePrompt(text) { return text; }\n`);
    writeFileSync(join(tmp, "AGENTS.md"), "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n");
    mkdirSync(join(tmp, ".github/workflows"), { recursive: true });
    mkdirSync(join(tmp, "bin"), { recursive: true });
    writeFileSync(
      join(tmp, ".github/workflows/auto-merge.yml"),
      "(feat|fix|docs|refactor|perf|test|build|ci|chore|revert)\nWhy|What changed|Scope|Blast Radius|Verification\nbase/bin/comment_audit.py --diff\n",
    );
    writeFileSync(
      join(tmp, ".github/workflows/ci.yml"),
      "run: bin/comment_audit.py --diff /tmp/comment-audit.diff\n",
    );
    writeFileSync(
      join(tmp, ".github/workflows/comment-audit.yml"),
      "on:\n  workflow_call:\n    inputs:\n      harness_ref:\n        type: string\nrun: bin/comment_audit.py --diff /tmp/comment-audit.diff\n",
    );
    writeFileSync(
      join(tmp, "bin/pr_guard.py"),
      "def body_problems(body):\n    return []\n",
    );
    assert.deepEqual(checkWorkflowWiring(tmp), [], "complete wiring must pass");
    assert.deepEqual(checkCommentAuditWiring(tmp), [], "the audit must be wired into both merge paths");

    writeFileSync(join(tmp, ".github/workflows/ci.yml"), "run: npm test\n");
    assert.ok(
      checkCommentAuditWiring(tmp).some((problem) => problem.file === ".github/workflows/ci.yml"),
      "CI without the diff audit must fail",
    );

    writeFileSync(join(tmp, "skills/engineering-loop/references/playbooks/perf.md"), "prose only\n");
    assert.ok(
      checkWorkflowWiring(tmp).some((problem) => problem.message.includes("at least one numbered step")),
      "a playbook without steps must fail",
    );
    writeFileSync(
      join(tmp, "skills/engineering-loop/references/playbooks/perf.md"),
      "1. one\n",
    );

    writeFileSync(join(tmp, "plugins/auto-intake.js"), 'export const PLAYBOOK_IDS = ["bug-fix"];\nexport function routePrompt() {}\n');
    assert.ok(
      checkIntakeWiring(tmp).some((problem) => problem.message.includes("PLAYBOOK_IDS is missing")),
      "a playbook id list that drifts from the eight sections must fail",
    );
    writeFileSync(join(tmp, "plugins/auto-intake.js"), `export const PLAYBOOK_IDS = ${JSON.stringify(PLAYBOOKS)};\nexport function routePrompt(text) { return text; }\n`);
    writeFileSync(join(tmp, "commands/review.md"), "A gate cannot certify its own weakening.\n");
    assert.ok(
      checkPolicyWiring(tmp).some((problem) =>
        problem.message.includes("gate cannot certify"),
      ),
      "the stale gate exception must fail",
    );
    writeFileSync(join(tmp, "commands/review.md"), "review\n");

    mkdirSync(join(tmp, "docs"), { recursive: true });
    writeFileSync(
      join(tmp, "skills/README.md"),
      "| Skill | Use |\n|---|---|\n| `one` | valid |\n",
    );
    writeFileSync(join(tmp, "README.md"), "See [skills](skills/README.md).\n");
    writeFileSync(
      join(tmp, "docs/reference.md"),
      "See [skills](../skills/README.md).\n",
    );
    const agentsWithLink = "# Rules\n\nSee [skills](skills/README.md).\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n";
    writeFileSync(join(tmp, "AGENTS.md"), agentsWithLink);
    assert.deepEqual(checkInstructionOwners(tmp), [], "one owner and three links must pass");
    writeFileSync(
      join(tmp, "AGENTS.md"),
      "# Rules\n\n## Commands\n\nnpm test\n\n## Boundaries\n\nno secrets\n\n## Rule enforcement\n\n| Rule | Check |\n|---|---|\n| one | `npm test` |\n",
    );
    assert.ok(
      checkInstructionOwners(tmp).some((problem) =>
        problem.message.includes("must link"),
      ),
      "AGENTS.md without a skill-map link must fail",
    );
    writeFileSync(join(tmp, "AGENTS.md"), agentsWithLink);
    writeFileSync(join(tmp, "README.md"), "| Skill | Use |\n|---|---|\n| `two` | duplicate |\n");
    assert.ok(
      checkInstructionOwners(tmp).some((problem) =>
        problem.message.includes("one owner"),
      ),
      "a second skill table must fail",
    );
    writeFileSync(join(tmp, "README.md"), "See [skills](skills/README.md).\n");
  } finally {
    rmSync(tmp, { recursive: true, force: true });
  }
}

function main() {
  selfTests();
  const problems = CHECKS.flatMap((check) => check(ROOT));
  if (problems.length > 0) {
    for (const problem of problems) console.error(formatProblem(problem));
    console.error(`\nharness-ratchets: ${problems.length} problem(s)`);
    process.exit(1);
  }
  console.log(`harness-ratchets: PASS (${CHECKS.length} checks)`);
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) main();

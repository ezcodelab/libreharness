// SPDX-License-Identifier: MIT
import { spawn, spawnSync } from "node:child_process";
import { chmodSync, mkdirSync } from "node:fs";
import { homedir } from "node:os";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

export const ROOT = dirname(dirname(fileURLToPath(import.meta.url)));

export function statePath(value, options = {}) {
  const platform = options.platform ?? process.platform;
  const env = options.env ?? process.env;
  const home = options.home ?? homedir();
  let chosen = value;
  if (!chosen) {
    if (platform === "win32") {
      chosen = join(env.LOCALAPPDATA ?? join(home, "AppData", "Local"), "libreharness");
    } else if (platform === "darwin") {
      chosen = join(home, "Library", "Application Support", "libreharness");
    } else {
      chosen = join(env.XDG_STATE_HOME ?? join(home, ".local", "state"), "libreharness");
    }
  }
  return resolve(String(chosen).replace(/^~(?=$|[\\/])/, home));
}

export function minimalEnv(overrides = {}) {
  const env = {
    PATH: process.env.PATH ?? "/usr/bin:/bin",
    HOME: process.env.HOME ?? "",
    ...overrides,
  };
  if (process.platform === "win32") {
    for (const name of [
      "SystemRoot",
      "SystemDrive",
      "WINDIR",
      "COMSPEC",
      "PATHEXT",
      "USERPROFILE",
      "TEMP",
      "TMP",
      "APPDATA",
      "LOCALAPPDATA",
    ]) {
      if (process.env[name]) env[name] = process.env[name];
    }
  }
  return env;
}

export function ensureStateDirectory(state) {
  mkdirSync(state, { recursive: true, mode: 0o700 });
  if (process.platform !== "win32") chmodSync(state, 0o700);
}

export function resolvePython(options = {}) {
  const env = options.env ?? process.env;
  const platform = options.platform ?? process.platform;
  if (env.LIBREHARNESS_PYTHON) {
    return { command: env.LIBREHARNESS_PYTHON, prefixArgs: [] };
  }
  const candidates =
    platform === "win32"
      ? [
          ["py", ["-3"]],
          ["python", []],
          ["python3", []],
        ]
      : [
          ["python3", []],
          ["python", []],
        ];
  for (const [command, prefixArgs] of candidates) {
    const probe = spawnSync(command, [...prefixArgs, "--version"], {
      env,
      stdio: "ignore",
      timeout: 10000,
    });
    if (!probe.error && probe.status === 0) return { command, prefixArgs };
  }
  throw new Error(
    "LibreHarness requires Python 3.10 or newer; set LIBREHARNESS_PYTHON to the interpreter",
  );
}

export function runProcess(command, args, cwd, env, signal) {
  return new Promise((resolvePromise, reject) => {
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
        resolvePromise(output);
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

export async function packageTool(script, args, cwd, env, signal) {
  const childEnv = { ...process.env, ...env };
  delete childEnv.HARNESS_HOME;
  const python = resolvePython({ env: childEnv });
  return runProcess(
    python.command,
    [...python.prefixArgs, join(ROOT, "bin", script), ...args],
    cwd,
    childEnv,
    signal,
  );
}

export async function untracked(cwd, signal) {
  const output = await runProcess(
    "git",
    ["ls-files", "-z", "--others", "--exclude-standard"],
    cwd,
    process.env,
    signal,
  );
  return output.split("\0").filter(Boolean);
}
